import re
from typing import Dict, List, Optional


SECTION_HEADERS = {
    "functional_requirements": ["functional requirement", "functional requirements"],
    "project_management_tool": ["project management tool", "project management", "management tool"],
    "repository": ["repository", "repo"],
    "ci_cd_pipeline": ["ci/cd pipeline", "ci cd pipeline", "pipeline", "cicd pipeline"],
    "technology_stack": ["technology stack", "tech stack", "stack"],
    "acceptance_criteria": ["acceptance criteria", "acceptance"],
    "architecture_notes": ["architecture", "architecture diagram", "system design"],
}

KNOWN_TOOLS = [
    "jira",
    "azure devops",
    "trello",
    "asana",
    "clickup",
    "notion",
    "linear",
]

KNOWN_TECH = [
    "react",
    "fastapi",
    "python",
    "docker",
    "postgres",
    "postgresql",
    "mysql",
    "mongodb",
    "next.js",
    "node",
    "node.js",
    "nodejs",
    "vue",
    "azure",
    "aws",
    "kubernetes",
    "angular",
    "express",
    "typescript",
    "java",
    "spring boot",
    "oracle",
    "oracle database",
    ".net",
    "dotnet",
    "sql",
    "sql server",
    "sql database",
    "mssql",
    "gcp",
    "google cloud",
    "google cloud platform",
]

TECHNOLOGY_ALIASES = {
    "angular": "Angular",
    "java": "Java",
    "spring boot": "Spring Boot",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "aws": "AWS",
    "docker": "Docker",
    "react": "React",
    "express": "Express",
    "typescript": "TypeScript",
    "fastapi": "FastAPI",
    "python": "Python",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "next.js": "Next.js",
    "node": "Node.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "node js": "Node.js",
    "vue": "Vue",
    "azure": "Azure",
    "azure cloud": "Azure",
    "microsoft azure": "Azure",
    "kubernetes": "Kubernetes",
    "google cloud": "Google Cloud",
    "google cloud platform": "Google Cloud",
    "gcp": "GCP",
    "oracle": "Oracle",
    "oracle database": "Oracle",
    ".net": ".NET",
    "dotnet": ".NET",
    "asp.net": ".NET",
    "sql": "SQL",
    "sql database": "SQL",
    "sql server": "SQL Server",
    "mssql": "SQL Server",
}

KNOWN_REPOSITORIES = ["git", "github", "gitlab", "bitbucket", "azure repos", "azure repo", "svn"]
KNOWN_CICD_PIPELINES = [
    "github actions",
    "github workflow",
    "gitlab ci",
    "bitbucket pipelines",
    "azure pipelines",
    "jenkins",
    "circleci",
    "teamcity",
    "argo cd",
]


def _clean_text(text: str) -> str:
    return re.sub(r"\r\n", "\n", text).strip()


def _is_bullet(line: str) -> bool:
    return bool(re.match(r"^([\-\*•]|\d+[\.)])\s+", line.strip()))


def _strip_bullet(line: str) -> str:
    return re.sub(r"^([\-\*•]|\d+[\.)])\s+", "", line).strip()


def _extract_title(line: str) -> str:
    stripped = re.sub(r"^#+\s*", "", line).strip()
    if stripped.lower().startswith("title:"):
        return stripped.split(":", 1)[1].strip()
    return stripped


def _match_section(lowered: str) -> Optional[str]:
    for section_name, markers in SECTION_HEADERS.items():
        if any(marker in lowered for marker in markers):
            return section_name
    return None


def _extract_section_payload(line: str) -> Optional[tuple[str, str]]:
    cleaned = re.sub(r"^#+\s*", "", line).strip()
    cleaned = _strip_bullet(cleaned).strip()
    lowered = cleaned.lower()

    for section_name, markers in SECTION_HEADERS.items():
        for marker in markers:
            pattern = re.compile(rf"^{re.escape(marker)}\s*[:\-]?\s*(.*)$", re.IGNORECASE)
            match = pattern.match(cleaned)
            if match:
                return section_name, match.group(1).strip()

    return None


def _normalize_technology(line: str) -> Optional[str]:
    cleaned = _strip_bullet(line).strip()
    if not cleaned:
        return None

    cleaned = re.sub(r"\s+", " ", cleaned)
    lowered = cleaned.lower()

    if lowered in TECHNOLOGY_ALIASES:
        return TECHNOLOGY_ALIASES[lowered]

    if lowered == "azure" or "azure" in lowered:
        if "azure devops" in lowered:
            return "Azure"
        if lowered in {"azure cloud", "azure cloud platform", "microsoft azure", "microsoft azure cloud"}:
            return "Azure"
        return "Azure"

    if "nodejs" in lowered or "node js" in lowered:
        return "Node.js"

    if "postgres" in lowered:
        return "PostgreSQL"

    if "spring" in lowered and "boot" in lowered:
        return "Spring Boot"

    matched_keyword = None
    for keyword in sorted(KNOWN_TECH, key=len, reverse=True):
        if keyword in lowered:
            matched_keyword = keyword
            break

    if matched_keyword:
        alias_key = matched_keyword
        return TECHNOLOGY_ALIASES.get(alias_key, matched_keyword.title() if matched_keyword.islower() else matched_keyword)

    return None


def _split_technology_candidates(line: str) -> List[str]:
    cleaned = _strip_bullet(line).strip()
    if not cleaned:
        return []

    normalized = re.sub(r"\s+", " ", cleaned)
    lowered = normalized.lower()

    if any(separator in normalized for separator in [",", ";", "|", "/"]):
        return [item.strip() for item in re.split(r"[,;|/]", normalized) if item.strip()]

    terms = set(TECHNOLOGY_ALIASES.keys()) | set(KNOWN_TECH)
    matches = []
    used_ranges = []

    for phrase in sorted(terms, key=len, reverse=True):
        pattern = re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(lowered):
            if any(not (match.end() <= start or match.start() >= end) for start, end in used_ranges):
                continue
            matches.append((match.start(), match.end(), phrase))
            used_ranges.append((match.start(), match.end()))

    if matches:
        return [phrase for _, _, phrase in sorted(matches, key=lambda item: item[0])]

    found = []
    for phrase in sorted(terms, key=len, reverse=True):
        if phrase in lowered:
            found.append(phrase)
            lowered = lowered.replace(phrase, " " * len(phrase), 1)

    if found:
        seen = set()
        unique = []
        for item in found:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique

    return []


def _match_tool(line: str) -> Optional[str]:
    lowered = line.lower()
    for tool in KNOWN_TOOLS:
        if tool in lowered:
            return tool.title()
    return None


def _normalize_repository(line: str) -> Optional[str]:
    cleaned = _strip_bullet(line).strip()
    if not cleaned:
        return None

    lowered = cleaned.lower()
    if lowered == "git":
        return "Git"
    if lowered in {"github", "github repo", "github repository"}:
        return "GitHub"
    if lowered in {"gitlab", "gitlab repo", "gitlab repository"}:
        return "GitLab"
    if lowered in {"bitbucket", "bitbucket repo", "bitbucket repository"}:
        return "Bitbucket"
    if lowered in {"azure repos", "azure repo", "azure repository"}:
        return "Azure Repos"
    if lowered == "svn":
        return "SVN"
    return None


def _normalize_cicd_pipeline(line: str) -> Optional[str]:
    cleaned = _strip_bullet(line).strip()
    if not cleaned:
        return None

    lowered = cleaned.lower()
    if lowered in {"github actions", "github workflow"}:
        return "GitHub Actions"
    if lowered == "gitlab ci":
        return "GitLab CI"
    if lowered == "bitbucket pipelines":
        return "Bitbucket Pipelines"
    if lowered == "azure pipelines":
        return "Azure Pipelines"
    if lowered == "jenkins":
        return "Jenkins"
    if lowered == "circleci":
        return "CircleCI"
    if lowered == "teamcity":
        return "TeamCity"
    if lowered == "argo cd":
        return "Argo CD"
    return None


def parse_hldd_document(text: str) -> Dict[str, object]:
    text = _clean_text(text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    title = "HLDD Project"
    for line in lines:
        lowered = line.lower()
        if lowered.startswith("title:") or lowered.startswith("project:"):
            title = _extract_title(line)
            break
        if line.startswith("#"):
            title = _extract_title(line)
            break

    functional_requirements = []
    project_management_tool = "Not specified"
    repository = "Not specified"
    ci_cd_pipeline = "Not specified"
    technology_stack = []
    acceptance_criteria = []
    architecture_notes = []

    current_section = None
    for line in lines:
        lowered = line.lower()
        section_payload = _extract_section_payload(line)

        if section_payload:
            current_section, inline_content = section_payload
            if inline_content:
                if current_section == "technology_stack":
                    for candidate in _split_technology_candidates(inline_content):
                        normalized = _normalize_technology(candidate)
                        if normalized and normalized not in technology_stack:
                            technology_stack.append(normalized)
                elif current_section == "functional_requirements":
                    if inline_content not in functional_requirements:
                        functional_requirements.append(inline_content)
                elif current_section == "acceptance_criteria":
                    if inline_content not in acceptance_criteria:
                        acceptance_criteria.append(inline_content)
                elif current_section == "project_management_tool":
                    project_management_tool = inline_content
                elif current_section == "repository":
                    normalized_repository = _normalize_repository(inline_content)
                    if normalized_repository:
                        repository = normalized_repository
                elif current_section == "ci_cd_pipeline":
                    normalized_pipeline = _normalize_cicd_pipeline(inline_content)
                    if normalized_pipeline:
                        ci_cd_pipeline = normalized_pipeline
                elif current_section == "architecture_notes":
                    architecture_notes.append(inline_content)
            continue

        if re.search(r"\btechnology stack\b|\btech stack\b", lowered):
            current_section = "technology_stack"
            continue

        if re.search(r"\bfunctional requirements\b", lowered):
            current_section = "functional_requirements"
            continue

        if re.search(r"\bacceptance criteria\b", lowered):
            current_section = "acceptance_criteria"
            continue

        if re.search(r"\bproject management tool\b", lowered):
            current_section = "project_management_tool"
            continue

        if re.search(r"\brepository\b|\brepo\b", lowered):
            current_section = "repository"
            continue

        if re.search(r"\bci/cd pipeline\b|\bci cd pipeline\b|\bcicd pipeline\b|\bpipeline\b", lowered):
            current_section = "ci_cd_pipeline"
            continue

        if re.search(r"\barchitecture\b|\barchitecture diagram\b|\bsystem design\b", lowered):
            current_section = "architecture_notes"
            continue

        if re.match(r"^#+", line):
            current_section = _match_section(lowered)
            continue

        if lowered in {"functional requirements", "acceptance criteria", "technology stack", "tech stack", "project management tool", "repository", "repo", "ci/cd pipeline", "ci cd pipeline", "pipeline", "cicd pipeline", "architecture", "architecture diagram", "system design"}:
            current_section = _match_section(lowered)
            continue

        tool = _match_tool(line)
        if tool:
            project_management_tool = tool

        if current_section == "functional_requirements":
            if _is_bullet(line):
                functional_requirements.append(_strip_bullet(line))
            elif line and not line.lower().startswith("functional requirements"):
                functional_requirements.append(line)
        elif current_section == "acceptance_criteria":
            if _is_bullet(line):
                acceptance_criteria.append(_strip_bullet(line))
            elif line and not line.lower().startswith("acceptance criteria"):
                acceptance_criteria.append(line)
        elif current_section == "technology_stack":
            for candidate in _split_technology_candidates(line):
                normalized = _normalize_technology(candidate)
                if normalized and normalized not in technology_stack:
                    technology_stack.append(normalized)
        elif current_section == "architecture_notes":
            if _is_bullet(line):
                architecture_notes.append(_strip_bullet(line))
            elif line:
                architecture_notes.append(line)
        elif current_section == "project_management_tool":
            if _is_bullet(line):
                tool_value = _strip_bullet(line)
                if tool_value:
                    project_management_tool = tool_value
        elif current_section == "repository":
            normalized_repository = _normalize_repository(line)
            if normalized_repository:
                repository = normalized_repository
        elif current_section == "ci_cd_pipeline":
            normalized_pipeline = _normalize_cicd_pipeline(line)
            if normalized_pipeline:
                ci_cd_pipeline = normalized_pipeline

    if not functional_requirements:
        for line in lines:
            if _is_bullet(line) and any(keyword in line.lower() for keyword in ["feature", "requirement", "workflow", "module", "process"]):
                functional_requirements.append(_strip_bullet(line))

    if not technology_stack:
        for line in lines:
            for candidate in _split_technology_candidates(line):
                normalized = _normalize_technology(candidate)
                if normalized and normalized not in technology_stack:
                    technology_stack.append(normalized)

    if repository == "Not specified":
        for line in lines:
            normalized_repository = _normalize_repository(line)
            if normalized_repository:
                repository = normalized_repository
                break

    if ci_cd_pipeline == "Not specified":
        for line in lines:
            normalized_pipeline = _normalize_cicd_pipeline(line)
            if normalized_pipeline:
                ci_cd_pipeline = normalized_pipeline
                break

    if not acceptance_criteria:
        acceptance_criteria = [
            "The solution satisfies the documented business objective and is ready for review.",
            "The deliverable is traceable to the uploaded HLDD requirements.",
        ]

    if project_management_tool == "Not specified":
        for line in lines:
            tool = _match_tool(line)
            if tool:
                project_management_tool = tool
                break

    summary = "\n".join(lines[:8])
    if len(summary) > 700:
        summary = summary[:700] + "..."

    normalized_stack = []
    for item in technology_stack:
        cleaned = _strip_bullet(item)
        if cleaned and cleaned not in normalized_stack:
            normalized_stack.append(cleaned)

    return {
        "title": title,
        "summary": summary,
        "functional_requirements": [item for item in functional_requirements if item],
        "project_management_tool": project_management_tool,
        "repository": repository,
        "ci_cd_pipeline": ci_cd_pipeline,
        "technology_stack": normalized_stack,
        "acceptance_criteria": [item for item in acceptance_criteria if item],
        "architecture_notes": [item for item in architecture_notes if item],
    }
