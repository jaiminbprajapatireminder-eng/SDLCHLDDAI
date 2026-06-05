"""
MCP-compatible server for HLDD AI Agent.

Run standalone (stdio):  python -m app.mcp_server
Or access via HTTP:     POST http://localhost:8000/mcp/call
"""

import json
import sys

from app.parser import parse_hldd_document
from app.generator import generate_project_plan
from app.gemini_dataflow import call_gemini_dataflow


TOOLS = {
    "parse_hldd": {
        "description": "Parse HLDD text into structured sections",
        "input_schema": {"text": "str"},
    },
    "generate_plan": {
        "description": "Generate project plan from parsed HLDD JSON",
        "input_schema": {"data": "dict"},
    },
    "ask_chatbot": {
        "description": "Ask the legacy chatbot a question",
        "input_schema": {"question": "str", "context": "str", "priority": "str"},
    },
}


def handle_tool(tool: str, arguments: dict) -> dict:
    if tool == "parse_hldd":
        return {"result": parse_hldd_document(arguments.get("text", ""))}
    elif tool == "generate_plan":
        return {"result": generate_project_plan(arguments.get("data", {}))}
    elif tool == "ask_chatbot":
        response, _ = call_gemini_dataflow(
            arguments.get("context", ""),
            arguments.get("question", ""),
            arguments.get("priority", "balanced"),
        )
        return {"result": response}
    else:
        return {"error": f"Unknown tool: {tool}"}


def main():
    """Standalone stdio MCP server."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            tool = request.get("tool", "")
            args = request.get("arguments", {})
            result = handle_tool(tool, args)
            print(json.dumps(result), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)


if __name__ == "__main__":
    main()
