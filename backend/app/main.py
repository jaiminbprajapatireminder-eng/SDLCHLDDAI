import base64
import io
import json
import os
from pathlib import Path
import zipfile
from typing import Dict

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.gemini_dataflow import call_gemini_dataflow
from app.generator import generate_project_plan
from app.parser import parse_hldd_document
from app.agent.graph import build_agent
from app.agent.state import AgentState
from app.rag import retriever
from langchain_core.messages import AIMessage, HumanMessage

app = FastAPI(title="HLDD AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LATEST_PAYLOAD: Dict[str, object] = {}


async def _read_upload(file: UploadFile) -> str:
    content = await file.read()
    filename = file.filename or "upload.txt"

    if filename.lower().endswith((".txt", ".md")):
        return content.decode("utf-8", errors="ignore")

    if filename.lower().endswith(".docx"):
        try:
            import docx

            doc = docx.Document(io.BytesIO(content))
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Unable to parse DOCX file: {exc}") from exc

    if filename.lower().endswith(".pdf"):
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Unable to parse PDF file: {exc}") from exc

    raise HTTPException(status_code=400, detail="Unsupported file type. Use .txt, .md, .docx, or .pdf")


class ChatbotRequest(BaseModel):
    prompt: str
    priority: str = "balanced"


def recommend_llm(payload: Dict[str, object]) -> Dict[str, str]:
    stack = {str(item).strip() for item in payload.get("technology_stack", []) if item}

    if "Google Cloud" in stack or "GCP" in stack:
        return {
            "provider": "Google Gemini",
            "model": "gemini-2.0-flash → gemini-2.5-flash",
            "reason": "Gemini Dataflow pipeline — best fit for GCP and cloud-specific delivery guidance.",
        }

    if {"React", "FastAPI", "PostgreSQL", "Docker"}.issubset(stack):
        return {
            "provider": "OpenAI",
            "model": "gpt-4.1-mini",
            "reason": "Best fit for React, FastAPI, PostgreSQL, and Docker delivery planning.",
        }

    if {"AWS", "Azure", "GCP"}.intersection(stack):
        return {
            "provider": "OpenAI",
            "model": "gpt-4o-mini",
            "reason": "Good fit for cloud-focused architecture and delivery guidance.",
        }

    return {
        "provider": "OpenAI",
        "model": "gpt-4o-mini",
        "reason": "General-purpose recommendations for HLDD analysis and planning.",
    }


def is_out_of_scope(prompt: str) -> bool:
    normalized_prompt = prompt.lower().strip()
    if not normalized_prompt:
        return False

    scope_keywords = (
        "hldd",
        "dashboard",
        "feature",
        "features",
        "story",
        "stories",
        "testing",
        "architecture",
        "frontend",
        "backend",
        "database",
        "postgresql",
        "cloud",
        "aws",
        "azure",
        "gcp",
        "google cloud",
        "docker",
        "kubernetes",
        "repository",
        "repo",
        "project structure",
        "project management",
        "jira",
        "trello",
        "github",
        "gitlab",
        "bitbucket",
        "deployment",
        "cost",
        "budget",
        "pricing",
        "security",
        "efficiency",
        "turnaround",
        "recommended model",
        "openai",
        "gemini",
        "llm",
        "rag",
        "mcp",
        "ci/cd",
        "pipeline",
        "mobile",
        "android",
        "ios",
        "react native",
        "flutter",
    )

    return not any(keyword in normalized_prompt for keyword in scope_keywords)


def build_chat_context(payload: Dict[str, object]) -> str:
    title = payload.get("title") or "Untitled HLDD"
    summary = payload.get("summary") or "No summary provided."
    tech_stack = ", ".join(str(item) for item in payload.get("technology_stack", []) if item)
    functional_requirements = payload.get("functional_requirements") or []
    acceptance_criteria = payload.get("acceptance_criteria") or []
    features = payload.get("features") or []
    stories = payload.get("stories") or []
    testing_stories = payload.get("testing_stories") or []
    project_management_tool = payload.get("project_management_tool") or "Not specified"
    repository = payload.get("repository") or "Not specified"
    ci_cd_pipeline = payload.get("ci_cd_pipeline") or "Not specified"
    architecture_notes = payload.get("architecture_notes") or []
    project_structure = payload.get("project_structure") or []

    return "\n".join(
        [
            f"Title: {title}",
            f"Summary: {summary}",
            f"Technology stack: {tech_stack or 'Not specified'}",
            f"Project management tool: {project_management_tool}",
            f"Repository: {repository}",
            f"CI/CD pipeline: {ci_cd_pipeline}",
            f"Functional requirements: {', '.join(str(item) for item in functional_requirements) or 'Not specified'}",
            f"Acceptance criteria: {', '.join(str(item) for item in acceptance_criteria) or 'Not specified'}",
            f"Architecture notes: {', '.join(str(item) for item in architecture_notes) or 'Not specified'}",
            f"Project structure: {', '.join(str(item) for item in project_structure) or 'Not specified'}",
            f"Features: {len(features)}",
            f"Development stories: {len(stories)}",
            f"Testing stories: {len(testing_stories)}",
        ]
    )


_QUESTION_PATTERNS = {
    "backend_alternative": [
        "alternative", "replace", "instead of", "substitute",
        "other option", "different", "another",
    ],
    "backend_mobile": [
        "mobile", "android", "ios", "react native", "flutter",
        "mobile app", "smartphone", "tablet",
    ],
    "frontend_alternative": [
        "frontend alternative", "front end alternative",
        "replace frontend", "frontend instead",
    ],
    "cloud_alternative": [
        "cloud alternative", "replace cloud",
        "other cloud", "different cloud",
    ],
    "database_alternative": [
        "database alternative", "replace database",
        "other database", "different database",
    ],
    "cost": [
        "cost", "price", "pricing", "compare", "expensive",
        "cheapest", "instance", "ec2", "vm", "compute",
        "budget", "billing", "monthly",
        "storage", "services", "service",
    ],
}


def _detect_question_type(prompt: str) -> str:
    lower = prompt.lower().strip()

    has_backend = any(word in lower for word in ["backend", "back-end", "back end", "server"])
    has_mobile = any(word in lower for word in _QUESTION_PATTERNS["backend_mobile"])
    has_frontend = any(word in lower for word in ["frontend", "front-end", "front end", "ui", "client"])
    has_cloud = any(word in lower for word in ["cloud"])
    has_database = any(word in lower for word in ["database", "db", "data store"])
    has_alternative = any(word in lower for word in _QUESTION_PATTERNS["backend_alternative"])
    has_cost = any(word in lower for word in _QUESTION_PATTERNS["cost"])

    if has_cost:
        return "cost"

    if has_backend and has_mobile and has_alternative:
        return "backend_mobile"

    if has_backend and has_alternative:
        return "backend_alternative"

    if has_frontend and has_alternative:
        return "frontend_alternative"

    if has_cloud and has_alternative:
        return "cloud_alternative"

    if has_database and has_alternative:
        return "database_alternative"

    if has_backend:
        return "backend_general"

    return "general"


def _format_backend_alternatives(payload: Dict[str, object], prompt: str) -> str:
    stack = {str(item).strip().lower() for item in payload.get("technology_stack", []) if item}
    current = "FastAPI"
    if "spring boot" in stack:
        current = "Spring Boot"
    elif "nestjs" in stack or "node.js" in stack:
        current = "NestJS"
    elif "django" in stack:
        current = "Django"
    elif ".net" in stack or "asp.net" in stack:
        current = "ASP.NET Core"

    lines = [
        f"Current backend: {current}",
        "",
        "Recommended alternatives for your HLDD stack:",
    ]

    all_backends = [
        ("FastAPI", "Python — async, high performance, auto OpenAPI docs"),
        ("Spring Boot", "Java/Kotlin — mature, strong typing, rich ecosystem"),
        ("NestJS", "TypeScript/Node.js — modular, familiar to JS devs"),
        ("Django", "Python — batteries-included, admin panel, ORM built-in"),
        ("ASP.NET Core", "C# — enterprise-grade, great tooling, high throughput"),
    ]

    for name, desc in all_backends:
        if name.lower() not in stack:
            lines.append(f"  - {name}: {desc}")

    lines.extend([
        "",
        "How to choose:",
        "  - Stick with Python? → FastAPI or Django",
        "  - Need enterprise support? → Spring Boot or ASP.NET Core",
        "  - Want JS/TS across stack? → NestJS",
        "  - Fastest MVP? → FastAPI (current default)",
    ])

    return "\n".join(lines)


def _format_backend_mobile_alternatives(payload: Dict[str, object], prompt: str) -> str:
    stack = {str(item).strip().lower() for item in payload.get("technology_stack", []) if item}
    current = "FastAPI"
    if "spring boot" in stack:
        current = "Spring Boot"
    elif "nestjs" in stack or "node.js" in stack:
        current = "NestJS"
    elif "django" in stack:
        current = "Django"
    elif ".net" in stack or "asp.net" in stack:
        current = "ASP.NET Core"

    lines = [
        f"Current backend: {current}",
        "",
        "For mobile app development, your backend should offer:",
        "  - Lightweight REST/GraphQL APIs",
        "  - Push notification support",
        "  - Auth (OAuth2, JWT, Firebase Auth)",
        "  - Scalable data sync",
        "",
        "Best alternatives for mobile:",
    ]

    mobile_options = [
        ("NestJS + GraphQL", "TypeScript — great for real-time, subscriptions, and shared types with React Native"),
        ("Firebase + Cloud Functions", "Serverless — auth, DB, push, analytics out of the box"),
        ("Supabase + FastAPI", "PostgreSQL + real-time subscriptions, auth, and storage — pairs well with your current stack"),
        ("Django + DRF + Channels", "Python — REST framework + WebSockets, great for mobile + web"),
        ("Spring Boot", "Java — robust for enterprise mobile backends"),
    ]

    for name, desc in mobile_options:
        lines.append(f"  - {name}: {desc}")

    lines.extend([
        "",
        "Top pick for mobile:",
        "  Supabase + FastAPI — stays close to your current stack, adds real-time and auth",
    ])

    return "\n".join(lines)


def _format_frontend_alternatives(payload: Dict[str, object]) -> str:
    stack = {str(item).strip().lower() for item in payload.get("technology_stack", []) if item}
    current = "React + Vite"
    if "angular" in stack:
        current = "Angular + Nx"
    elif "vue" in stack:
        current = "Vue + Vite"
    elif "next.js" in stack or "nextjs" in stack:
        current = "Next.js"

    lines = [
        f"Current frontend: {current}",
        "",
        "Alternative frontend options:",
    ]

    options = [
        ("React + Vite", "Most popular, huge ecosystem, flexible component model"),
        ("Next.js", "React with SSR/SSG, file-based routing, good for SEO"),
        ("Angular + Nx", "Full framework, strong typing, enterprise-grade structure"),
        ("Vue + Vite", "Lightweight, easy learning curve, great DX"),
        ("SvelteKit", "Newer, minimal boilerplate, very fast runtime"),
    ]

    for name, desc in options:
        label = f"  - {name}: {desc}"
        if name.lower().strip() in stack:
            label += " (current)"
        lines.append(label)

    lines.extend([
        "",
        "How to choose:",
        "  - Need SSR/SEO? → Next.js",
        "  - Large team, strict patterns? → Angular + Nx",
        "  - Fast and simple? → React + Vite or Vue + Vite",
    ])

    return "\n".join(lines)


def _format_cloud_alternatives(payload: Dict[str, object]) -> str:
    stack = {str(item).strip().lower() for item in payload.get("technology_stack", []) if item}
    current = "Google Cloud"
    if "aws" in stack:
        current = "AWS"
    elif "azure" in stack:
        current = "Azure"

    lines = [
        f"Current cloud: {current}",
        "",
        "Alternative cloud providers:",
    ]

    clouds = [
        ("AWS", "Mature, broadest service catalog, strong DevOps tooling"),
        ("Azure", "Best .NET/Microsoft integration, enterprise hybrid cloud"),
        ("Google Cloud", "Leader in data/ML, competitive pricing, Cloud Run"),
    ]

    for name, desc in clouds:
        label = f"  - {name}: {desc}"
        if name.lower() in stack:
            label += " (current)"
        lines.append(label)

    lines.extend([
        "",
        "Quick comparison:",
        "  - Lowest cost → Google Cloud (Cloud Run reduces ops overhead)",
        "  - Widest services → AWS",
        "  - Microsoft shop → Azure",
    ])

    return "\n".join(lines)


def _format_database_alternatives(payload: Dict[str, object]) -> str:
    stack = {str(item).strip().lower() for item in payload.get("technology_stack", []) if item}
    current = "PostgreSQL"
    if "mysql" in stack:
        current = "MySQL"
    elif "mongodb" in stack:
        current = "MongoDB"
    elif "sql server" in stack:
        current = "SQL Server"
    elif "oracle" in stack:
        current = "Oracle"
    elif "sqlite" in stack:
        current = "SQLite"

    lines = [
        f"Current database: {current}",
        "",
        "Alternative database options:",
    ]

    dbs = [
        ("PostgreSQL", "Advanced SQL, JSON support, great ecosystem"),
        ("MySQL", "Widely adopted, performant reads, good for LAMP stack"),
        ("MongoDB", "Document store, flexible schema, good for rapid prototyping"),
        ("SQLite", "Embedded, zero-config, good for local/dev use"),
        ("DuckDB", "Analytical/OLAP, embedded, great for reporting"),
    ]

    for name, desc in dbs:
        label = f"  - {name}: {desc}"
        if name.lower() in stack or name.lower() == current.lower():
            label += " (current)"
        lines.append(label)

    lines.extend([
        "",
        "How to choose:",
        "  - Relational/structured data → PostgreSQL or MySQL",
        "  - Flexible/unstructured → MongoDB",
        "  - Analytics/reporting → DuckDB (alongside your primary DB)",
    ])

    return "\n".join(lines)


def _format_backend_general(payload: Dict[str, object]) -> str:
    stack = {str(item).strip().lower() for item in payload.get("technology_stack", []) if item}
    current = "FastAPI"
    if "spring boot" in stack:
        current = "Spring Boot"
    elif "nestjs" in stack or "node.js" in stack:
        current = "NestJS"
    elif "django" in stack:
        current = "Django"

    lines = [
        f"Current backend: {current}",
        "",
        f"{current} is well-suited for your HLDD project.",
        "",
        "Key strengths:",
    ]

    strengths = {
        "FastAPI": ["Async-first, high throughput", "Auto-generated OpenAPI docs", "Pydantic validation built-in", "Great with Docker + cloud run"],
        "Spring Boot": ["Mature ecosystem, battle-tested", "Strong typing and DI", "Excellent transaction support", "Cloud-native with Spring Cloud"],
        "NestJS": ["Modular architecture out of the box", "TypeScript end-to-end", "GraphQL + WebSocket support", "Familiar for Angular/React devs"],
        "Django": ["Batteries-included (admin, ORM, auth)", "Great documentation", "Large community and packages", "Secure by default"],
        "ASP.NET Core": ["High performance", "Strong tooling (Visual Studio)", "Great for enterprise apps", "Cross-platform"],
    }

    for s in strengths.get(current, ["Well-suited for your HLDD stack."]):
        lines.append(f"  - {s}")

    lines.extend([
        "",
        "Tip: Ask for 'backend alternative' to see other backend options.",
    ])

    return "\n".join(lines)


# Cloud service categories used for broader cost guidance
_CLOUD_SERVICE_CATEGORIES = [
    ("Compute",           "VMs, containers, serverless functions, autoscaling groups, spot/preemptible instances"),
    ("Object Storage",    "S3 / Blob Storage / Cloud Storage — tiered (hot/cool/archive/glacier)"),
    ("Block Storage",     "EBS / Managed Disk / Persistent Disk — SSD/HDD, snapshots, IOPS-based pricing"),
    ("Databases",         "RDS / Azure SQL / Cloud SQL (relational); DynamoDB / Cosmos DB / Firestore (NoSQL); ElastiCache / Redis Cache / Memorystore"),
    ("Serverless / FaaS", "Lambda / Functions / Cloud Functions — per-invocation & duration billing"),
    ("Content Delivery",  "CloudFront / Azure CDN / Cloud CDN — data transfer pricing per region"),
    ("Container Orchestration", "ECS/EKS / AKS / GKE — control plane fee + node cost; Fargate/ACI/Cloud Run for serverless containers"),
    ("API Gateway / LB",  "API Gateway / APIM / Cloud Endpoints — per-call & data-out pricing; ALB/NLB/GLB (hourly + LCU/unit)"),
    ("AI / ML Services",  "SageMaker / Azure ML / Vertex AI — training & inference compute; Rekognition / Vision / Speech / Translator APIs per-request"),
    ("Data Analytics",    "Athena/EMR/Redshift / Synapse/HDInsight / BigQuery/Dataproc — query-scan or cluster-hour pricing"),
    ("Monitoring / Logs", "CloudWatch / Monitor / Cloud Operations — metric retention, log ingestion, alerting"),
    ("Data Transfer",     "Internet egress charges often dominate costs; free-tier inbound, paid outbound (varies by provider & region)"),
]

_SERVICE_KEYWORDS = {
    "compute": ["compute", "vm", "vms", "virtual machine", "ec2", "instance"],
    "storage": ["storage", "blob", "s3", "disk", "ebs", "file storage", "archive", "backup"],
    "database": ["database", "db", "sql", "nosql", "rds", "dynamodb", "cosmos", "firestore", "redis", "cache"],
    "serverless": ["serverless", "lambda", "function", "faas"],
    "cdn": ["cdn", "content delivery", "cloudfront", "edge"],
    "container": ["container", "kubernetes", "k8s", "docker", "eks", "aks", "gke", "ecs"],
    "api gateway": ["api gateway", "apim", "load balancer", "alb", "nlb"],
    "ai/ml": ["ai", "ml", "machine learning", "sage maker", "vertex", "cognito", "rekognition", "comprehend"],
    "analytics": ["analytics", "big data", "athena", "emr", "redshift", "bigquery", "dataproc", "synapse"],
    "monitoring": ["monitoring", "logging", "cloudwatch", "metric", "alert", "trace"],
    "data transfer": ["data transfer", "egress", "bandwidth", "network"],
}

# Maps detected service category keywords to _SERVICE_INSTANCE_DATA keys
_CATEGORY_INSTANCE_MAP = {
    "compute": ["compute"],
    "storage": ["object storage", "block storage"],
    "database": ["databases"],
    "serverless": ["serverless"],
    "cdn": ["cdn"],
    "container": ["container orchestration"],
    "api gateway": ["api gateway"],
    "ai/ml": ["ai/ml"],
    "analytics": ["data analytics"],
    "monitoring": ["monitoring"],
    "data transfer": ["data transfer"],
}

_CLOUD_PROVIDER_PRICING = {
    "aws": {
        "name": "AWS",
        "calculator": "https://calculator.aws/#/",
        "docs": "https://aws.amazon.com/pricing/",
        "free_tier": "https://aws.amazon.com/free/",
        "optimization": "Cost Explorer, Savings Plans, Compute Optimizer, Trusted Advisor",
    },
    "azure": {
        "name": "Azure",
        "calculator": "https://azure.microsoft.com/en-us/pricing/calculator/",
        "docs": "https://azure.microsoft.com/en-us/pricing/",
        "free_tier": "https://azure.microsoft.com/en-us/free/",
        "optimization": "Cost Management + Billing, Azure Advisor, Reserved Instances, Spot VMs",
    },
    "gcp": {
        "name": "GCP",
        "calculator": "https://cloud.google.com/products/calculator",
        "docs": "https://cloud.google.com/pricing",
        "free_tier": "https://cloud.google.com/free",
        "optimization": "Cost Management, Committed Use Discounts, Preemptible VMs, Recommender",
    },
}

# Concrete service instances with configuration and cost per provider
_SERVICE_INSTANCE_DATA = {
    "compute": {
        "aws": [
            ("t3.micro",     "2 vCPU", "1 GB",    "$0.0104/hr",  "Burstable, low-traffic web apps, dev/test"),
            ("t3.small",     "2 vCPU", "2 GB",    "$0.0208/hr",  "Burstable, medium web apps, staging"),
            ("t3.medium",    "2 vCPU", "4 GB",    "$0.0416/hr",  "Burstable, production web apps, app servers"),
            ("t3.large",     "2 vCPU", "8 GB",    "$0.0832/hr",  "Burstable, high-traffic web apps"),
            ("m5.large",     "2 vCPU", "8 GB",    "$0.096/hr",   "General purpose, balanced compute & memory"),
            ("m5.xlarge",    "4 vCPU", "16 GB",   "$0.192/hr",   "General purpose, medium workloads"),
            ("m5.2xlarge",   "8 vCPU", "32 GB",   "$0.384/hr",   "General purpose, large workloads"),
            ("c5.large",     "2 vCPU", "4 GB",    "$0.085/hr",   "Compute-optimized, batch processing"),
            ("c5.xlarge",    "4 vCPU", "8 GB",    "$0.17/hr",    "Compute-optimized, video encoding"),
            ("r5.large",     "2 vCPU", "16 GB",   "$0.126/hr",   "Memory-optimized, in-memory caches"),
            ("r5.xlarge",    "4 vCPU", "32 GB",   "$0.252/hr",   "Memory-optimized, large databases"),
        ],
        "azure": [
            ("B1s",          "1 vCPU", "1 GB",    "$0.0067/hr",  "Burstable, low-cost dev/test"),
            ("B1ms",         "1 vCPU", "2 GB",    "$0.0133/hr",  "Burstable, small web apps"),
            ("B2s",          "2 vCPU", "4 GB",    "$0.0267/hr",  "Burstable, medium workloads"),
            ("B2ms",         "2 vCPU", "8 GB",    "$0.0533/hr",  "Burstable, production web apps"),
            ("D2s v3",       "2 vCPU", "8 GB",    "$0.096/hr",   "General purpose, balanced"),
            ("D4s v3",       "4 vCPU", "16 GB",   "$0.192/hr",   "General purpose, medium workloads"),
            ("D8s v3",       "8 vCPU", "32 GB",   "$0.384/hr",   "General purpose, large workloads"),
            ("F2s v2",       "2 vCPU", "4 GB",    "$0.085/hr",   "Compute-optimized"),
            ("F4s v2",       "4 vCPU", "8 GB",    "$0.17/hr",    "Compute-optimized, batch"),
            ("E2s v3",       "2 vCPU", "16 GB",   "$0.126/hr",   "Memory-optimized"),
            ("E4s v3",       "4 vCPU", "32 GB",   "$0.252/hr",   "Memory-optimized, databases"),
        ],
        "gcp": [
            ("e2-micro",     "2 vCPU", "1 GB",    "$0.0065/hr",  "Burstable, smallest compute"),
            ("e2-small",     "2 vCPU", "2 GB",    "$0.013/hr",   "Burstable, small services"),
            ("e2-medium",    "2 vCPU", "4 GB",    "$0.026/hr",   "Burstable, moderate workloads"),
            ("e2-standard-2","2 vCPU", "8 GB",    "$0.052/hr",   "Standard, balanced production"),
            ("e2-standard-4","4 vCPU", "16 GB",   "$0.104/hr",   "Standard, medium workloads"),
            ("e2-standard-8","8 vCPU", "32 GB",   "$0.208/hr",   "Standard, large workloads"),
            ("n2-standard-2","2 vCPU", "8 GB",    "$0.096/hr",   "Next-gen general purpose"),
            ("n2-standard-4","4 vCPU", "16 GB",   "$0.192/hr",   "Next-gen, medium workloads"),
            ("n2d-highmem-2","2 vCPU", "16 GB",   "$0.126/hr",   "Memory-optimized"),
            ("c2-standard-4","4 vCPU", "16 GB",   "$0.170/hr",   "Compute-optimized"),
        ],
    },
    "object storage": {
        "aws": [
            ("S3 Standard",          "", "", "$0.023/GB/mo",  "Frequently accessed data, low-latency"),
            ("S3 Intelligent",       "", "", "$0.023/GB/mo",  "Auto-tiering for unknown patterns"),
            ("S3 Standard-IA",       "", "", "$0.0125/GB/mo", "Infrequent access, rapid retrieval"),
            ("S3 One Zone-IA",       "", "", "$0.01/GB/mo",   "Recreatable data, single AZ"),
            ("S3 Glacier Instant",   "", "", "$0.004/GB/mo",  "Archive, millisecond retrieval"),
            ("S3 Glacier Flexible",  "", "", "$0.0036/GB/mo", "Archive, 1-5 min retrieval"),
            ("S3 Glacier Deep Archive", "", "", "$0.00099/GB/mo", "Long-term archive, 12hr retrieval"),
        ],
        "azure": [
            ("Blob Hot",             "", "", "$0.018/GB/mo",  "Frequently accessed data"),
            ("Blob Cool",            "", "", "$0.01/GB/mo",   "Infrequent access, 30-day min"),
            ("Blob Cold",            "", "", "$0.0045/GB/mo", "Rarely accessed, 90-day min"),
            ("Blob Archive",         "", "", "$0.002/GB/mo",  "Long-term archive, 180-day min"),
            ("Azure Files Hot",      "", "", "$0.06/GB/mo",   "SMB/NFS file shares, transactional"),
            ("Azure Files Cool",     "", "", "$0.04/GB/mo",   "SMB/NFS file shares, infrequent"),
        ],
        "gcp": [
            ("Standard",             "", "", "$0.020/GB/mo",  "Frequently accessed, multi-region"),
            ("Nearline",             "", "", "$0.010/GB/mo",  "Infrequent, 30-day min"),
            ("Coldline",             "", "", "$0.004/GB/mo",  "Rarely accessed, 90-day min"),
            ("Archive",              "", "", "$0.0012/GB/mo", "Long-term archive, 365-day min"),
            ("Filestore Basic HDD",  "", "", "$0.02/GB/mo",   "NFS file storage, capacity-oriented"),
            ("Filestore Basic SSD",  "", "", "$0.06/GB/mo",   "NFS file storage, performance-oriented"),
        ],
    },
    "block storage": {
        "aws": [
            ("EBS gp3",              "", "", "$0.08/GB/mo",   "General purpose SSD, 3K IOPS free"),
            ("EBS io2 Block Express","", "", "$0.125/GB/mo",  "Provisioned IOPS SSD, high perf"),
            ("EBS st1",              "", "", "$0.045/GB/mo",  "Throughput-optimized HDD"),
            ("EBS sc1",              "", "", "$0.015/GB/mo",  "Cold HDD, lowest cost"),
            ("Instance Store",       "", "", "$0.00/GB/mo",   "Ephemeral, included with EC2"),
        ],
        "azure": [
            ("Managed SSD Premium","", "", "$0.12/GB/mo",    "Premium SSD, low latency, 4K-20K IOPS"),
            ("Managed SSD Standard","", "", "$0.05/GB/mo",   "Standard SSD, consistent perf"),
            ("Managed HDD Standard","", "", "$0.03/GB/mo",   "Standard HDD, backup/dev/test"),
            ("Ultra Disk",           "", "", "$0.16/GB/mo",  "Ultra-high perf, sub-ms latency"),
        ],
        "gcp": [
            ("Persistent Disk SSD",  "", "", "$0.17/GB/mo",  "Standard SSD, 1.5K-15K IOPS"),
            ("Persistent Disk HDD",  "", "", "$0.04/GB/mo",  "Standard HDD, backup/dev/test"),
            ("Local SSD (NVMe)",     "", "", "$0.08/GB/mo",  "Ephemeral, included with instance"),
            ("Hyperdisk Extreme",    "", "", "$0.17/GB/mo",  "High IOPS, 100K+ throughput"),
        ],
    },
    "databases": {
        "aws": [
            ("RDS db.t3.micro",      "2 vCPU", "1 GB",    "$0.017/hr",  "MySQL/PostgreSQL/MariaDB, dev/test"),
            ("RDS db.t3.medium",     "2 vCPU", "4 GB",    "$0.068/hr",  "MySQL/PostgreSQL, small production"),
            ("RDS db.r5.large",      "2 vCPU", "16 GB",   "$0.24/hr",   "Memory-optimized, production DB"),
            ("Aurora Serverless v2", "", "", "$0.12/ACU-hr","Auto-scaling MySQL/PostgreSQL"),
            ("DynamoDB On-Demand",   "", "", "$1.25/RCU-mo + $1.25/WCU-mo", "NoSQL, auto-scaling"),
            ("ElastiCache r6g.large","2 vCPU","13.3 GB", "$0.163/hr",  "Redis/Memcached, in-memory cache"),
        ],
        "azure": [
            ("Azure SQL S2",         "", "", "$75.11/mo",  "Standard tier, 50 DTU, 250GB DB"),
            ("Azure SQL S4",         "", "", "$150.22/mo", "Standard tier, 100 DTU, 250GB DB"),
            ("Azure SQL Hyperscale", "", "", "$0.90/hr",   "Serverless, auto-scale to 100TB"),
            ("Cosmos DB Autoscale",  "", "", "$0.008/RU",  "NoSQL, global distribution"),
            ("Cache for Redis C1",   "", "", "$0.06/hr",   "1 GB Redis cache, basic tier"),
        ],
        "gcp": [
            ("Cloud SQL db-f1-micro","0.25 vCPU","0.6 GB","$0.015/hr", "MySQL/PostgreSQL, dev/test"),
            ("Cloud SQL db-perf-optimized-2","2 vCPU","16 GB","$0.50/hr","Production MySQL/PostgreSQL"),
            ("Spanner Regional",     "", "", "$0.90/hr",   "Globally distributed, strong consistency"),
            ("Firestore",            "", "", "$0.06/100K reads", "NoSQL, real-time, serverless"),
            ("Memorystore r2c2",     "2 vCPU", "14 GB",   "$0.154/hr", "Redis, high availability"),
        ],
    },
    "serverless": {
        "aws": [
            ("Lambda",               "", "", "$0.20/1M requests + $0.0000166667/GB-sec", "Up to 10GB memory, 15min timeout"),
            ("Lambda @ Edge",        "", "", "$0.60/1M requests + $0.00005001/GB-sec", "Global, edge-located functions"),
        ],
        "azure": [
            ("Functions",            "", "", "$0.20/1M executions + $0.000016/GB-sec", "Consumption plan, 5min timeout"),
            ("Functions Premium",    "", "", "$0.139/hr",  "Premium plan, VNet, unlimited exec"),
        ],
        "gcp": [
            ("Cloud Functions 1st gen", "", "", "$0.40/1M invocations + $0.0000025/GB-sec", "128MB-8GB, 9min timeout"),
            ("Cloud Functions 2nd gen", "", "", "$0.40/1M invocations + $0.00001/GB-sec", "Cloud Run-based, 60min timeout"),
            ("Cloud Run",            "", "", "$0.00/hr + $0.000024/GB-sec", "Container-based serverless, min 0"),
        ],
    },
    "cdn": {
        "aws": [
            ("CloudFront",           "", "", "$0.085/GB (US)",  "Global CDN, 20K requests free/mo"),
            ("CloudFront",           "", "", "$0.12/GB (EU)",   "European edge locations"),
            ("CloudFront",           "", "", "$0.25/GB (SA)",   "South American edge locations"),
        ],
        "azure": [
            ("CDN Standard",         "", "", "$0.081/GB (US)",  "Microsoft Standard Rules"),
            ("CDN Premium",          "", "", "$0.15/GB (US)",   "Verizon Premium"),
            ("Front Door",           "", "", "$0.062/GB",       "Global HTTP(S) load balancer + CDN"),
        ],
        "gcp": [
            ("Cloud CDN",            "", "", "$0.08/GB (APAC)", "Global CDN, 10K requests free/mo"),
            ("Cloud CDN",            "", "", "$0.02/GB (US)",   "US/Canada edge locations"),
            ("Cloud CDN Cache Egress","", "", "$0.02-0.08/GB", "Varies by destination region"),
        ],
    },
    "container orchestration": {
        "aws": [
            ("EKS Control Plane",    "", "", "$0.10/hr",   "Kubernetes management per cluster"),
            ("ECS Fargate",          "", "", "$0.00001333/vCPU-s + $0.00000145/GB-s", "Serverless containers, no node mgmt"),
            ("ECS EC2",              "", "", "$0.00/hr",   "No mgmt fee, pay for EC2 nodes only"),
        ],
        "azure": [
            ("AKS Control Plane",    "", "", "$0.00/hr",   "Free managed Kubernetes control plane"),
            ("ACI",                  "", "", "$0.000008/vCPU-s + $0.000001/GB-s", "Serverless containers"),
        ],
        "gcp": [
            ("GKE Control Plane (Zonal)", "", "", "$0.10/hr", "Kubernetes management per cluster"),
            ("GKE Autopilot",        "", "", "$0.000032/vCPU-s + $0.000003/GB-s", "Serverless Kubernetes, node mgmt included"),
            ("Cloud Run",            "", "", "$0.00/hr + $0.000024/GB-s", "Serverless containers, 60min timeout"),
        ],
    },
    "api gateway": {
        "aws": [
            ("API Gateway REST",     "", "", "$3.50/1M API calls + $0.09/GB", "REST API, caching, throttling"),
            ("API Gateway HTTP",     "", "", "$1.00/1M API calls", "Low-latency HTTP APIs"),
            ("ALB",                  "", "", "$0.0225/hr + $0.008/LCU", "Application Load Balancer"),
            ("NLB",                  "", "", "$0.0225/hr + $0.006/LCU", "Network Load Balancer"),
        ],
        "azure": [
            ("APIM Developer",       "", "", "$0.05/hr",   "API Management, dev/test"),
            ("APIM Standard",        "", "", "$0.19/hr",   "API Management, production"),
            ("App Gateway v2",       "", "", "$0.246/hr + $0.008/GB", "Layer 7 load balancer + WAF"),
        ],
        "gcp": [
            ("Cloud Endpoints",      "", "", "$0.00/hr",   "API management, pay per call volume"),
            ("Cloud Load Balancer",  "", "", "$0.025/hr + $0.008/GB", "Global HTTP(S)/TCP load balancer"),
        ],
    },
    "ai/ml": {
        "aws": [
            ("SageMaker ml.t3.medium","2 vCPU","4 GB",    "$0.047/hr",    "Notebook/training instance"),
            ("SageMaker ml.m5.xlarge","4 vCPU","16 GB",   "$0.23/hr",     "Training, moderate workloads"),
            ("Rekognition",          "", "", "$0.001/image","Image/video analysis per API call"),
            ("Comprehend",           "", "", "$0.0001/entity","NLP entity extraction"),
            ("Polly",                "", "", "$0.000004/char","Text-to-speech"),
        ],
        "azure": [
            ("Azure ML Standard_DS3_v2","4 vCPU","14 GB","$0.298/hr", "Compute cluster training"),
            ("Cognitive Services",   "", "", "$1.50/1K transactions","Vision/Speech/Language APIs"),
            ("Bot Service",          "", "", "$0.50/hr",  "Conversational AI"),
        ],
        "gcp": [
            ("Vertex AI n1-standard-4","4 vCPU","15 GB","$0.19/hr",    "Training/prediction node"),
            ("Vertex AI Custom",     "", "", "$0.00/hr + $3.50/1K nodes","AutoML model training"),
            ("Vision API",           "", "", "$1.50/1K images","Image recognition, label detection"),
            ("Natural Language",     "", "", "$1.00/1K entities","Entity extraction, sentiment"),
        ],
    },
    "data analytics": {
        "aws": [
            ("Athena",               "", "", "$5.00/TB scanned", "Serverless SQL query on S3"),
            ("EMR m5.xlarge",        "4 vCPU", "16 GB","$0.198/hr",  "Hadoop/Spark cluster node"),
            ("RedShift dc2.large",   "2 vCPU", "15 GB","$0.25/hr",   "Data warehouse"),
        ],
        "azure": [
            ("Synapse Dedicated",    "", "", "$1.20/hr",  "Data warehouse, 100 DWU"),
            ("HDInsight A3",         "4 vCPU", "7 GB",  "$0.19/hr",   "Hadoop/Spark cluster"),
            ("Azure Data Lake",      "", "", "$0.04/GB/mo","Analytics storage, unlimited"),
        ],
        "gcp": [
            ("BigQuery On-Demand",   "", "", "$5.00/TB processed", "Serverless analytics SQL"),
            ("BigQuery Flat Rate",   "", "", "$0.0022/slot-hr","Reserved capacity pricing"),
            ("Dataproc n1-standard-4","4 vCPU","15 GB","$0.19/hr",   "Spark/Hadoop cluster node"),
        ],
    },
    "monitoring": {
        "aws": [
            ("CloudWatch Metrics",   "", "", "$0.30/metric/mo", "Standard metrics, 10-day retention"),
            ("CloudWatch Logs",      "", "", "$0.50/GB ingested", "Log storage and query"),
            ("CloudWatch Alarms",    "", "", "$0.10/alarm/mo",  "Per-alarm charge"),
            ("X-Ray",                "", "", "$5.00/100K traces","Distributed tracing"),
        ],
        "azure": [
            ("Monitor Metrics",      "", "", "$0.05/metric/mo", "Standard metrics, 93-day retention"),
            ("Log Analytics",        "", "", "$2.76/GB/mo",     "Log retention and query"),
            ("Application Insights", "", "", "$0.30/GB ingested","APM and telemetry"),
        ],
        "gcp": [
            ("Cloud Monitoring Metrics","","","$0.10/metric/mo", "Standard metrics, 6wk retention"),
            ("Cloud Logging Storage","", "", "$0.50/GB/mo",     "Log storage, 30-day default"),
            ("Cloud Trace",          "", "", "$0.00/50K spans/mo","Distributed tracing, free tier"),
        ],
    },
    "data transfer": {
        "aws": [
            ("Internet Egress",      "", "", "$0.09/GB (first 10TB)", "Outbound data from EC2/S3"),
            ("Cross-Region",         "", "", "$0.02/GB",      "Inter-region data transfer"),
            ("CloudFront Egress",    "", "", "$0.085/GB (US)","CDN data transfer out"),
        ],
        "azure": [
            ("Internet Egress",      "", "", "$0.087/GB (Zone 1)", "Outbound data from VMs/storage"),
            ("Cross-Region",         "", "", "$0.02/GB (US-US)","Inter-region data transfer"),
        ],
        "gcp": [
            ("Internet Egress",      "", "", "$0.12/GB (first 1TB)","Outbound data from GCE/GCS"),
            ("Cross-Region",         "", "", "$0.02/GB",      "Inter-region data transfer"),
            ("Premium Tier Egress",  "", "", "$0.15/GB",      "Google-grade global network"),
        ],
    },
}


def _detect_service_categories(prompt: str) -> list[str]:
    lower = prompt.lower()
    matched = []
    for category, keywords in _SERVICE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            matched.append(category)
    return matched


def _format_instance_table(instances: list[tuple]) -> list[str]:
    lines = []
    for name, cpu, mem, cost, note in instances:
        row = f"    {name:<20} {cpu:<9} {mem:<12} {cost:<18} {note}"
        lines.append(row)
    return lines


def _format_cost_comparison(payload: Dict[str, object], prompt: str) -> str:
    lower = prompt.lower()

    providers = []
    if any(w in lower for w in ("aws", "ec2", "amazon")):
        providers.append("aws")
    if any(w in lower for w in ("azure", "azur", "ms", "microsoft")):
        providers.append("azure")
    if any(w in lower for w in ("gcp", "google", "compute engine")):
        providers.append("gcp")

    if not providers:
        providers = ["aws", "azure", "gcp"]

    service_categories = _detect_service_categories(prompt)

    if service_categories:
        suffix = " — " + ", ".join(c.title() for c in service_categories)
    else:
        suffix = ""
    subtitle = f"Cloud Service Cost Comparison{suffix}"

    lines = [
        subtitle,
        "=" * 40,
        "",
    ]

    for key in providers:
        p = _CLOUD_PROVIDER_PRICING[key]
        lines.append(f"{p['name']}")
        lines.append(f"{'─' * 40}")
        lines.append(f"  Pricing calculator : {p['calculator']}")
        lines.append(f"  Pricing docs       : {p['docs']}")
        lines.append(f"  Free tier          : {p['free_tier']}")
        lines.append(f"  Cost optimization  : {p['optimization']}")
        lines.append("")

    if service_categories:
        lines.extend([
            "Relevant service categories with instance details:",
            f"{'─' * 60}",
        ])
    else:
        lines.extend([
            "Service categories to compare across providers:",
            f"{'─' * 60}",
        ])

    for category, description in _CLOUD_SERVICE_CATEGORIES:
        cat_lower = category.lower()
        if service_categories and not any(
            sc in cat_lower or cat_lower.startswith(sc)
            for sc in service_categories
        ):
            continue

        lines.append(f"")
        lines.append(f"  • {category}")
        lines.append(f"    {description}")

        # Add instance details if available
        cat_key = category.lower().replace(" / ", "/")
        instance_keys = set()
        if service_categories:
            for sc in service_categories:
                instance_keys.update(_CATEGORY_INSTANCE_MAP.get(sc, [sc]))
        else:
            instance_keys.add(cat_key)
        matched_keys = [k for k in instance_keys if k in cat_key or cat_key in k]
        for svc_key in matched_keys:
            if svc_key in _SERVICE_INSTANCE_DATA:
                inst_data = _SERVICE_INSTANCE_DATA[svc_key]
                for p_key in providers:
                    if p_key in inst_data:
                        instances = inst_data[p_key]
                        p_name = _CLOUD_PROVIDER_PRICING[p_key]["name"]
                        lines.append(f"")
                        lines.append(f"    {p_name}:")
                        lines.append(f"    {'Name':<20} {'vCPU':<9} {'Memory':<12} {'Cost':<18} {'Use case'}")
                        lines.append(f"    {'─' * 80}")
                        lines.extend(_format_instance_table(instances))

    if not service_categories:
        lines.append("")
        lines.extend([
            "General cost guidance:",
            "  - Pricing varies by region — always use your target region's rates",
            "  - Reserved / committed use (1-3yr) saves 30-70% vs on-demand",
            "  - Spot / preemptible / low-priority VMs save 60-90% for fault-tolerant workloads",
            "  - Data egress is a major hidden cost — minimize cross-region and internet transfer",
            "  - Use provider cost calculators (linked above) for accurate estimates",
            "",
            "For a precise comparison on a specific service or workload, ask the live LLM",
            '  e.g. "Compare AWS Lambda vs GCP Cloud Functions pricing for 10M requests/month with 512MB memory"',
        ])

    return "\n".join(lines)


def _wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    lines_out = []
    cur = ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines_out.append(cur)
            cur = w
        elif cur:
            cur += " " + w
        else:
            cur = w
    if cur:
        lines_out.append(cur)
    return lines_out


def _format_general_summary(payload: Dict[str, object], prompt: str, priority: str) -> str:
    title = payload.get("title") or "the uploaded HLDD"
    stack = ", ".join(str(item) for item in payload.get("technology_stack", []) if item) or "the selected stack"
    requirements = payload.get("functional_requirements") or []
    features = payload.get("features") or []
    stories = payload.get("stories") or []
    testing_stories = payload.get("testing_stories") or []
    management = payload.get("project_management_tool") or "Not specified"

    lines = [
        f"Project: {title}",
        "",
        f"Tech stack: {stack}",
        f"Management tool: {management}",
        f"Features: {len(features)}  |  Dev stories: {len(stories)}  |  Test stories: {len(testing_stories)}",
        "",
        "Functional requirements:",
    ]

    for r in requirements:
        lines.append(f"  - {r}")

    if not requirements:
        lines.append("  (none specified)")

    lines.append("")
    lines.append(f"You asked: \"{prompt}\"")
    lines.append("")
    lines.append("Tip: Try asking about backend alternatives, frontend options, cloud providers, or database choices for more specific recommendations.")

    return "\n".join(lines)


def build_local_response(payload: Dict[str, object], prompt: str, priority: str = "balanced") -> str:
    llm = recommend_llm(payload)
    question_type = _detect_question_type(prompt)

    intro = (
        f"Recommended model: {llm['provider']} {llm['model']} ({llm['reason']})"
        "\n---"
    )

    if question_type == "backend_alternative":
        body = _format_backend_alternatives(payload, prompt)
    elif question_type == "backend_mobile":
        body = _format_backend_mobile_alternatives(payload, prompt)
    elif question_type == "backend_general":
        body = _format_backend_general(payload)
    elif question_type == "frontend_alternative":
        body = _format_frontend_alternatives(payload)
    elif question_type == "cloud_alternative":
        body = _format_cloud_alternatives(payload)
    elif question_type == "database_alternative":
        body = _format_database_alternatives(payload)
    elif question_type == "cost":
        body = _format_cost_comparison(payload, prompt)
    else:
        body = _format_general_summary(payload, prompt, priority)

    return f"{intro}\n\n{body}"


def fetch_json(url: str, headers: Dict[str, str], payload: Dict[str, object]):
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def call_openai(payload: Dict[str, object], prompt: str, priority: str = "balanced"):
    api_key = os.getenv("OPENAI_API_KEY")
    llm = recommend_llm(payload)

    if not api_key:
        return None, llm

    body = {
        "model": llm["model"],
        "messages": [
            {
                "role": "system",
                "content": "You are a delivery planning assistant for HLDD analysis. Respond with clear, practical guidance grounded in the uploaded HLDD context. Structure the answer with sections for Recommendation priority, Recommended setup, Alternatives, Efficiency, Security, Turnaround time, and Cost breakdown when the user asks for budget or pricing guidance. Prefer the selected priority when tradeoffs are competing: lowest cost, fastest time to market, or highest security.",
            },
            {
                "role": "user",
                "content": f"HLDD context:\n{build_chat_context(payload)}\n\nSelected priority:\n{priority}\n\nUser question:\n{prompt}",
            },
        ],
    }

    response = fetch_json(
        "https://api.openai.com/v1/chat/completions",
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        body,
    )

    return response["choices"][0]["message"]["content"], llm


def call_gemini(payload: Dict[str, object], prompt: str, priority: str = "balanced"):
    api_key = os.getenv("GEMINI_API_KEY")
    llm = recommend_llm(payload)

    if not api_key:
        return None, llm

    context = build_chat_context(payload)
    return call_gemini_dataflow(context, prompt, priority)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "HLDD AI Agent"}


class MCPRequest(BaseModel):
    tool: str
    arguments: dict = {}


@app.post("/mcp/call")
def mcp_endpoint(req: MCPRequest):
    """MCP tool dispatcher. Available: parse_hldd, generate_plan, ask_chatbot."""
    try:
        if req.tool == "parse_hldd":
            text = req.arguments.get("text", "")
            if not text:
                raise HTTPException(status_code=400, detail="Missing 'text' argument")
            parsed = parse_hldd_document(text)
            return {"result": parsed}

        elif req.tool == "generate_plan":
            data = req.arguments.get("data", {})
            plan = generate_project_plan(data)
            return {"result": plan}

        elif req.tool == "ask_chatbot":
            question = req.arguments.get("question", "")
            context = req.arguments.get("context", "")
            priority = req.arguments.get("priority", "balanced")
            response, _ = call_gemini_dataflow(context, question, priority)
            return {"result": response or "No response"}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown MCP tool: {req.tool}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP error: {e}")


@app.post("/api/upload")
async def upload_hldd(file: UploadFile = File(...)):
    try:
        raw_text = await _read_upload(file)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not raw_text or not raw_text.strip():
        raise HTTPException(status_code=400, detail="The uploaded document is empty.")

    parsed = parse_hldd_document(raw_text)
    payload = generate_project_plan(parsed)
    LATEST_PAYLOAD.clear()
    LATEST_PAYLOAD.update(payload)

    # Index raw HLDD text into vector store for RAG retrieval
    try:
        retriever.ingest(raw_text)
    except Exception:
        pass  # RAG indexing is non-critical; upload succeeds regardless

    return payload


@app.post("/api/chatbot")
def chatbot_agent(request: ChatbotRequest):
    payload = dict(LATEST_PAYLOAD)
    prompt = request.prompt.strip() or "Summarize the HLDD and outline the next delivery steps."
    priority = request.priority or "balanced"

    if not payload:
        return {
            "prompt": prompt,
            "priority": priority,
            "response": "Upload an HLDD document first so the chatbot can reference the extracted context.",
            "source": "placeholder",
            "recommended_llm": recommend_llm({}),
        }

    llm = recommend_llm(payload)

    if is_out_of_scope(prompt):
        return {
            "prompt": prompt,
            "priority": priority,
            "response": "Out of Scope Information",
            "source": "out_of_scope",
            "recommended_llm": llm,
        }

    if llm["provider"] == "Google Gemini":
        try:
            content, llm = call_gemini(payload, prompt, priority)
            if content:
                return {
                    "prompt": prompt,
                    "priority": priority,
                    "response": content,
                    "source": "live",
                    "recommended_llm": llm,
                }
        except (HTTPError, URLError, KeyError, ValueError):
            pass

    try:
        content, llm = call_openai(payload, prompt, priority)
        if content:
            return {
                "prompt": prompt,
                "priority": priority,
                "response": content,
                "source": "live",
                "recommended_llm": llm,
            }
    except (HTTPError, URLError, KeyError, ValueError):
        pass

    return {
        "prompt": prompt,
        "priority": priority,
        "response": build_local_response(payload, prompt, priority),
        "source": "fallback",
        "recommended_llm": llm,
    }


class AgentRequest(BaseModel):
    prompt: str
    hldd_text: str = ""
    history: list[Dict[str, str]] = []
    confirm: bool = False


class DownloadStructureRequest(BaseModel):
    project_structure: list[str] = []


class JiraCreateRequest(BaseModel):
    features: list[Dict[str, object]] = []


class JiraCreateStoriesRequest(BaseModel):
    stories: list[Dict[str, object]] = []
    epic_mapping: dict[str, str] = {}


class JiraCreateTestingRequest(BaseModel):
    testing_stories: list[Dict[str, object]] = []
    story_mapping: dict[str, str] = {}


class JiraConfirmRequest(BaseModel):
    plan: dict = {}


@app.post("/api/agent")
def agent_endpoint(request: AgentRequest):
    try:
        agent = build_agent()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    history_messages = []
    for msg in request.history or []:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            history_messages.append(HumanMessage(content=content))
        else:
            history_messages.append(AIMessage(content=content))

    history_messages.append(HumanMessage(content=request.prompt))

    state = AgentState(
        raw_hldd_text=request.hldd_text or "",
        parsed_hldd=None,
        project_plan=None,
        epic_mapping={},
        story_mapping={},
        messages=history_messages,
        user_input=request.prompt,
        jira_pending_scope=None,
        jira_confirmed=request.confirm,
    )

    try:
        result = agent.invoke(state, {"recursion_limit": 50})
    except Exception as e:
        err_str = str(e)
        if "rate_limit_exceeded" in err_str or "Request too large" in err_str:
            raise HTTPException(
                status_code=429,
                detail=f"Groq API rate limit exceeded. The prompt is too large for the free tier. "
                       f"Try a shorter HLDD document or upgrade your Groq plan. ({err_str[:200]})"
            )
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")

    last_message = result["messages"][-1].content if result["messages"] else ""

    jira_pending = result.get("jira_pending_scope")

    return {
        "response": last_message,
        "jira_pending": jira_pending if jira_pending else None,
        "state": {
            "parsed": result.get("parsed_hldd"),
            "plan": result.get("project_plan"),
            "epics": result.get("epic_mapping"),
            "stories": result.get("story_mapping"),
        },
    }


@app.post("/api/agent/confirm-jira")
def agent_confirm_jira(request: JiraConfirmRequest):
    """Execute batch JIRA creation after user approval."""
    plan = request.plan or {}
    if not plan:
        raise HTTPException(status_code=400, detail="No project plan provided.")

    try:
        from app.agent.tools import batch_create_jira
        result = batch_create_jira(plan)
        LATEST_PAYLOAD["epic_mapping"] = result["epic_mapping"]
        LATEST_PAYLOAD["story_mapping"] = result["story_mapping"]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JIRA batch creation failed: {e}")


@app.post("/api/extract-text")
async def extract_text(file: UploadFile = File(...)):
    try:
        raw_text = await _read_upload(file)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not raw_text or not raw_text.strip():
        raise HTTPException(status_code=400, detail="The uploaded document is empty.")

    return {"text": raw_text, "filename": file.filename or "upload"}


@app.post("/api/jira/create-testing-stories")
def jira_create_testing_stories(request: JiraCreateTestingRequest):
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")
    if not email or not api_token:
        raise HTTPException(
            status_code=400,
            detail="JIRA integration is not configured. Set JIRA_EMAIL and JIRA_API_TOKEN environment variables.",
        )

    base_url = "https://mylearningdata.atlassian.net"
    auth_header = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    results = []

    for ts in (request.testing_stories or []):
        title = ts.get("title", "Untitled testing story")
        description = ts.get("description") or ""
        test_id = ts.get("id") or ""
        related_story_id = ts.get("related_story_id") or ""
        parent_story_key = request.story_mapping.get(related_story_id, "")

        fields = {
            "project": {"key": "SCRUM"},
            "summary": f"[{test_id}] {title}",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": description}
                        ],
                    }
                ],
            },
            "issuetype": {"id": "10002"},  # Subtask
        }

        if parent_story_key:
            fields["parent"] = {"key": parent_story_key}

        body = json.dumps({"fields": fields})

        try:
            req = Request(
                f"{base_url}/rest/api/3/issue",
                data=body.encode("utf-8"),
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                results.append({
                    "test_id": test_id,
                    "title": title,
                    "jira_key": result.get("key"),
                    "jira_url": f"{base_url}/browse/{result.get('key')}",
                    "parent_story": parent_story_key,
                    "success": True,
                })
        except (HTTPError, URLError) as e:
            detail = str(e)
            if isinstance(e, HTTPError):
                try:
                    detail = e.read().decode("utf-8")
                except Exception:
                    pass
            results.append({
                "test_id": test_id,
                "title": title,
                "parent_story": parent_story_key,
                "success": False,
                "error": detail,
            })

    success_count = sum(1 for r in results if r["success"])
    return {
        "results": results,
        "total": len(results),
        "success_count": success_count,
        "failure_count": len(results) - success_count,
    }


@app.post("/api/jira/create-stories")
def jira_create_stories(request: JiraCreateStoriesRequest):
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")
    if not email or not api_token:
        raise HTTPException(
            status_code=400,
            detail="JIRA integration is not configured. Set JIRA_EMAIL and JIRA_API_TOKEN environment variables.",
        )

    base_url = "https://mylearningdata.atlassian.net"
    auth_header = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    results = []

    for story in (request.stories or []):
        title = story.get("title", "Untitled story")
        description = story.get("description") or ""
        story_id = story.get("id") or ""
        feature_id = story.get("feature_id") or ""
        parent_epic_key = request.epic_mapping.get(feature_id, "")

        fields = {
            "project": {"key": "SCRUM"},
            "summary": f"[{story_id}] {title}",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": description}
                        ],
                    }
                ],
            },
            "issuetype": {"id": "10004"},  # Story
        }

        if parent_epic_key:
            fields["parent"] = {"key": parent_epic_key}

        body = json.dumps({"fields": fields})

        try:
            req = Request(
                f"{base_url}/rest/api/3/issue",
                data=body.encode("utf-8"),
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                results.append({
                    "story_id": story_id,
                    "title": title,
                    "jira_key": result.get("key"),
                    "jira_url": f"{base_url}/browse/{result.get('key')}",
                    "parent_epic": parent_epic_key,
                    "success": True,
                })
        except (HTTPError, URLError) as e:
            detail = str(e)
            if isinstance(e, HTTPError):
                try:
                    detail = e.read().decode("utf-8")
                except Exception:
                    pass
            results.append({
                "story_id": story_id,
                "title": title,
                "parent_epic": parent_epic_key,
                "success": False,
                "error": detail,
            })

    success_count = sum(1 for r in results if r["success"])
    return {
        "results": results,
        "total": len(results),
        "success_count": success_count,
        "failure_count": len(results) - success_count,
    }


@app.post("/api/jira/create-features")
def jira_create_features(request: JiraCreateRequest):
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")
    if not email or not api_token:
        raise HTTPException(
            status_code=400,
            detail="JIRA integration is not configured. Set JIRA_EMAIL and JIRA_API_TOKEN environment variables.",
        )

    base_url = "https://mylearningdata.atlassian.net"
    auth_header = base64.b64encode(f"{email}:{api_token}".encode()).decode()

    results = []
    for feature in (request.features or []):
        title = feature.get("title", "Untitled feature")
        description = feature.get("description") or ""
        feature_id = feature.get("id") or ""

        body = json.dumps({
            "fields": {
                "project": {"key": "SCRUM"},
                "summary": f"[{feature_id}] {title}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": description}
                            ],
                        }
                    ],
                },
                "issuetype": {"name": "Epic"},
            }
        })

        try:
            req = Request(
                f"{base_url}/rest/api/3/issue",
                data=body.encode("utf-8"),
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                results.append({
                    "feature_id": feature_id,
                    "title": title,
                    "jira_key": result.get("key"),
                    "jira_url": f"{base_url}/browse/{result.get('key')}",
                    "success": True,
                })
        except (HTTPError, URLError) as e:
            detail = str(e)
            if isinstance(e, HTTPError):
                try:
                    detail = e.read().decode("utf-8")
                except Exception:
                    pass
            results.append({
                "feature_id": feature_id,
                "title": title,
                "success": False,
                "error": detail,
            })

    success_count = sum(1 for r in results if r["success"])
    return {
        "results": results,
        "total": len(results),
        "success_count": success_count,
        "failure_count": len(results) - success_count,
    }


@app.post("/api/download/structure")
def download_structure(req: DownloadStructureRequest):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in req.project_structure:
            normalized = path.strip().replace("\\", "/")
            if normalized.endswith("/"):
                dirname = normalized.rstrip("/")
                zf.writestr(f"{dirname}/", "")
            else:
                zf.writestr(normalized, "")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=project-structure.zip"},
    )


@app.get("/api/hldd")
def get_latest_hldd():
    if not LATEST_PAYLOAD:
        return {
            "title": "No HLDD uploaded yet",
            "summary": "Upload a High Level Design Document to generate the dashboard and delivery plan.",
            "functional_requirements": [],
            "project_management_tool": "Not specified",
            "repository": "Not specified",
            "ci_cd_pipeline": "Not specified",
            "technology_stack": [],
            "acceptance_criteria": [],
            "architecture_notes": [],
            "architecture_diagram": {"nodes": [], "edges": []},
            "project_structure": [],
            "features": [],
            "stories": [],
            "testing_stories": [],
        }
    return LATEST_PAYLOAD
