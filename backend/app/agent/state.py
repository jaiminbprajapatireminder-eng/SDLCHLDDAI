from typing import Annotated, Dict, List, Optional, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    raw_hldd_text: str
    parsed_hldd: Optional[Dict]
    project_plan: Optional[Dict]
    epic_mapping: Dict[str, str]
    story_mapping: Dict[str, str]
    messages: Annotated[List[BaseMessage], add_messages]
    user_input: str
    jira_pending_scope: Optional[str]
    jira_confirmed: bool
