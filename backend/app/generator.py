from typing import Dict
import re


def _estimate_story_points(text: str) -> int:
    words = len(re.findall(r"\w+", text))
    if words <= 14:
        return 1
    if words <= 28:
        return 2
    return 3


def _clamp_feature_title(text: str) -> str:
    title = re.sub(r"^[\-\*•\d\.\)\s]+", "", text.strip())
    title = title[:80].rstrip()
    return title or "Core HLDD Workflow"


def _suggest_cloud_services(stack_lower):
    if "aws" in stack_lower:
        return ["ECS", "EC2", "Lambda", "Amazon RDS for PostgreSQL", "Aurora DB"]
    if "azure" in stack_lower:
        return ["AKS", "App Service", "Azure Functions", "Azure Database for PostgreSQL"]
    if "gcp" in stack_lower or "google cloud" in stack_lower:
        return ["GKE", "Cloud Run", "Cloud Functions", "Cloud SQL for PostgreSQL"]
    return []


def _cloud_service_icons(service_name: str) -> str:
    icons = {
        "ECS": "🧩",
        "EC2": "🖥️",
        "Lambda": "⚡",
        "AKS": "🚀",
        "App Service": "🌐",
        "Azure Functions": "⚡",
        "GKE": "🚀",
        "Cloud Run": "☁️",
        "Cloud Functions": "⚡",
        "Amazon RDS for PostgreSQL": "🗄️",
        "Aurora DB": "🛢️",
        "Azure Database for PostgreSQL": "🗄️",
        "Cloud SQL for PostgreSQL": "🗄️",
    }
    return icons.get(service_name, "☁️")


def generate_project_plan(parsed: Dict[str, object]) -> Dict[str, object]:
    requirements = parsed.get("functional_requirements") or ["Core workflow implementation"]
    acceptance = parsed.get("acceptance_criteria") or ["The delivered feature matches the HLDD objectives."]
    stack = parsed.get("technology_stack") or ["React", "FastAPI"]
    management = parsed.get("project_management_tool") or "Not specified"
    repository = parsed.get("repository") or "Not specified"
    ci_cd_pipeline = parsed.get("ci_cd_pipeline") or "Not specified"

    stack_lower = [str(item).strip().lower() for item in stack if str(item).strip()]
    has_react = "react" in stack_lower
    has_angular = "angular" in stack_lower
    has_vue = "vue" in stack_lower
    has_fastapi = "fastapi" in stack_lower
    has_spring_boot = "spring boot" in stack_lower
    has_java = "java" in stack_lower
    has_node = "node" in stack_lower or "node.js" in stack_lower or "nodejs" in stack_lower
    has_python = "python" in stack_lower
    has_dotnet = ".net" in stack_lower or "dotnet" in stack_lower or "asp.net" in stack_lower
    has_oracle = "oracle" in stack_lower
    has_sql_server = "sql server" in stack_lower or "mssql" in stack_lower
    has_sql = "sql" in stack_lower and not has_sql_server
    has_postgresql = "postgresql" in stack_lower
    has_mysql = "mysql" in stack_lower
    has_mongodb = "mongodb" in stack_lower
    has_sqlite = "sqlite" in stack_lower
    has_frontend = has_react or has_angular or has_vue
    has_backend = has_fastapi or has_spring_boot or has_java or has_node or has_python or has_dotnet
    has_docker = "docker" in stack_lower
    has_aws = "aws" in stack_lower
    has_azure = "azure" in stack_lower
    has_gcp = "gcp" in stack_lower or "google cloud" in stack_lower
    has_kubernetes = "kubernetes" in stack_lower
    has_terraform = "terraform" in stack_lower
    has_cloud_runtime = has_aws or has_azure or has_gcp
    cloud_services = _suggest_cloud_services(stack_lower)

    data_nodes = []
    if has_oracle:
        data_nodes.append(("data_oracle", "Oracle Database"))
    if has_sql_server:
        data_nodes.append(("data_sqlserver", "SQL Server"))
    elif has_sql:
        data_nodes.append(("data_sql", "SQL"))
    if has_postgresql:
        data_nodes.append(("data_postgresql", "PostgreSQL"))
    if has_mysql:
        data_nodes.append(("data_mysql", "MySQL"))
    if has_mongodb:
        data_nodes.append(("data_mongodb", "MongoDB"))
    if has_sqlite:
        data_nodes.append(("data_sqlite", "SQLite"))
    if not data_nodes:
        data_nodes.append(("data", "Data Store"))

    primary_data_label = data_nodes[0][1]
    delivery_tool = management if management != "Not specified" else None
    frontend_label = "Angular UI" if has_angular else "React UI" if has_react else "Vue UI" if has_vue else "Frontend UI"
    cloud_label = "AWS Cloud" if has_aws else "Azure Cloud" if has_azure else "GCP Cloud" if has_gcp else "Cloud Platform"
    runtime_label = "Kubernetes Cluster" if has_kubernetes else None

    backend_nodes = []
    if has_dotnet:
        backend_nodes.append(("backend_dotnet", "ASP.NET Core APIs"))
    if has_spring_boot:
        backend_nodes.append(("backend_spring", "Spring Boot APIs"))
    if has_fastapi:
        backend_nodes.append(("backend_fastapi", "FastAPI Services"))
    if has_python:
        backend_nodes.append(("backend_python", "Python APIs"))
    if has_node:
        backend_nodes.append(("backend_nodejs", "Node.js APIs"))
    if has_java and not has_spring_boot:
        backend_nodes.append(("backend_java", "Java APIs"))
    if not backend_nodes:
        backend_nodes.append(("backend", "Backend Services"))

    features = []
    stories = []
    testing_stories = []
    story_counter = 1

    def _story_details(feature_title: str, task_label: str, task_description: str):
        title = f"{task_label} for {feature_title}"
        description = (
            f"{task_description} "
            f"Confirm the implementation meets the acceptance criteria for {feature_title.lower()} and is ready for review."
        )
        return title, description

    for index, requirement in enumerate(requirements[:4], start=1):
        feature_title = _clamp_feature_title(requirement)
        feature_id = f"IPMA#{index:03d}"
        feature_description = f"Deliver the {feature_title.lower()} workflow across the HLDD technology stack."
        feature_acceptance = acceptance[:2] if len(acceptance) >= 2 else acceptance + [f"{feature_title} is delivered and review-ready."]
        features.append(
            {
                "id": feature_id,
                "title": feature_title,
                "description": feature_description,
                "acceptance_criteria": feature_acceptance,
            }
        )

        story_tasks = []
        if has_react:
            story_tasks.append(
                (
                    "Build React UI flow",
                    f"Design and build the React UI flow needed for {feature_title.lower()}, including the user interactions and responsive view state.",
                )
            )
        if has_fastapi:
            story_tasks.append(
                (
                    "Implement FastAPI service",
                    f"Create the FastAPI route, validation, and response model required for {feature_title.lower()}, using the agreed request and response contract.",
                )
            )
        if primary_data_label:
            story_tasks.append(
                (
                    f"Persist data in {primary_data_label}",
                    f"Store, retrieve, and validate the {feature_title.lower()} data in {primary_data_label}, including the required data shape and query behavior.",
                )
            )
        if has_docker:
            story_tasks.append(
                (
                    "Update Docker packaging",
                    f"Update the Docker-related build and run steps so {feature_title.lower()} can be started and verified locally with the current stack.",
                )
            )
        if delivery_tool:
            story_tasks.append(
                (
                    f"Align delivery in {delivery_tool}",
                    f"Create the implementation notes and delivery checklist for {feature_title.lower()} so the work can be tracked and approved in {delivery_tool}.",
                )
            )

        if not story_tasks:
            story_tasks.append(
                (
                    "Implement core workflow",
                    f"Complete the implementation work required for {feature_title.lower()} and confirm the outcome is review-ready.",
                )
            )

        for task_label, task_description in story_tasks:
            story_title, story_description = _story_details(feature_title, task_label, task_description)
            story_points = _estimate_story_points(story_description)
            story_id = f"E-CRM#{story_counter:03d}"
            story_counter += 1
            stories.append(
                {
                    "id": story_id,
                    "feature_id": feature_id,
                    "title": story_title,
                    "description": story_description,
                    "acceptance_criteria": [
                        f"The task for {feature_title.lower()} is completed in the expected component.",
                        f"The deliverable supports the acceptance criteria for {feature_title.lower()}.",
                    ],
                    "story_points": min(3, story_points),
                    "type": "development",
                }
            )

            testing_stories.append(
                {
                    "id": f"TEST-{story_id}",
                    "related_story_id": story_id,
                    "title": f"Validate {story_title}",
                    "description": (
                        f"Execute validation for {story_title.lower()}, confirm the UI/API/data/container behavior is correct, and record any defects or follow-up actions before release."
                    ),
                    "acceptance_criteria": [
                        "Validation is completed for the associated development story.",
                        "Evidence is captured for the expected behavior and any defects are tracked.",
                    ],
                    "story_points": 1,
                }
            )

    if not features:
        features.append(
            {
                "id": "IPMA#001",
                "title": "Core HLDD implementation",
                "description": "Create the foundational workflow and dashboard for the uploaded HLDD.",
                "acceptance_criteria": acceptance[:2],
            }
        )

    architecture_nodes = []
    architecture_edges = []

    if has_frontend:
        architecture_nodes.append(
            {
                "id": "frontend",
                "label": frontend_label,
                "type": "frontend",
                "detail": f"The {frontend_label} hosts the workflows and dashboard views for the HLDD solution.",
            }
        )

    for backend_id, backend_label in backend_nodes:
        architecture_nodes.append(
            {
                "id": backend_id,
                "label": backend_label,
                "type": "backend",
                "detail": f"{backend_label} expose the APIs and processing logic used by the HLDD solution.",
            }
        )

    for data_id, data_label in data_nodes:
        architecture_nodes.append(
            {
                "id": data_id,
                "label": data_label,
                "type": "data",
                "detail": f"{data_label} stores and retrieves the structured artifacts and workflow data for the solution.",
            }
        )

    if has_cloud_runtime:
        architecture_nodes.append(
            {
                "id": "cloud",
                "label": cloud_label,
                "type": "cloud",
                "detail": f"{cloud_label} provides the managed infrastructure and platform services for the HLDD solution.",
            }
        )
    if repository != "Not specified":
        architecture_nodes.append(
            {
                "id": "repository",
                "label": repository,
                "type": "repository",
                "detail": f"{repository} is the source control location for the HLDD solution and the generated repository layout.",
            }
        )
    if has_kubernetes:
        architecture_nodes.append(
            {
                "id": "runtime",
                "label": runtime_label,
                "type": "runtime",
                "detail": "Kubernetes schedules and scales the runtime workloads that support the HLDD delivery pipeline.",
            }
        )
    if has_docker:
        architecture_nodes.append(
            {
                "id": "container",
                "label": "Docker Runtime",
                "type": "backend",
                "detail": "Docker packages and runs the application components so the HLDD workflow can be started and verified consistently.",
            }
        )
    if delivery_tool:
        architecture_nodes.append(
            {
                "id": "delivery",
                "label": f"Delivery with {delivery_tool}",
                "type": "backend",
                "detail": f"{delivery_tool} is used to track implementation work and approvals for the HLDD solution.",
            }
        )

    if has_frontend and backend_nodes:
        for backend_id, _ in backend_nodes:
            architecture_edges.append({"from": "frontend", "to": backend_id, "label": "UI to API workflow"})
    if backend_nodes and data_nodes:
        for backend_id, _ in backend_nodes:
            for data_id, _ in data_nodes:
                architecture_edges.append({"from": backend_id, "to": data_id, "label": "API to persistence"})
    if has_cloud_runtime and backend_nodes:
        for backend_id, _ in backend_nodes:
            architecture_edges.append({"from": "cloud", "to": backend_id, "label": "Hosts APIs"})
    if has_cloud_runtime and has_frontend:
        architecture_edges.append({"from": "cloud", "to": "frontend", "label": "Hosts UI"})
    if has_cloud_runtime and data_nodes:
        for data_id, _ in data_nodes:
            architecture_edges.append({"from": "cloud", "to": data_id, "label": "Managed data plane"})
    if has_cloud_runtime and has_docker:
        architecture_edges.append({"from": "cloud", "to": "container", "label": "Runs containerized services"})
    if repository != "Not specified" and has_frontend:
        architecture_edges.append({"from": "repository", "to": "frontend", "label": "Owns UI code"})
    if repository != "Not specified" and backend_nodes:
        for backend_id, _ in backend_nodes:
            architecture_edges.append({"from": "repository", "to": backend_id, "label": "Owns API code"})
    if has_kubernetes and backend_nodes:
        for backend_id, _ in backend_nodes:
            architecture_edges.append({"from": "runtime", "to": backend_id, "label": "Orchestrates APIs"})
    if has_kubernetes and has_frontend:
        architecture_edges.append({"from": "runtime", "to": "frontend", "label": "Scales UI workloads"})
    if has_kubernetes and has_docker:
        architecture_edges.append({"from": "runtime", "to": "container", "label": "Schedules containers"})
    if has_docker and has_frontend:
        architecture_edges.append({"from": "container", "to": "frontend", "label": "Runs UI container"})
    if has_docker and backend_nodes:
        for backend_id, _ in backend_nodes:
            architecture_edges.append({"from": "container", "to": backend_id, "label": "Runs API container"})
    if delivery_tool and has_frontend:
        architecture_edges.append({"from": "delivery", "to": "frontend", "label": "Track UI work"})
    if delivery_tool and backend_nodes:
        for backend_id, _ in backend_nodes:
            architecture_edges.append({"from": "delivery", "to": backend_id, "label": "Track API work"})
    if delivery_tool and data_nodes:
        for data_id, _ in data_nodes:
            architecture_edges.append({"from": "delivery", "to": data_id, "label": "Track data work"})

    diagram_lines = [
        "%%{init: {'theme': 'base', 'flowchart': {'curve': 'basis', 'nodeSpacing': 150, 'rankSpacing': 200}, 'themeVariables': {'primaryColor': '#0f172a', 'primaryTextColor': '#e2e8f0', 'primaryBorderColor': '#334155', 'lineColor': '#93c5fd', 'secondaryColor': '#111827', 'tertiaryColor': '#0b1120', 'fontSize': '15px'}}}%%",
        "flowchart LR",
        "    classDef frontend fill:#0f172a,stroke:#38bdf8,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18",
        "    classDef backend fill:#111827,stroke:#818cf8,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18",
        "    classDef data fill:#0b1120,stroke:#4ade80,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18",
        "    classDef container fill:#111827,stroke:#f59e0b,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18",
        "    classDef cloud fill:#111827,stroke:#38bdf8,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18",
        "    classDef runtime fill:#111827,stroke:#22d3ee,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18",
        "    classDef repository fill:#111827,stroke:#fbbf24,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18",
        "    classDef service fill:#111827,stroke:#f59e0b,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18",
        "    classDef delivery fill:#111827,stroke:#f472b6,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18",
        "    linkStyle default stroke:#93c5fd,stroke-width:2.2px",
        "",
    ]

    if has_frontend:
        diagram_lines.extend([
            "    subgraph UI[Presentation]",
            f"        frontend[\"🖥️ {frontend_label}\"]",
            "    end",
            "",
        ])
    if backend_nodes:
        diagram_lines.extend([
            "    subgraph API[Application]",
        ])
        for backend_id, backend_label in backend_nodes:
            diagram_lines.append(f"        {backend_id}[\"🔧 {backend_label}\"]")
        diagram_lines.extend([
            "    end",
            "",
        ])
    if data_nodes:
        diagram_lines.extend([
            "    subgraph DATA_LAYER[Persistence]",
        ])
        for data_id, data_label in data_nodes:
            diagram_lines.append(f"        {data_id}[\"🗄️ {data_label}\"]")
        diagram_lines.extend([
            "    end",
            "",
        ])
    if has_cloud_runtime:
        diagram_lines.extend([
            "    subgraph CLOUD[Cloud Platform]",
            f"        cloud[\"☁️ {cloud_label}\"]",
            "    end",
            "",
        ])
    if repository != "Not specified":
        diagram_lines.extend([
            "    subgraph REPO[Repository]",
            f"        repository[\"📦 {repository}\"]",
            "    end",
            "",
        ])
    if has_kubernetes:
        diagram_lines.extend([
            "    subgraph RUNTIME[Runtime Orchestration]",
            f"        runtime[\"🚀 {runtime_label}\"]",
            "    end",
            "",
        ])
    if has_docker:
        diagram_lines.extend([
            "    subgraph OPS[Runtime & Containers]",
            "        container[\"🐳 Docker Runtime\"]",
            "    end",
            "",
        ])
    if delivery_tool:
        diagram_lines.extend([
            "    subgraph DELIVERY_LAYER[Delivery Governance]",
            f"        delivery[\"📋 {delivery_tool}\"]",
            "    end",
            "",
        ])

    if has_frontend and backend_nodes:
        for backend_id, _ in backend_nodes:
            diagram_lines.append(f"    frontend -->|Calls| {backend_id}")
    if backend_nodes and data_nodes:
        for backend_id, _ in backend_nodes:
            for data_id, _ in data_nodes:
                diagram_lines.append(f"    {backend_id} -->|Stores| {data_id}")
    if has_cloud_runtime and backend_nodes:
        for backend_id, _ in backend_nodes:
            diagram_lines.append(f"    cloud -->|Hosts| {backend_id}")
    if has_cloud_runtime and has_frontend:
        diagram_lines.append("    cloud -->|Hosts| frontend")
    if has_cloud_runtime and data_nodes:
        for data_id, _ in data_nodes:
            diagram_lines.append(f"    cloud -->|Stores data| {data_id}")
    if has_cloud_runtime and has_docker:
        diagram_lines.append("    cloud -->|Runs containerized services| container")
    if repository != "Not specified" and has_frontend:
        diagram_lines.append("    repository -->|Owns UI code| frontend")
    if repository != "Not specified" and backend_nodes:
        for backend_id, _ in backend_nodes:
            diagram_lines.append(f"    repository -->|Owns API code| {backend_id}")
    if has_kubernetes and backend_nodes:
        for backend_id, _ in backend_nodes:
            diagram_lines.append(f"    runtime -->|Orchestrates| {backend_id}")
    if has_kubernetes and has_frontend:
        diagram_lines.append("    runtime -->|Scales| frontend")
    if has_kubernetes and has_docker:
        diagram_lines.append("    runtime -->|Schedules| container")
    if has_docker and has_frontend:
        diagram_lines.append("    container -->|Runs UI| frontend")
    if has_docker and backend_nodes:
        for backend_id, _ in backend_nodes:
            diagram_lines.append(f"    container -->|Runs APIs| {backend_id}")
    if delivery_tool and has_frontend:
        diagram_lines.append("    delivery -->|Tracks UI work| frontend")
    if delivery_tool and backend_nodes:
        for backend_id, _ in backend_nodes:
            diagram_lines.append(f"    delivery -->|Tracks API work| {backend_id}")
    if delivery_tool and data_nodes:
        for data_id, _ in data_nodes:
            diagram_lines.append(f"    delivery -->|Tracks data work| {data_id}")

    diagram_lines.append("")
    if has_frontend:
        diagram_lines.append("    class frontend frontend")
    if backend_nodes:
        for backend_id, _ in backend_nodes:
            diagram_lines.append(f"    class {backend_id} backend")
    if data_nodes:
        for data_id, _ in data_nodes:
            diagram_lines.append(f"    class {data_id} data")
    if has_cloud_runtime:
        diagram_lines.append("    class cloud cloud")
    if repository != "Not specified":
        diagram_lines.append("    class repository repository")
    if has_kubernetes:
        diagram_lines.append("    class runtime runtime")
    if has_docker:
        diagram_lines.append("    class container container")
    if delivery_tool:
        diagram_lines.append("    class delivery delivery")

    base_diagram = "\n".join(diagram_lines)
    expanded_diagram = base_diagram

    if has_cloud_runtime and cloud_services:
        expanded_lines = diagram_lines.copy()
        insert_index = next((index for index, line in enumerate(expanded_lines) if line.startswith("    subgraph OPS")), len(expanded_lines))
        service_nodes = []
        for service in cloud_services:
            service_id = service.lower().replace(" ", "_")
            service_nodes.append(f"        {service_id}[\"{_cloud_service_icons(service)} {service}\"]")

        expanded_lines[insert_index:insert_index] = [
            "    subgraph CLOUD_SERVICES[Recommended Services]",
            *service_nodes,
            "    end",
            "",
        ]
        expanded_lines.append("")
        for service in cloud_services:
            service_id = service.lower().replace(" ", "_")
            expanded_lines.append(f"    cloud -->|Runs| {service_id}")
        expanded_lines.append("")
        for service in cloud_services:
            service_id = service.lower().replace(" ", "_")
            expanded_lines.append(f"    class {service_id} service")
        expanded_diagram = "\n".join(expanded_lines)

    architecture_diagram = {
        "nodes": architecture_nodes,
        "edges": architecture_edges,
        "diagram": base_diagram,
        "expanded_diagram": expanded_diagram,
        "cloud_services": cloud_services,
        "legend": stack + ([management] if management != "Not specified" else []),
        "project_management_tool": management,
    }

    project_structure = [
        ".dockerignore",
        ".gitignore",
        ".github/workflows/frontend-ci.yml",
        ".github/workflows/backend-ci.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "README.md",
        "backend/requirements.txt",
        "backend/app/__init__.py",
        "backend/app/main.py",
        "backend/app/generator.py",
        "backend/app/parser.py",
        "backend/app/models.py",
        "backend/db/alembic/",
        "backend/db/seeds/",
        "backend/tests/__init__.py",
        "backend/tests/unit/",
        "backend/tests/integration/",
        "frontend/package.json",
        "frontend/vite.config.js",
        "frontend/public/",
        "frontend/src/App.jsx",
        "frontend/src/main.jsx",
        "frontend/src/index.css",
    ]

    if has_docker:
        project_structure.extend([
            "backend/Dockerfile",
            "docker-compose.yml",
        ])

    return {
        "title": parsed.get("title") or "HLDD Project",
        "summary": parsed.get("summary") or "Upload an HLDD document to generate a dashboard and delivery plan.",
        "functional_requirements": requirements,
        "project_management_tool": management,
        "repository": repository,
        "ci_cd_pipeline": ci_cd_pipeline,
        "technology_stack": stack,
        "acceptance_criteria": acceptance,
        "architecture_notes": parsed.get("architecture_notes") or ["The solution will show architecture relationships based on the uploaded design inputs."],
        "architecture_diagram": architecture_diagram,
        "project_structure": project_structure,
        "features": features,
        "stories": stories,
        "testing_stories": testing_stories,
    }
