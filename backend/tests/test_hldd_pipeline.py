import unittest

from app.generator import generate_project_plan
from app.parser import parse_hldd_document


SAMPLE_HLDD = """# Sample HLDD Template

## Title
Sample HLDD for Customer Logistic Project

## Summary
This document describes the high-level design for a customer relationship management project.

## Functional Requirements
- Manage customer onboarding workflow
- Generate reporting dashboards
- Integrate with Logistic and billing systems

## Project Management Tool
- Jira

## Technology Stack
- Angular
- JAVA
- Spring Boot
- PostgreSQL
- AWS
- Docker

## Acceptance Criteria
- The onboarding workflow is documented and implemented
- Dashboards provide updated metrics
- Parcel Loading and billing integrations are working as expected

## Architecture Notes
- Frontend communicates with backend APIs
- Backend stores structured project artifacts
- AI Agent enriches HLDD parsing and planning
"""


class HlddPipelineTests(unittest.TestCase):
    def test_parser_preserves_all_technology_stack_items(self):
        parsed = parse_hldd_document(SAMPLE_HLDD)

        self.assertEqual(
            parsed["technology_stack"],
            ["Angular", "Java", "Spring Boot", "PostgreSQL", "AWS", "Docker"],
        )

    def test_generator_builds_frontend_and_backend_architecture_nodes(self):
        payload = generate_project_plan(parse_hldd_document(SAMPLE_HLDD))
        diagram = payload["architecture_diagram"]["diagram"]

        self.assertIn('frontend["🖥️ Angular UI"]', diagram)
        self.assertIn('backend_spring["🔧 Spring Boot APIs"]', diagram)
        self.assertIn('data_postgresql["🗄️ PostgreSQL"]', diagram)

    def test_generator_renders_explicit_cloud_runtime_nodes(self):
        payload = generate_project_plan(parse_hldd_document(SAMPLE_HLDD))
        diagram = payload["architecture_diagram"]["diagram"]

        self.assertIn('cloud["☁️ AWS Cloud"]', diagram)
        self.assertIn('container["🐳 Docker Runtime"]', diagram)
        self.assertIn('cloud -->|Runs containerized services| container', diagram)

    def test_generator_exposes_clickable_cloud_services(self):
        payload = generate_project_plan(parse_hldd_document(SAMPLE_HLDD))
        architecture = payload["architecture_diagram"]

        self.assertEqual(
            architecture["cloud_services"],
            ["ECS", "EC2", "Lambda", "Amazon RDS for PostgreSQL", "Aurora DB"],
        )
        self.assertIn('ecs["🧩 ECS"]', architecture["expanded_diagram"])
        self.assertIn('cloud -->|Runs| ecs', architecture["expanded_diagram"])

    def test_generator_recommends_provider_specific_database_services(self):
        payload = generate_project_plan(parse_hldd_document(SAMPLE_HLDD))
        architecture = payload["architecture_diagram"]

        self.assertIn("Amazon RDS for PostgreSQL", architecture["cloud_services"])
        self.assertIn("Aurora DB", architecture["cloud_services"])

    def test_generator_returns_azure_database_recommendation(self):
        payload = generate_project_plan(parse_hldd_document("""
        # Azure HLDD

        ## Title
        Azure-based HLDD

        ## Technology Stack
        - Angular
        - Java
        - Spring Boot
        - PostgreSQL
        - Azure
        - Docker
        """))

        architecture = payload["architecture_diagram"]

        self.assertIn("Azure Database for PostgreSQL", architecture["cloud_services"])
        self.assertIn('azure_database_for_postgresql["🗄️ Azure Database for PostgreSQL"]', architecture["expanded_diagram"])

    def test_google_cloud_is_preserved_and_generates_gcp_recommendations(self):
        payload = generate_project_plan(parse_hldd_document("""
        # Google Cloud HLDD

        ## Title
        Google Cloud HLDD

        ## Technology Stack
        - React
        - FastAPI
        - PostgreSQL
        - Google Cloud
        - Docker
        """))

        self.assertIn("Google Cloud", payload["technology_stack"])
        self.assertEqual(payload["architecture_diagram"]["cloud_services"], ["GKE", "Cloud Run", "Cloud Functions", "Cloud SQL for PostgreSQL"])
        self.assertIn('cloud["☁️ GCP Cloud"]', payload["architecture_diagram"]["diagram"])

    def test_parser_preserves_additional_stack_items_like_oracle_python_dotnet_and_sql(self):
        parsed = parse_hldd_document("""
        ## Technology Stack
        - Angular
        - Python
        - Oracle
        - .NET
        - SQL Server
        - GCP
        - Docker
        """)

        self.assertEqual(
            parsed["technology_stack"],
            ["Angular", "Python", "Oracle", ".NET", "SQL Server", "GCP", "Docker"],
        )

    def test_parser_extracts_pdf_like_inline_technology_stack_values(self):
        parsed = parse_hldd_document("""
        ## Technology Stack
        Azure, React, Python
        Azure Cloud
        Docker
        """)

        self.assertEqual(parsed["technology_stack"], ["Azure", "React", "Python", "Docker"])

    def test_parser_extracts_technology_stack_values_from_same_line_headers(self):
        parsed = parse_hldd_document("""
        ## Technology Stack: GCP, React, FastAPI
        """)

        self.assertEqual(parsed["technology_stack"], ["GCP", "React", "FastAPI"])

    def test_parser_extracts_technology_stack_values_from_bullet_headers_and_collapsed_text(self):
        parsed = parse_hldd_document("""
        * Technology Stack: Google Cloud, React, FastAPI
        """)

        self.assertEqual(parsed["technology_stack"], ["Google Cloud", "React", "FastAPI"])

    def test_parser_normalizes_azure_variants_and_collapsed_stack_lines(self):
        parsed = parse_hldd_document("""
        ## Technology Stack
        Microsoft Azure Cloud
        Azure React Python Docker
        Azure / React / Python / Docker
        """)

        self.assertEqual(parsed["technology_stack"], ["Azure", "React", "Python", "Docker"])

    def test_parser_reads_technology_stack_when_header_has_bullet_or_punctuation(self):
        parsed = parse_hldd_document("""
        * Technology Stack:
        GCP
        React
        FastAPI
        """)

        self.assertEqual(parsed["technology_stack"], ["GCP", "React", "FastAPI"])

    def test_project_structure_is_git_ready(self):
        payload = generate_project_plan(parse_hldd_document(SAMPLE_HLDD))

        self.assertIn(".gitignore", payload["project_structure"])
        self.assertIn("frontend/package.json", payload["project_structure"])
        self.assertIn("backend/requirements.txt", payload["project_structure"])

    def test_project_structure_matches_react_fastapi_postgresql_stack(self):
        payload = generate_project_plan(parse_hldd_document("""
        # React FastAPI HLDD

        ## Title
        React FastAPI PostgreSQL HLDD

        ## Technology Stack
        - React
        - FastAPI
        - PostgreSQL
        - Docker
        """))

        structure = set(payload["project_structure"])

        self.assertIn("frontend/src/App.jsx", structure)
        self.assertIn("frontend/src/main.jsx", structure)
        self.assertIn("frontend/package.json", structure)
        self.assertIn("frontend/vite.config.js", structure)
        self.assertIn("backend/app/main.py", structure)
        self.assertIn("backend/app/generator.py", structure)
        self.assertIn("backend/app/parser.py", structure)
        self.assertIn("backend/app/models.py", structure)
        self.assertIn("backend/db/alembic/", structure)
        self.assertIn("backend/db/seeds/", structure)
        self.assertIn("docker-compose.yml", structure)
        self.assertNotIn("frontend/src/App.tsx", structure)
        self.assertNotIn("frontend/src/features/auth/components/", structure)
        self.assertNotIn("backend/app/core/config.py", structure)
        self.assertNotIn("backend/app/core/security.py", structure)

    def test_project_structure_matches_active_stack_delivery_map(self):
        payload = generate_project_plan(parse_hldd_document("""
        # React FastAPI HLDD

        ## Title
        React FastAPI HLDD

        ## Technology Stack
        - React
        - FastAPI
        - PostgreSQL
        - Docker
        """))

        delivery_paths = {
            ".github/workflows/frontend-ci.yml",
            ".github/workflows/backend-ci.yml",
            ".github/PULL_REQUEST_TEMPLATE.md",
            "README.md",
            ".dockerignore",
            ".gitignore",
            "docker-compose.yml",
            "backend/Dockerfile",
            "backend/requirements.txt",
            "backend/app/main.py",
            "backend/app/generator.py",
            "backend/app/parser.py",
            "backend/app/models.py",
            "backend/db/alembic/",
            "backend/db/seeds/",
            "backend/tests/__init__.py",
            "frontend/package.json",
            "frontend/vite.config.js",
            "frontend/public/",
            "frontend/src/App.jsx",
            "frontend/src/main.jsx",
            "frontend/src/index.css",
        }

        self.assertTrue(delivery_paths.issubset(set(payload["project_structure"])))

    def test_parser_extracts_repository_and_cicd_configuration(self):
        parsed = parse_hldd_document("""
        ## Repository
        - Bitbucket

        ## CI/CD Pipeline
        - GitHub Actions

        ## Technology Stack
        - NodeJS
        - .NET
        - SQL Server
        """)

        self.assertEqual(parsed["repository"], "Bitbucket")
        self.assertEqual(parsed["ci_cd_pipeline"], "GitHub Actions")
        self.assertEqual(parsed["technology_stack"], ["Node.js", ".NET", "SQL Server"])

    def test_generator_maps_nodejs_dotnet_and_sql_server_in_architecture(self):
        payload = generate_project_plan(parse_hldd_document("""
        ## Title
        Mixed stack HLDD

        ## Technology Stack
        - NodeJS
        - .NET
        - SQL Server
        - Docker
        """))

        diagram = payload["architecture_diagram"]["diagram"]

        self.assertIn('backend_nodejs["🔧 Node.js APIs"]', diagram)
        self.assertIn('backend_dotnet["🔧 ASP.NET Core APIs"]', diagram)
        self.assertIn('data_sqlserver["🗄️ SQL Server"]', diagram)


if __name__ == "__main__":
    unittest.main()
