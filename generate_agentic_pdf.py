from fpdf import FPDF

FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"

class ArchPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("ArialUni", "", FONT_PATH)
        self.add_font("ArialUni", "B", FONT_PATH)
        self.add_font("ArialUni", "I", FONT_PATH)

    def header(self):
        self.set_font("ArialUni", "B", 10)
        self.set_text_color(100, 130, 180)
        self.cell(0, 6, "HLDD AI Agent \u2013 Agentic AI Implementation", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("ArialUni", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font("ArialUni", "B", 13)
        self.set_text_color(30, 60, 120)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def sub_title(self, title):
        self.set_font("ArialUni", "B", 10)
        self.set_text_color(50, 80, 140)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("ArialUni", "", 9)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 4.5, text)
        self.ln(1)

    def bullet(self, text, indent=10):
        self.set_font("ArialUni", "", 9)
        self.set_text_color(30, 30, 30)
        x0 = self.l_margin
        self.set_x(x0 + indent)
        self.multi_cell(self.w - self.r_margin - x0 - indent, 4.5, "\u2022 " + text)

    def code_block(self, text):
        self.set_fill_color(240, 244, 248)
        self.set_font("Courier", "", 7)
        self.set_text_color(20, 20, 30)
        lines = text.split("\n")
        for line in lines:
            self.cell(0, 3.5, "  " + line, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(2)


pdf = ArchPDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

# ===== TITLE PAGE =====
pdf.ln(20)
pdf.set_font("ArialUni", "B", 24)
pdf.set_text_color(30, 60, 120)
pdf.cell(0, 12, "HLDD AI Agent", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("ArialUni", "", 14)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 8, "Agentic AI Implementation (LangGraph + Groq)", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(5)
pdf.set_font("ArialUni", "I", 10)
pdf.set_text_color(120, 120, 120)
pdf.cell(0, 6, "Generated: May 2026", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "Repository: github.com/jaiminbprajapatireminder-eng/SDLC-HLDD-AI", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(15)

# ===== 1. HIGH-LEVEL OVERVIEW =====
pdf.section_title("1. High-Level Architecture Overview")
pdf.body_text(
    "The HLDD AI Agent is a full-stack web application that ingests High-Level Design Documents, extracts "
    "structured project data, generates a delivery plan, and provides an interactive dashboard. "
    "It has two LLM-powered interfaces: a Legacy Chatbot (single-shot QA with 3-tier cascade) and "
    "a LangGraph Agentic AI (multi-turn ReAct loop with 5 tools).\n\n"
    "This document covers ONLY the Agentic AI implementation.\n\n"
    "Stack: React + Vite (frontend) | FastAPI (backend) | Groq (primary LLM) / Gemini (fallback LLM) | "
    "LangGraph (agent orchestration) | JIRA Cloud (project mgmt)"
)

pdf.ln(3)
pdf.sub_title("Application Component Diagram")
pdf.code_block(
    "  User Browser (React + Vite)"
    "\n        |  :8000"
    "\n        v"
    "\n  +-----------------------------------------+"
    "\n  |          FastAPI Backend                |"
    "\n  |  /api/upload  /api/chatbot  /api/jira/* |"
    "\n  |  /api/agent   /api/extract-text         |"
    "\n  +-----------------------------------------+"
    "\n        |          |            |       |"
    "\n        v          v            v       v"
    "\n  +--------+ +-----------+ +---------+ +-----------+"
    "\n  | Parser | | Generator | | JIRA    | | LangGraph |"
    "\n  | .py    | | .py       | | REST    | | Agent     |"
    "\n  +--------+ +-----------+ +----+----+ +-----------+"
    "\n                                  |"
    "\n                                  v"
    "\n                          +--------------+"
    "\n                          | JIRA Cloud   |"
    "\n                          | (SCRUM proj) |"
    "\n                          +--------------+"
    "\n"
    "\n  Agent LLM Fallback Chain:"
    "\n  1. GROQ_API_KEY set       -> Groq llama-3.1-8b-instant (default)"
    "\n  2. GEMINI_API_KEY set      -> Gemini gemini-2.5-flash-lite (fallback)"
    "\n  3. Neither set             -> ValueError (at least one required)"
)

# ===== 2. WHAT IS THE LANGGRAPH AGENT? =====
pdf.add_page()
pdf.section_title("2. What is the LangGraph Agent?")
pdf.body_text(
    "The LangGraph Agent replaces the previous single-shot chatbot with an autonomous AI agent that "
    "can reason, plan, and execute multi-step tasks using tools. Instead of following a fixed pipeline "
    "(parse -> plan -> respond), the agent uses a ReAct loop (Reasoning + Acting): it thinks about what "
    "to do next, calls a tool, gets the result, thinks again, and repeats until the task is complete.\n\n"
    "The agent uses Groq (llama-3.1-8b-instant) as its default LLM (with Gemini as fallback), bound to "
    "5 tools that wrap the existing HLDD application logic. The frontend provides a dedicated Agent tab "
    "(separate from the Chatbot tab) with file upload, chat messages, and JIRA controls. "
    "Human-in-the-loop is enforced via the system prompt: the agent always asks for confirmation before "
    "creating or modifying JIRA items."
)

pdf.ln(3)
pdf.sub_title("Comparison: Legacy Chatbot vs Agentic AI")
pdf.code_block(
    "  LEGACY CHATBOT (Single-Shot):               AGENTIC AI (LangGraph):"
    "\n  User question -> fixed pipeline -> resp     User goal -> agent decides -> tools -> loops -> done"
    "\n                                                                                                     "
    "\n  POST /api/chatbot                           POST /api/agent"
    "\n  { prompt, priority }                        { prompt, hldd_text, history, confirm }"
    "\n                                                                                                     "
    "\n  1. is_out_of_scope()                        1. Agent LLM (Groq llama-3.1-8b-instant + tools)"
    "\n  2. Gemini dataflow (3 stages)               2. ToolNode (execute 1 of 5 tools)"
    "\n  3. OpenAI fallback                          3. Loop back to Agent LLM"
    "\n  4. Local rule templates                     4. END when task is done"
    "\n                                                                                                     "
    "\n  Returns: { response, source }               Returns: { response, state }"
)

# ===== 3. AGENT ARCHITECTURE =====
pdf.section_title("3. Agent Architecture")

pdf.sub_title("LangGraph StateGraph Structure")
pdf.code_block(
    "  +----------+"
    "\n  |  START   |"
    "\n  +----+-----+"
    "\n       |"
    "\n       v"
    "\n  +----------+"
    "\n  |  AGENT   |  (Groq llama-3.1-8b-instant + tool binding)"
    "\n  +----+-----+"
    "\n       |"
    "\n       +-- tool_calls? --Yes--> +----------+"
    "\n       |                        |  TOOLS   |  (ToolNode dispatches to matched tool)"
    "\n       | No                     +----+-----+"
    "\n       |                             |"
    "\n       v                             v"
    "\n  +----------+              +-----------------+"
    "\n  |   END    |              | process_results |  (extract parsed/plan from JSON output)"
    "\n  +----------+              +--------+--------+"
    "\n                                       |"
    "\n                                       v"
    "\n                                  (back to AGENT)"
    "\n"
    "\n  should_continue() decision function:"
    "\n    - Last message has tool_calls? -> route to TOOLS"
    "\n    - No tool_calls? -> route to END"
)
pdf.ln(3)

pdf.sub_title("Agent State Schema (state.py)")
pdf.code_block(
    "  AgentState = {"
    "\n      raw_hldd_text: str         # Original HLDD document text"
    "\n      parsed_hldd: dict | None   # Output of parse_hldd tool"
    "\n      project_plan: dict | None  # Output of generate_plan tool"
    "\n      epic_mapping: dict         # feature_id -> JIRA epic key"
    "\n      story_mapping: dict        # story_id -> JIRA story key"
    "\n      messages: list             # Chat history (Human/AI/Tool msgs)"
    "\n      user_input: str            # Latest prompt from user"
    "\n      pending_confirmation: str  # Pending action awaiting user OK"
    "\n  }"
)
pdf.ln(3)

pdf.sub_title("File Structure (backend/app/agent/)")
pdf.code_block(
    "  backend/app/agent/"
    "\n  +-- __init__.py           -- Package marker"
    "\n  +-- state.py              -- AgentState TypedDict"
    "\n  +-- prompts.py            -- AGENT_SYSTEM_PROMPT (~800 chars)"
    "\n  +-- tools.py              -- 5 LangChain @tool functions"
    "\n  +-- llm.py                -- LLM builder (Groq primary, Gemini fallback)"
    "\n  +-- graph.py              -- StateGraph build + conditional edges"
)

# ===== 4. TECHNOLOGY STACK =====
pdf.add_page()
pdf.section_title("4. Technology Stack")

pdf.sub_title("Backend")
pdf.bullet("Python 3.9+ — FastAPI framework for REST API endpoints")
pdf.bullet("LangGraph — StateGraph agent orchestration with ReAct loop (Agent -> Tool -> Agent)")
pdf.bullet("LangChain Groq — ChatGroq integration for llama-3.1-8b-instant as the default agent LLM")
pdf.bullet("LangChain Google GenAI — ChatGoogleGenerativeAI fallback for Gemini 2.5-flash-lite")
pdf.bullet("LangChain Core — AIMessage, HumanMessage, ToolMessage types; ToolNode for tool dispatch")
pdf.bullet("Groq API — Primary LLM provider (llama-3.1-8b-instant, 30K TPD free tier)")
pdf.bullet("Google Gemini API — Fallback LLM provider (gemini-2.5-flash-lite)")
pdf.bullet("JIRA Cloud REST API v3 — Epics (10001), Stories (10004), Subtasks (10002)")
pdf.bullet("PyPDF2 / python-docx — Multi-format file parsing (.pdf, .docx)")
pdf.bullet("python-dotenv — Environment variable loading from .env file")
pdf.bullet("fpdf2 — PDF generation")

pdf.ln(2)
pdf.sub_title("Frontend")
pdf.bullet("React 18 — Component-based UI with hooks")
pdf.bullet("Vite — Build tool and dev server")
pdf.bullet("Mermaid.js — Architecture diagram rendering in the browser")
pdf.bullet("jspdf + html2canvas — PDF export from DOM")
pdf.bullet("xlsx — Excel (.xlsx) export for Features, Stories, Testing tabs")

# ===== 5. LLM CONFIGURATION =====
pdf.ln(2)
pdf.section_title("5. LLM Configuration")

pdf.sub_title("Agent LLM Priority")
pdf.code_block(
    "  Agent LLM (LangGraph) priority:"
    "\n    1. GROQ_API_KEY set         -> Groq llama-3.1-8b-instant (default)"
    "\n    2. GEMINI_API_KEY set        -> Gemini gemini-2.5-flash-lite (fallback)"
    "\n    3. Neither set               -> ValueError"
    "\n"
    "\n  Override: GROQ_MODEL env var (e.g. llama-3.3-70b-versatile for paid tiers)"
)
pdf.ln(2)

pdf.sub_title("Token Optimization for Groq Free Tier (6000 TPM limit)")
pdf.bullet("HLDD text truncated to 1500 characters before sending to the LLM")
pdf.bullet("Conversation history limited to last 6 messages to control cumulative token growth")
pdf.bullet("AI response content truncated to 500 characters per message")
pdf.bullet("Tool result content truncated to 600 characters per message")
pdf.bullet("Combined parse_and_generate_plan tool replaces two separate tools (parse_hldd + generate_plan)")
pdf.bullet("System prompt condensed from ~1900 to ~800 characters")
pdf.bullet("Reduced from 7 to 5 tools, cutting tool schema overhead by ~30%")
pdf.bullet("Graceful 429 HTTP response when rate limit is hit, with upgrade suggestion")
pdf.ln(2)

pdf.sub_title("GROQ_API_KEY Configuration")
pdf.bullet("Default model: llama-3.1-8b-instant (30,000 TPD free tier limit)")
pdf.bullet("Paid upgrade: llama-3.3-70b-versatile (set GROQ_MODEL env var)")
pdf.bullet("Fallback: GEMINI_API_KEY is used when GROQ_API_KEY is not set")
pdf.bullet("Rate limits: ~6000 TPM on free tier -- optimized via prompt truncation")

# ===== 6. AGENT PROMPTS =====
pdf.add_page()
pdf.section_title("6. Agent Prompts")

pdf.sub_title("6.1 AGENT_SYSTEM_PROMPT (master prompt)")
pdf.body_text(
    "This is the most important prompt -- it defines the agent's personality, capabilities, "
    "workflow rules, and human-in-the-loop requirements. It lives in prompts.py."
)
pdf.code_block(
    "\"\"\"You are an HLDD Delivery Agent that analyzes High-Level Design"
    "\nDocuments and manages JIRA delivery."
    "\n"
    "\n## Tools"
    "\n- parse_and_generate_plan: Parse HLDD and generate features/stories/tests."
    "\n- ask_gemini: Ask Gemini about the project, tech comparisons, or recommendations."
    "\n- create_jira_epic: Create a JIRA Epic for a feature (ask user first)."
    "\n- create_jira_story: Create a JIRA Story linked to an Epic (ask user first)."
    "\n- create_jira_subtask: Create a JIRA Subtask linked to a Story (ask user first)."
    "\n"
    "\n## Rules"
    "\n1. When user provides HLDD text, call parse_and_generate_plan. Report results."
    "\n2. For JIRA: only create when user explicitly asks. Always ask confirmation first."
    "\n3. For questions: use ask_gemini."
    "\n4. Be concise. If no HLDD provided, ask the user to provide one."
    "\n\"\"\""
)
pdf.ln(3)

pdf.sub_title("6.2 Tool Docstrings (per-tool prompts)")
pdf.body_text(
    "Each @tool function's docstring IS a prompt -- it tells the LLM when to call the tool, "
    "what inputs it needs, and what it returns. The LLM reads these docstrings at inference "
    "time via Gemini's function calling / tool binding."
)
pdf.ln(3)

pdf.sub_title("6.3 Context Injection (dynamic prompt)")
pdf.body_text(
    "Before each agent turn, the agent_node function injects the current HLDD context into "
    "the system message. This is built dynamically from the state:"
)
pdf.code_block(
    "  ## Current HLDD Context"
    "\n  Title: {title}"
    "\n  Tech Stack: React, FastAPI, PostgreSQL"
    "\n  Functional Requirements: 4"
    "\n"
    "\n  ## Current Project Plan"
    "\n  Features: 4"
    "\n  Development Stories: 12"
    "\n  Testing Stories: 12"
    "\n  JIRA Epics Created: 2 (SCRUM-50, SCRUM-51)"
    "\n  JIRA Stories Created: 0"
)

# ===== 7. TOOL DEFINITIONS =====
pdf.add_page()
pdf.section_title("7. Tool Definitions")

tools_desc = [
    ("parse_and_generate_plan(raw_hldd_text: str) -> dict",
     "Wraps parser.parse_hldd_document() then generator.generate_project_plan() in one step. "
     "Extracts title, functional_requirements, technology_stack, and immediately generates "
     "features, stories, testing stories, architecture diagram, and project structure. "
     "Preferred over calling parse_hldd + generate_plan separately."),
    ("ask_gemini(question: str, context_str: str) -> str",
     "Wraps gemini_dataflow.call_gemini_dataflow(). For general Q&A, technology comparisons, "
     "cost analysis, architecture advice, risk assessment. Always passes current HLDD context."),
    ("create_jira_epic(feature_id: str, name: str, description: str) -> str",
     "Creates an Epic in JIRA SCRUM project. Returns JIRA key (e.g., SCRUM-42). "
     "Must be called BEFORE create_jira_story. Human confirmation required."),
    ("create_jira_story(story_id: str, title: str, description: str, epic_key: str) -> str",
     "Creates a Story in JIRA linked to a parent Epic via the parent field. "
     "Requires epic_key from create_jira_epic. Human confirmation required."),
    ("create_jira_subtask(test_id: str, title: str, description: str, parent_key: str) -> str",
     "Creates a Subtask in JIRA linked to a parent Story. "
     "Requires parent_key from create_jira_story. Human confirmation required."),
]

for sig, desc in tools_desc:
    pdf.sub_title(sig)
    pdf.bullet(desc)

# ===== 8. AGENT EXECUTION FLOW =====
pdf.add_page()
pdf.section_title("8. Agent Execution Flow")

pdf.sub_title("Example: Parse HLDD and Create JIRA Epics")
pdf.code_block(
    "  Step 1: Agent LLM receives system prompt + user message"
    "\n          Thinks: 'I need to parse the HLDD and generate a plan'"
    "\n          Calls: parse_and_generate_plan(raw_text)"
    "\n          State: parsed_hldd = { title, tech_stack, ... }"
    "\n                 project_plan = { features: [...], stories: [...] }"
    "\n"
    "\n  Step 2: process_tool_results extracts parsed_hldd and project_plan"
    "\n          from the ToolMessage JSON output, then loops back to Agent"
    "\n"
    "\n  Step 3: Agent LLM sees plan. User asked for JIRA."
    "\n          Thinks: '4 features found. Must ask user before creating.'"
    "\n          Responds: 'I found 4 features. Shall I create 4 Epics in JIRA?'"
    "\n          Pauses (waits for user input)"
    "\n"
    "\n  Step 4: User says 'Yes, proceed'"
    "\n          Agent: Calls create_jira_epic() x 4"
    "\n          Results: SCRUM-50, SCRUM-51, SCRUM-52, SCRUM-53"
    "\n          State: epic_mapping = { IPMA#001: SCRUM-50, ... }"
    "\n"
    "\n  Step 5: Agent reports results"
    "\n          Responds: 'Created 4 Epics: SCRUM-50 through SCRUM-53'"
    "\n          END"
)
pdf.ln(3)

pdf.sub_title("Graph Transitions")
pdf.code_block(
    "  Agent Node -> should_continue()"
    "\n                   |"
    "\n                   +-- Last msg has tool_calls? --> Tools Node"
    "\n                   |                                  |"
    "\n                   |                                  +-- Execute tool"
    "\n                   |                                  +-- Return result as ToolMessage"
    "\n                   |                                  +-- Go back to Agent Node"
    "\n                   |"
    "\n                   +-- Last msg has NO tool_calls? --> END"
    "\n                                                        |"
    "\n                                                        +-- Return final response"
)

# ===== 9. HUMAN-IN-THE-LOOP =====
pdf.section_title("9. Human-in-the-Loop Design")
pdf.bullet("The system prompt instructs the agent to ALWAYS ask before JIRA actions")
pdf.bullet("The LLM generates the confirmation question naturally (no code-level interrupt)")
pdf.bullet("User responds with 'yes'/'proceed'/'confirm' -- agent then calls JIRA tools")
pdf.bullet("If user says 'no'/'cancel'/'stop' -- agent does NOT call JIRA tools and asks what next")
pdf.bullet("The confirm field in the AgentRequest allows frontend to pass explicit approval")
pdf.bullet("All 5 tools are pure functions -- they cannot modify state without being called")

# ===== 10. FASTAPI INTEGRATION =====
pdf.add_page()
pdf.section_title("10. FastAPI Integration")

pdf.sub_title("Endpoint: POST /api/agent")
pdf.code_block(
    "  Request:"
    "\n  {"
    "\n    'prompt': 'Parse this HLDD and create Epics for all features',"
    "\n    'hldd_text': 'HLDD document content...',"
    "\n    'history': [                      # conversation so far"
    "\n      { 'role': 'user', 'content': '...' },"
    "\n      { 'role': 'assistant', 'content': '...' }"
    "\n    ],"
    "\n    'confirm': false                  # set true to confirm pending action"
    "\n  }"
    "\n"
    "\n  Response:"
    "\n  {"
    "\n    'response': 'Created 4 Epics: SCRUM-50, SCRUM-51...',"
    "\n    'state': {"
    "\n      'parsed': { ... },             # parsed HLDD data"
    "\n      'plan': { ... },               # project plan"
    "\n      'epics': { IPMA#001: SCRUM-50, ... },"
    "\n      'stories': {}"
    "\n    }"
    "\n  }"
)
pdf.ln(3)

pdf.sub_title("Error Handling")
pdf.bullet("If GROQ_API_KEY and GEMINI_API_KEY are both unset: HTTP 400 with clear error")
pdf.bullet("If JIRA_EMAIL/JIRA_API_TOKEN not set: JIRA tools return error string (not crash)")
pdf.bullet("Tool failures are returned as ToolMessage content, fed back to agent LLM")
pdf.bullet("Agent LLM reads the error and asks the user how to proceed")
pdf.bullet("Groq rate limits: HTTP 429 with retry suggestion and upgrade link")
pdf.ln(3)

pdf.sub_title("State Flow per Request")
pdf.code_block(
    "  1. Frontend sends { prompt, hldd_text, history, confirm }"
    "\n  2. Backend converts history to LangChain message objects"
    "\n  3. Creates AgentState: raw_hldd_text, messages + user_input"
    "\n  4. Invokes agent (StateGraph) with recursion_limit=50"
    "\n  5. Graph loops: Agent Node -> Tools -> Agent -> ... -> END"
    "\n  6. Last message content returned as 'response'"
    "\n  7. parsed_hldd, project_plan, epic_mapping, story_mapping"
    "\n     extracted from state and returned"
)

# ===== 11. FILE UPLOAD WORKFLOW =====
pdf.add_page()
pdf.section_title("11. File Upload via Agent Chat")
pdf.body_text(
    "The frontend Agent tab provides a file upload input and a chat interface. Users can upload "
    ".txt, .md, .docx, or .pdf HLDD documents directly to the agent without using the main "
    "/api/upload endpoint."
)
pdf.ln(2)
pdf.sub_title("Upload Flow")
pdf.code_block(
    "  1. User clicks file input in agent chat"
    "\n  2. Frontend reads file as text (FileReader / .text())"
    "\n  3. Frontend calls POST /api/agent with:"
    "\n     { prompt: 'Parse this HLDD...', hldd_text: '<text>', history: [] }"
    "\n  4. Agent LLM receives file content as hldd_text"
    "\n  5. Agent decides to call parse_and_generate_plan(raw_text) tool"
    "\n  6. Returns structured sections + project plan in one call"
    "\n  7. Agent reports results to user in chat"
    "\n  8. User can continue: 'Create Epics in JIRA', 'Summarize the plan', etc."
)
pdf.ln(3)

pdf.sub_title("Supported Formats")
pdf.code_block(
    "  Format    Method"
    "\n  ---------------------------------------------"
    "\n  .txt      file.text() in browser (client-side)"
    "\n  .md       file.text() in browser (client-side)"
    "\n  .docx     POST /api/extract-text (python-docx)"
    "\n  .pdf      POST /api/extract-text (PyPDF2)"
)
pdf.ln(3)

pdf.sub_title("Example Prompts for the Agent")
pdf.code_block(
    "  Prompt                                        Agent Action"
    "\n  ------------------------------------------------------------------"
    "\n  'Upload an HLDD file and parse it'           Prompts user to upload"
    "\n  'What can you do?'                           Lists capabilities"
    "\n  'Summarize the delivery plan'                Summarizes parsed plan"
    "\n  'Create Epics in JIRA for all features'      Creates Epics (asks first)"
    "\n  'Create Stories linked to the Epics'         Creates Stories"
    "\n  'Create Subtasks for all Stories'            Creates Subtasks"
    "\n  'Compare AWS vs GCP for this project'        Calls ask_gemini tool"
    "\n  'What are the risks?'                        Risk analysis via Gemini"
    "\n  'Yes' / 'Proceed'                            Confirms pending JIRA action"
    "\n  'No' / 'Cancel'                              Cancels pending action"
)

# ===== 12. RAG IMPLEMENTATION =====
pdf.add_page()
pdf.section_title("12. RAG (Retrieval-Augmented Generation)")

pdf.body_text(
    "RAG is IMPLEMENTED as of May 2026. The application uses ChromaDB (ephemeral by default) "
    "with a DefaultEmbeddingFunction to index HLDD document chunks for vector search."
)

pdf.sub_title("Architecture")
pdf.code_block(
    "  Upload Flow:"
    "\n  1. User uploads HLDD (.txt/.md/.docx/.pdf)"
    "\n  2. Text is extracted via _read_upload()"
    "\n  3. Text is chunked (500 chars, 50 overlap) and indexed in ChromaDB"
    "\n  4. retriever.ingest(raw_text) deletes old chunks, inserts new ones"
    "\n"
    "\n  Retrieval Flow (Agent tool):"
    "\n  1. Agent calls retrieve_hldd_context(question)"
    "\n  2. ChromaDB performs vector similarity search (k=3)"
    "\n  3. Top-k chunks returned as plain text"
    "\n  4. Agent uses retrieved context instead of truncated text"
)
pdf.ln(2)

pdf.sub_title("Components")
pdf.bullet("backend/app/rag.py — HLDDRetriever class (ingest, retrieve, clear)")
pdf.bullet("ChromaDB — vector store (ephemeral in-memory, configurable to persistent)")
pdf.bullet("DefaultEmbeddingFunction — built-in ChromaDB embedding (no extra model needed)")
pdf.bullet("Chunk size: 500 chars with 50 char overlap")
pdf.bullet("Agent tool: retrieve_hldd_context(question) -> relevant chunks")
pdf.bullet("Wired into upload flow: retriever.ingest() called after every upload")

# ===== 13. MCP IMPLEMENTATION =====
pdf.add_page()
pdf.section_title("13. MCP (Model Context Protocol)")

pdf.body_text(
    "MCP is IMPLEMENTED as of May 2026. The application exposes an HTTP-based MCP endpoint "
    "and an agent tool to call external MCP tools. The MCP server can also run as a standalone "
    "stdio process via python -m app.mcp_server."
)

pdf.sub_title("Architecture")
pdf.code_block(
    "  HTTP Endpoint (POST /mcp/call):"
    "\n  Request: { tool, arguments }"
    "\n"
    "\n  Available MCP tools:"
    "\n  - parse_hldd(text)       -> parse HLDD into structured data"
    "\n  - generate_plan(data)    -> generate project plan from parsed data"
    "\n  - ask_chatbot(question, context, priority) -> ask the legacy chatbot"
    "\n"
    "\n  Agent Integration:"
    "\n  Agent tool: mcp_call(tool_name, arguments) -> calls POST /mcp/call"
    "\n  The LangGraph agent can invoke MCP tools as part of its ReAct loop"
)
pdf.ln(2)

pdf.sub_title("Components")
pdf.bullet("backend/app/mcp_server.py — Standalone MCP Server (stdio, no external deps)")
pdf.bullet("POST /mcp/call — FastAPI endpoint for HTTP MCP calls")
pdf.bullet("Agent tool: mcp_call(tool_name, arguments) -> str")
pdf.bullet("3 tools: parse_hldd, generate_plan, ask_chatbot")
pdf.bullet("Start standalone: python -m app.mcp_server")

# ===== 14. LIMITATIONS =====
pdf.section_title("14. Current Limitations")
pdf.bullet("No true RAG -- context stuffing limits HLDD document size to ~1500 chars")
pdf.bullet("Groq free tier limited to 6000 TPM / 30,000 TPD -- may hit rate limits on heavy usage")
pdf.bullet("No streaming -- agent response returns as a single block (no SSE)")
pdf.bullet("No persistent state -- AgentState is created per-request, conversation lives in frontend history")
pdf.bullet("No database -- LATEST_PAYLOAD is in-memory, lost on backend restart")
pdf.bullet("No auth/authentication -- open endpoints, CORS allows all origins")
pdf.bullet("JIRA project hardcoded to 'SCRUM' at mylearningdata.atlassian.net")
pdf.bullet("Recursion limit set to 50 -- infinite loops are bounded but long chains fail silently")

# ===== 13. ENVIRONMENT VARIABLES =====
pdf.section_title("13. Environment Variables")
pdf.code_block(
    "  Variable          Required    Description"
    "\n  ------------------------------------------------------------"
    "\n  GROQ_API_KEY      Preferred   Groq key for agent LLM (llama-3.1-8b-instant)"
    "\n  GEMINI_API_KEY    Fallback    Gemini key (fallback when GROQ_API_KEY not set)"
    "\n  JIRA_EMAIL        For JIRA    JIRA Cloud email"
    "\n  JIRA_API_TOKEN    For JIRA    JIRA Cloud API token"
    "\n  GROQ_MODEL        No          Override default Groq model"
)

# ===== 15. FUTURE ENHANCEMENTS =====
pdf.section_title("15. Future Enhancements")
pdf.bullet("Add interrupt_before=['tools'] in graph.compile() for code-level human-in-the-loop (pauses before every tool)")
pdf.bullet("Switch ChromaDB to persistent mode and add sentence-transformers for better embeddings")
pdf.bullet("Add web_search MCP tool for real-time technology/cost research")
pdf.bullet("Add MCP stdio client for IDE tool access (file editing, git operations)")
pdf.bullet("Add streaming response via Server-Sent Events so the agent's reasoning is visible in real-time")
pdf.bullet("Add persistent state via SQLite checkpointing (LangGraph's built-in MemorySaver)")
pdf.bullet("Replace Gemini with a fine-tuned model specialized in HLDD analysis")

# ===== SAVE =====
pdf.output("/Users/jaimin/Documents/HLDD-AI/HLDD_AGENTIC_AI.pdf")
print("PDF generated: HLDD_AGENTIC_AI.pdf")
