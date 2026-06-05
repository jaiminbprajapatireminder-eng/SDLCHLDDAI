import json

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from .state import AgentState
from .tools import TOOLS
from .llm import build_agent_llm
from .prompts import AGENT_SYSTEM_PROMPT
from app.parser import parse_hldd_document
from app.generator import generate_project_plan


def agent_node(state: AgentState):
    llm = build_agent_llm(TOOLS)

    raw_text = (state.get("raw_hldd_text") or "")
    parsed_hldd = state.get("parsed_hldd")
    project_plan = state.get("project_plan")

    updates = {}
    if raw_text and not parsed_hldd:
        try:
            parsed_hldd = parse_hldd_document(raw_text)
            project_plan = generate_project_plan(parsed_hldd)
            updates["parsed_hldd"] = parsed_hldd
            updates["project_plan"] = project_plan
        except Exception:
            pass

    context_block = ""
    if parsed_hldd:
        p = parsed_hldd
        summary_preview = (p.get("summary") or "")[:700]
        fr_list = p.get("functional_requirements", [])
        fr_preview = ', '.join((f if isinstance(f, str) else f.get('id', str(f)))[:60] for f in fr_list[:6])
        ac_list = p.get("acceptance_criteria", [])
        ac_first = (ac_list[0] if ac_list else 'N/A')[:80]
        context_block += f"""
## Parsed HLDD Document
Title: {p.get('title', 'N/A')}
Summary: {summary_preview + ('...' if len(p.get('summary') or '') > 700 else '')}
Tech Stack: {', '.join(p.get('technology_stack', ['N/A']))}
Functional Requirements ({len(fr_list)}): {fr_preview}{'...' if len(fr_list) > 6 else ''}
Acceptance Criteria ({len(ac_list)}): {ac_first}{'...' if len(ac_list) > 1 else ''}

Architecture Notes:
{p.get('architecture_notes', 'N/A')[:500]}
"""
    if project_plan:
        plan = project_plan
        features = plan.get("features", [])
        stories = plan.get("stories", [])
        testing_stories = plan.get("testing_stories", [])
        context_block += f"""
## Project Plan
Features ({len(features)}): {', '.join(f.get('id', '') + ': ' + (f.get('title', '') or '')[:60] for f in features[:5])}{'...' if len(features) > 5 else ''}
Development Stories: {len(stories)}
Testing Stories: {len(testing_stories)}
"""

    system_msg = AGENT_SYSTEM_PROMPT + context_block

    # Keep only the last 6 messages + system to stay within token limits
    recent_msgs = state["messages"]
    if len(recent_msgs) > 6:
        recent_msgs = recent_msgs[-6:]

    messages = [{"role": "system", "content": system_msg}]
    for msg in recent_msgs:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            text = msg.content or ""
            if len(text) > 500:
                text = text[:500] + "...[truncated]"
            d = {"role": "assistant", "content": text}
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                d["tool_calls"] = [
                    {
                        "id": tc.id if hasattr(tc, "id") else tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc.name if hasattr(tc, "name") else tc.get("name", ""),
                            "arguments": json.dumps(tc.args if hasattr(tc, "args") else tc.get("args", {})),
                        },
                    }
                    for tc in (msg.tool_calls or [])
                ]
            messages.append(d)
        elif isinstance(msg, ToolMessage):
            text = msg.content or ""
            if len(text) > 600:
                text = text[:600] + "...[truncated]"
            messages.append({"role": "tool", "content": text, "tool_call_id": msg.tool_call_id})
        else:
            messages.append({"role": "user", "content": str(msg.content) if hasattr(msg, 'content') else str(msg)})

    response = llm.invoke(messages)
    result = {"messages": [response]}
    result.update(updates)
    return result


def process_tool_results(state: AgentState):
    """Extract parsed_hldd and project_plan from the last tool message."""
    messages = state.get("messages", [])
    if not messages:
        return {}

    updates = {}
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            continue
        try:
            data = json.loads(msg.content)
            if isinstance(data, dict):
                if "features" in data or "stories" in data:
                    updates["project_plan"] = data
                if "title" in data and "functional_requirements" in data:
                    updates["parsed_hldd"] = data
        except (json.JSONDecodeError, TypeError):
            pass
    return updates


def get_tc_name(tc):
    if isinstance(tc, dict):
        return tc.get("name", "")
    return tc.name if hasattr(tc, "name") else ""


def get_tc_args(tc):
    if isinstance(tc, dict):
        return tc.get("args", {}) or {}
    return tc.args if hasattr(tc, "args") else {}


def _find_plan_in_messages(messages) -> dict:
    """Search through ToolMessages to find the project plan."""
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            continue
        try:
            data = json.loads(msg.content)
            if isinstance(data, dict) and "features" in data:
                return data
        except (json.JSONDecodeError, TypeError):
            continue
    return {}


def jira_guard(state: AgentState):
    """Intercept JIRA creation requests. If the LLM called request_jira_creation,
    store the pending scope and return a confirmation message instead of executing tools."""
    try:
        messages = state.get("messages", [])
        if not messages:
            return {}
        last = messages[-1]
        if not (hasattr(last, "tool_calls") and last.tool_calls):
            return {}

        for tc in last.tool_calls:
            tc_name = get_tc_name(tc)
            if tc_name != "request_jira_creation":
                continue

            tc_args = get_tc_args(tc)
            scope = tc_args.get("scope", "all")

            plan = state.get("project_plan") or _find_plan_in_messages(messages)
            feature_count = len(plan.get("features", []))
            story_count = len(plan.get("stories", []))
            test_count = len(plan.get("testing_stories", []))

            if feature_count > 0:
                summary = (
                    f"I will create the following JIRA items:\n"
                    f"• **{feature_count} Epic(s)** — one per feature\n"
                    f"• **{story_count} Development Story(ies)** — linked to Epics\n"
                    f"• **{test_count} Testing Subtask(s)** — linked to Stories\n\n"
                    f"**Do you approve?**"
                )
            else:
                summary = (
                    f"I will create Epics, Stories, and Subtasks in JIRA for all features.\n\n"
                    f"**Do you approve?**"
                )

            return {
                "jira_pending_scope": scope,
                "messages": [AIMessage(content=summary)],
            }

        return {}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"messages": [AIMessage(content=f"Guard error: {e}")]}


def should_continue(state: AgentState):
    messages = state["messages"]
    if not messages:
        return "end"
    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        pending = state.get("jira_pending_scope")
        if pending:
            return "end"
        return "tools"
    return "end"


def after_guard(state: AgentState):
    """After the JIRA guard, skip tools and end if pending, otherwise proceed to tools."""
    if state.get("jira_pending_scope"):
        return "end"
    return "tools"


def build_agent() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_node("process", process_tool_results)
    builder.add_node("jira_guard", jira_guard)

    builder.set_entry_point("agent")

    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "jira_guard",
            "end": END,
        },
    )

    builder.add_conditional_edges(
        "jira_guard",
        after_guard,
        {
            "tools": "tools",
            "end": END,
        },
    )

    builder.add_edge("tools", "process")
    builder.add_edge("process", "agent")

    return builder.compile()
