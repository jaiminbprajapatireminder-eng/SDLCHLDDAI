import base64
import json
import os
from typing import Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from langchain_core.tools import tool

from app.gemini_dataflow import call_gemini_dataflow
from app.generator import generate_project_plan
from app.parser import parse_hldd_document


@tool
def parse_hldd(raw_text: str) -> dict:
    """Parse an HLDD document into structured sections (title, requirements, tech stack, etc.)."""
    return parse_hldd_document(raw_text)


@tool
def generate_plan(hldd_data_json: str) -> dict:
    """Generate a project plan (features, stories, tests) from parsed HLDD JSON."""
    import json
    parsed = json.loads(hldd_data_json) if isinstance(hldd_data_json, str) else hldd_data_json
    return generate_project_plan(parsed)


@tool
def parse_and_generate_plan(raw_hldd_text: str) -> dict:
    """Parse HLDD and generate a project plan in one step (preferred)."""
    parsed = parse_hldd_document(raw_hldd_text)
    return generate_project_plan(parsed)


@tool
def ask_gemini(question: str, context_str: str) -> str:
    """Ask Gemini about the project, tech comparisons, or recommendations."""
    try:
        response, _ = call_gemini_dataflow(context_str, question, "balanced")
        return response or "Gemini returned an empty response."
    except Exception as e:
        return f"Gemini API error: {e}"


@tool
def request_jira_creation(scope: str) -> str:
    """Request user approval to create JIRA items. Call this BEFORE creating any JIRA items.

    The user MUST approve before any JIRA items are created. Call this with scope="all"
    to create Epics for all features, Stories for all features, and Subtasks for all stories.
    After user approval, the system will create everything in batch.

    Args:
        scope: Must be "all" to create Epics, Stories, and Subtasks together.
    """
    return f"JIRA_CREATION_REQUEST:{scope}"


def _jira_create_issue(fields: dict) -> str:
    """Internal helper to create a JIRA issue. Not exposed as a tool."""
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")
    if not email or not api_token:
        return "Error: JIRA_EMAIL and JIRA_API_TOKEN environment variables are not set."

    base_url = "https://mylearningdata.atlassian.net"
    auth_header = base64.b64encode(f"{email}:{api_token}".encode()).decode()

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
            return result.get("key", "Unknown")
    except (HTTPError, URLError) as e:
        detail = str(e)
        if isinstance(e, HTTPError):
            try:
                detail = e.read().decode("utf-8")
            except Exception:
                pass
        return f"Error: {detail}"


def _jira_create_epic(feature_id: str, name: str, description: str) -> str:
    """Create a JIRA Epic for a feature. Internal function, not a tool."""
    return _jira_create_issue({
        "project": {"key": "SCRUM"},
        "summary": f"[{feature_id}] {name}",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
        },
        "issuetype": {"name": "Epic"},
    })


def _jira_create_story(story_id: str, title: str, description: str, epic_key: str) -> str:
    """Create a Story in JIRA linked to a parent Epic. Internal function, not a tool."""
    fields = {
        "project": {"key": "SCRUM"},
        "summary": f"[{story_id}] {title}",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
        },
        "issuetype": {"id": "10004"},
    }
    if epic_key:
        fields["parent"] = {"key": epic_key}
    return _jira_create_issue(fields)


def _jira_create_subtask(test_id: str, title: str, description: str, parent_key: str) -> str:
    """Create a Subtask in JIRA linked to a parent Story. Internal function, not a tool."""
    fields = {
        "project": {"key": "SCRUM"},
        "summary": f"[{test_id}] {title}",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
        },
        "issuetype": {"id": "10002"},
    }
    if parent_key:
        fields["parent"] = {"key": parent_key}
    return _jira_create_issue(fields)


def batch_create_jira(project_plan: dict) -> dict:
    """Batch-create all JIRA items from a project plan. Called after user approval."""
    from app.agent.state import AgentState

    features = project_plan.get("features", [])
    stories = project_plan.get("stories", [])
    testing_stories = project_plan.get("testing_stories", [])

    epic_mapping = {}
    story_mapping = {}

    results = {"epics": [], "stories": [], "testing": []}

    for feature in features:
        key = _jira_create_epic(
            feature["id"],
            feature.get("title", ""),
            feature.get("description", ""),
        )
        epic_mapping[feature["id"]] = key
        results["epics"].append({"feature_id": feature["id"], "jira_key": key})

    for story in stories:
        epic_key = epic_mapping.get(story.get("feature_id", ""), "")
        key = _jira_create_story(
            story["id"],
            story.get("title", ""),
            story.get("description", ""),
            epic_key,
        )
        story_mapping[story["id"]] = key
        results["stories"].append({"story_id": story["id"], "jira_key": key, "parent_epic": epic_key})

    for test in testing_stories:
        parent_key = story_mapping.get(test.get("related_story_id", ""), "")
        key = _jira_create_subtask(
            test["id"],
            test.get("title", ""),
            test.get("description", ""),
            parent_key,
        )
        results["testing"].append({"test_id": test["id"], "jira_key": key, "parent_story": parent_key})

    return {
        "results": results,
        "epic_mapping": epic_mapping,
        "story_mapping": story_mapping,
    }


@tool
def retrieve_hldd_context(question: str) -> str:
    """Retrieve relevant HLDD document chunks using vector search. Use this to find specific details in the HLDD instead of relying on truncated text."""
    try:
        from app.rag import retriever
        result = retriever.retrieve(question)
        return result if result else "No relevant context found in the HLDD document."
    except Exception as e:
        return f"Retrieval error: {e}"


@tool
def mcp_call(tool_name: str, arguments: str) -> str:
    """Call an external MCP tool. Available MCP tools: parse_hldd (parse HLDD text into structured data), generate_plan (generate project plan from parsed JSON), ask_chatbot (ask the legacy chatbot a question with context). Pass tool_name and arguments as a JSON string."""
    try:
        import json
        from urllib.request import Request, urlopen
        args = json.loads(arguments) if isinstance(arguments, str) else arguments
        body = json.dumps({"tool": tool_name, "arguments": args}).encode("utf-8")
        req = Request(
            "http://localhost:8000/mcp/call",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return json.dumps(result, indent=2)
    except Exception as e:
        return f"MCP call error: {e}"


TOOLS = [
    parse_and_generate_plan,
    ask_gemini,
    retrieve_hldd_context,
    mcp_call,
    request_jira_creation,
]
