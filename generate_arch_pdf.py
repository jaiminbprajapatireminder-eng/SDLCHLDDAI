from fpdf import FPDF

FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"

class ArchPDF(FPDF):
    def __init__(self):
        super().__init__()
        self._setup_fonts()

    def _setup_fonts(self):
        self.add_font("ArialUni", "", FONT_PATH)
        self.add_font("ArialUni", "B", FONT_PATH)
        self.add_font("ArialUni", "I", FONT_PATH)

    def header(self):
        self.set_font("ArialUni", "B", 10)
        self.set_text_color(100, 130, 180)
        self.cell(0, 6, "HLDD AI Agent \u2013 Application Architecture", align="C", new_x="LMARGIN", new_y="NEXT")
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
        self.multi_cell(self.w - self.r_margin - x0 - indent, 5, "\u2022 " + text)

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
pdf.set_font("Helvetica", "B", 24)
pdf.set_text_color(30, 60, 120)
pdf.cell(0, 12, "HLDD AI Agent", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 14)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 8, "Application Architecture Documentation", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(5)
pdf.set_font("Helvetica", "I", 10)
pdf.set_text_color(120, 120, 120)
pdf.cell(0, 6, "Generated: May 2026", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 6, "Repository: github.com/jaiminbprajapatireminder-eng/SDLC-HLDD-AI", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(15)

# ===== 1. HIGH-LEVEL OVERVIEW =====
pdf.section_title("1. High-Level Architecture Overview")
pdf.body_text(
    "The HLDD AI Agent is a full-stack web application that ingests High-Level Design Documents, extracts "
    "structured project data, generates a delivery plan (features, stories, test cases, architecture diagrams), "
    "and provides an interactive dashboard with LLM-powered chatbot and JIRA synchronization.\n\n"
    "Stack: React + Vite (frontend) | FastAPI (backend) | Gemini/OpenAI (LLM) | JIRA Cloud (project mgmt)\n"
    "No database is used -- state is held in an in-memory dictionary on the backend and in React state on the frontend."
)

pdf.ln(3)

pdf.sub_title("Component Diagram")
pdf.code_block(
    "  User Browser (React + Vite)"
    "\n        |  :8000"
    "\n        v"
    "\n  +-----------------------------------------+"
    "\n  |          FastAPI Backend                |"
    "\n  |  /api/upload  /api/chatbot  /api/jira/* |"
    "\n  +-----------------------------------------+"
    "\n        |          |            |"
    "\n        v          v            v"
    "\n  +--------+ +-----------+ +---------+"
    "\n  | Parser | | Generator | | JIRA    |"
    "\n  | .py    | | .py       | | REST    |"
    "\n  +--------+ +-----------+ +----+----+"
    "\n                                  |"
    "\n                                  v"
    "\n                          +--------------+"
    "\n                          | JIRA Cloud   |"
    "\n                          | (SCRUM proj) |"
    "\n                          +--------------+"
    "\n"
    "\n  LLM Integration (3-tier cascade, Legacy Chatbot only):"
    "\n  +----------+      +----------+      +------------+"
    "\n  | Gemini   | ---> | OpenAI   | ---> | Local Rule |"
    "\n  | Dataflow | fall | Chat API | fall | Templates  |"
    "\n  +----------+      +----------+      +------------+"
)

# ===== 2. FUNCTIONALITY =====
pdf.add_page()
pdf.section_title("2. Functionality Implemented")

funcs = [
    ("HLDD Upload & Parsing (parser.py)",
     "Supports .txt, .md, .docx, .pdf uploads. Extracts: title, summary, functional requirements, "
     "technology stack, acceptance criteria, architecture notes, project management tool, repository, "
     "CI/CD pipeline. Uses regex + keyword matching (NO LLM)."),
    ("Project Plan Generation (generator.py)",
     "Takes parsed data and generates: features (max 4 from requirements), development stories "
     "(3-4 per feature based on tech stack), testing stories (1 per dev story), Mermaid architecture "
     "diagram (nodes + edges), recommended project file structure. Uses rule-based logic (NO LLM)."),
    ("Interactive Dashboard (React frontend)",
     "7 tabs: Dashboard (summary stats), Features (table with CRUD), Stories (table with CRUD), "
     "Testing (table with CRUD), Architecture (Mermaid.js interactive diagram), Structure "
     "(file tree), Chatbot (LLM QA). Export to PDF, Excel, TXT."),
    ("LLM Chatbot (gemini_dataflow.py + main.py)",
     "3-tier pipeline for classic QA: (1) Gemini 3-stage dataflow (Analyze -> Reason -> Generate), "
     "(2) OpenAI single-call fallback (GPT-4.1-mini / GPT-4o-mini), (3) Local rule-based templates. "
     "Context is built from the parsed HLDD payload. Single-shot (no multi-turn agent loop)."),
    ("JIRA Sync (main.py endpoints)",
     "3 endpoints: create-features (Epics), create-stories (Stories linked to Epics), "
     "create-testing-stories (Subtasks linked to Stories). JIRA Cloud REST API v3."),
    ("Local CRUD",
     "Add, edit, delete features/stories/testing stories from the UI. Changes are local "
     "to the React state and not persisted on the backend."),
]

for title, desc in funcs:
    pdf.sub_title(title)
    pdf.bullet(desc)

# ===== 3. LLM USAGE - CHATBOT =====
pdf.add_page()
pdf.section_title("3. LLM Usage -- Chatbot Detailed Breakdown")

pdf.body_text(
    "The legacy chatbot endpoint (/api/chatbot) implements a 3-tier cascade with automatic LLM "
    "selection based on the project's technology stack."
)

pdf.ln(2)
pdf.sub_title("Tier 1: Gemini Dataflow (gemini_dataflow.py)")
pdf.body_text(
    "Model Pipeline: gemini-2.0-flash -> gemini-2.0-flash -> gemini-2.5-flash"
)
pdf.code_block(
    "  Stage 1 - ANALYZE (gemini-2.0-flash, temp=0.1, max_tokens=1024)"
    "\n    Prompt: classify question topic, scope, key terms, intent"
    "\n    Output format: TOPIC / SCOPE / KEY_TERMS / INTENT"
    "\n"
    "\n  Stage 2 - REASON (gemini-2.0-flash, temp=0.2, max_tokens=2048)"
    "\n    Prompt: step-by-step reasoning with 5 structured questions"
    "\n    Output: 1. What is being asked? 2. Relevant context?"
    "\n            3. Options? 4. Tradeoffs? 5. Best recommendation?"
    "\n"
    "\n  Stage 3 - GENERATE (gemini-2.5-flash, temp=0.15, max_tokens=4096)"
    "\n    Prompt: produce structured final response"
    "\n    Output sections: Summary / Details / Recommendation / Next Steps"
    "\n"
    "\n  Fallback: If any stage fails, a single call to gemini-2.5-flash is made."
    "\n  API: Uses direct REST (urllib), NOT the google-generativeai SDK."
)
pdf.ln(2)

pdf.sub_title("Tier 2: OpenAI Fallback (main.py - call_openai)")
pdf.body_text(
    "Model: gpt-4.1-mini or gpt-4o-mini (selected by recommend_llm() based on tech stack)\n"
    "Single-shot call with system instruction + user message containing context.\n"
    "System instruction covers: Recommendation, Setup, Alternatives, Efficiency,\n"
    "Security, Turnaround time, Cost breakdown."
)
pdf.ln(2)

pdf.sub_title("Tier 3: Local Rule Fallback (main.py - build_local_response)")
pdf.body_text(
    "NO LLM call. Pure Python template engine (~40KB of dicts/if-else).\n"
    "Question type detection via keyword matching:\n"
    "- backend_alternative, backend_mobile, frontend_alternative\n"
    "- cloud_alternative, database_alternative, cost, general\n"
    "Includes full cloud pricing tables (AWS/Azure/GCP) hardcoded in the source."
)
pdf.ln(2)

pdf.sub_title("Chatbot LLM Recommendation Logic")
pdf.code_block(
    "  Chatbot (/api/chatbot) recommendation:"
    "\n    Tech stack contains 'Google Cloud' or 'GCP'   -> Gemini Dataflow"
    "\n    Tech stack has React + FastAPI + PostgreSQL + Docker -> GPT-4.1-mini"
    "\n    Tech stack has AWS/Azure/GCP                     -> GPT-4o-mini"
    "\n    Default                                            -> GPT-4o-mini"
)
pdf.ln(2)

pdf.sub_title("Out-of-Scope Detection")
pdf.body_text(
    "Before any LLM call, the prompt passes through is_out_of_scope() which checks if the "
    "question is related to the HLDD project context. Irrelevant prompts (e.g., 'write a poem') "
    "return an 'Out of Scope' response without consuming API credits."
)

pdf.ln(2)
pdf.sub_title("Context Stuffing (build_chat_context())")
pdf.body_text(
    "The chatbot does NOT use RAG. Instead, the entire parsed HLDD payload is serialized to a "
    "plain-text string and prepended to every LLM prompt. This works for small documents but "
    "will break on large HLDD files that exceed the model's context window."
)
pdf.code_block(
    "  Context includes: Title, Summary, Technology stack,"
    "\n  Project management tool, Repository, CI/CD pipeline,"
    "\n  Functional requirements, Acceptance criteria,"
    "\n  Architecture notes, Project structure,"
    "\n  Feature count, Story count, Testing story count"
)

# ===== 4. TECHNOLOGY STACK =====
pdf.add_page()
pdf.section_title("4. Full Technology Stack")

pdf.sub_title("Backend")
pdf.bullet("Python 3.9+ — FastAPI framework for all REST API endpoints")
pdf.bullet("Google Gemini API — 3-stage dataflow for chatbot (Analyze -> Reason -> Generate)")
pdf.bullet("OpenAI API — GPT-4.1-mini / GPT-4o-mini fallback for chatbot")
pdf.bullet("JIRA Cloud REST API v3 — Epics (10001), Stories (10004), Subtasks (10002)")
pdf.bullet("PyPDF2 / python-docx — Multi-format file parsing (.pdf, .docx)")
pdf.bullet("python-dotenv — Auto-load .env file with API keys")
pdf.bullet("fpdf2 — Offline PDF generation (this document)")

pdf.ln(2)
pdf.sub_title("Frontend")
pdf.bullet("React 18 — Hooks-based UI (useState, useEffect, useCallback, useMemo, useRef)")
pdf.bullet("Vite — Build tool and dev server with hot-reload")
pdf.bullet("Mermaid.js — Architecture diagram rendering from JSON/MMC definition")
pdf.bullet("jspdf + html2canvas — PDF export from DOM elements")
pdf.bullet("xlsx — Excel (.xlsx) export for Features, Stories, Testing tabs")

pdf.ln(2)
pdf.sub_title("Infrastructure / DevOps")
pdf.bullet("Git + GitHub — Version control and CI/CD with Copilot Agent")
pdf.bullet("JIRA Cloud (SCRUM project) — Issue tracking with Epics, Stories, Subtasks")
pdf.bullet("Bitbucket — Repository hosting (parsed from HLDD)")

# ===== 5. DATA FLOW =====
pdf.add_page()
pdf.section_title("5. Data Flow Diagrams")

pdf.sub_title("5.1 Upload -> Dashboard Flow")
pdf.code_block(
    "  User uploads .txt/.docx/.pdf"
    "\n       |"
    "\n       v"
    "\n  POST /api/upload"
    "\n       |"
    "\n       v"
    "\n  _read_upload()     -- extracts text from file"
    "\n       |"
    "\n       v"
    "\n  parse_hldd()        -- regex parsing, NO LLM"
    "\n       |"
    "\n       v"
    "\n  generate_project_plan() -- rule-based gen, NO LLM"
    "\n       |"
    "\n       v"
    "\n  LATEST_PAYLOAD (in-memory dict)"
    "\n       |"
    "\n       v"
    "\n  Response JSON -> React renders 7-tab dashboard"
    "\n  Dashboard/Features/Stories/Tests/Architecture/Structure/Chatbot"
)
pdf.ln(3)

pdf.sub_title("5.2 Chatbot Request Flow")
pdf.code_block(
    "  User types question in chatbot tab"
    "\n       |"
    "\n       v"
    "\n  POST /api/chatbot { prompt, priority }"
    "\n       |"
    "\n       v"
    "\n  is_out_of_scope(prompt) -----> True --> return 'Out of Scope'"
    "\n       | False"
    "\n       v"
    "\n  recommend_llm(payload)"
    "\n       |"
    "\n       v"
    "\n  call_gemini() (if Gemini recommended)"
    "\n       | Success? -> return response"
    "\n       | Fail? -> fall through"
    "\n       v"
    "\n  call_openai() (if OpenAI recommended)"
    "\n       | Success? -> return response"
    "\n       | Fail? -> fall through"
    "\n       v"
    "\n  build_local_response() -- hardcoded templates"
    "\n       | Always works"
    "\n       v"
    "\n  Return { response, source, recommended_llm }"
)
pdf.ln(3)

pdf.sub_title("5.3 JIRA Sync Flow")
pdf.code_block(
    "  User clicks 'Create in JIRA' (per tab)"
    "\n       |"
    "\n       v"
    "\n  Features tab -> POST /api/jira/create-features"
    "\n       | Creates Epics in JIRA (SCRUM project)"
    "\n       | Returns mapping { feature_id -> SCRUM-XX }"
    "\n       | Stored in frontend: jiraEpicMapping"
    "\n       v"
    "\n  Stories tab -> POST /api/jira/create-stories"
    "\n       | Sends jiraEpicMapping in request body"
    "\n       | Creates Stories with parent=Epic key"
    "\n       | Returns mapping { story_id -> SCRUM-YY }"
    "\n       | Stored in frontend: jiraStoryMapping"
    "\n       v"
    "\n  Testing tab -> POST /api/jira/create-testing-stories"
    "\n       | Sends jiraStoryMapping in request body"
    "\n       | Creates Subtasks with parent=Story key"
    "\n       | Returns results"
)

# ===== 6. PROJECT STRUCTURE =====
pdf.add_page()
pdf.section_title("6. Project File Structure")

pdf.code_block(
    "  HLDD-AI/"
    "\n  +-- backend/"
    "\n  |   +-- app/"
    "\n  |   |   +-- main.py           -- FastAPI app, all endpoints"
    "\n  |   |   +-- parser.py         -- HLDD document parsing (regex)"
    "\n  |   |   +-- generator.py      -- project plan generation (rules)"
    "\n  |   |   +-- gemini_dataflow.py -- 3-stage Gemini pipeline"
    "\n  |   |   +-- models.py         -- Pydantic models"
    "\n  |   |   +-- __init__.py"
    "\n  |   +-- tests/"
    "\n  |   |   +-- test_hldd_pipeline.py"
    "\n  |   |   +-- test_chatbot_response.py"
    "\n  |   +-- requirements.txt"
    "\n  |   +-- .gitignore"
    "\n  +-- frontend/"
    "\n  |   +-- src/"
    "\n  |   |   +-- App.jsx           -- Main React component (all tabs)"
    "\n  |   |   +-- main.jsx          -- Entry point"
    "\n  |   |   +-- index.css         -- All styles"
    "\n  |   |   +-- download.js       -- PDF/Excel/TXT export"
    "\n  |   +-- public/"
    "\n  |   |   +-- sample-hldd-template.txt"
    "\n  |   +-- index.html"
    "\n  |   +-- package.json"
    "\n  |   +-- vite.config.js"
    "\n  |   +-- .gitignore"
    "\n  +-- .env               -- API keys (gitignored)"
    "\n  +-- .gitignore"
    "\n  +-- README.md"
    "\n  +-- prompt.txt"
    "\n  +-- generate_arch_pdf.py     -- This document generator"
    "\n  +-- HLDD_AI_Architecture.pdf -- Generated arch doc"
)

# ===== 7. ENVIRONMENT VARIABLES =====
pdf.section_title("7. Environment Variables")

pdf.code_block(
    "  Variable          Required    Description"
    "\n  ------------------------------------------------------------"
    "\n  GEMINI_API_KEY    Preferred   Gemini key for chatbot 3-stage dataflow"
    "\n  JIRA_EMAIL        For JIRA    JIRA Cloud email address"
    "\n  JIRA_API_TOKEN    For JIRA    JIRA Cloud API token"
    "\n  OPENAI_API_KEY    No          OpenAI key (chatbot fallback)"
)

# ===== 8. LIMITATIONS =====
pdf.add_page()
pdf.section_title("8. Current Limitations")

limitations = [
    "No true RAG -- context stuffing limits HLDD document size",
    "No agentic loop -- chatbot is single-shot QA, no multi-turn reasoning",
    "JIRA sync is manual (3 separate UI buttons), no autonomous workflow",
    "No database -- LATEST_PAYLOAD is in-memory, lost on backend restart",
    "Local fallback is ~40KB of hardcoded Python templates -- brittle",
    "No auth/authentication -- open endpoints, CORS allows all origins",
    "No async Gemini calls -- synchronous urllib may block the event loop",
    "No streaming -- chatbot response returns as a single block",
]

for l in limitations:
    pdf.bullet(l)

# ===== 9. ARCHITECTURE DECISIONS =====
pdf.section_title("9. Key Architecture Decisions")

decisions = [
    ("Direct REST over SDK for chatbot",
     "Gemini and OpenAI are called via raw urllib (not google-generativeai or openai Python SDK). "
     "This avoids SDK dependency issues and keeps control over HTTP behavior."),
    ("JIRA parent field over Epic Link",
     "Since the JIRA project is team-managed (simplified=true), the standard "
     "Epic Link custom field (customfield_10014) is unavailable. Links are created via the 'parent' field in the "
     "issue creation payload instead."),
    ("Frontend-managed mappings",
     "JIRA sync mappings (feature->Epic key, story->Story key) are stored in React "
     "state, not on the backend. This avoids needing a database but means mappings are lost on page refresh."),
    ("3-tier LLM cascade",
     "Gemini (dataflow) -> OpenAI (fallback) -> Local rules (last resort). "
     "This ensures the app always returns a response even if all API keys are unset."),
    ("Context stuffing over RAG",
     "Since HLDD documents are small (typically <50KB), context stuffing is simpler to implement "
     "and has lower latency than a full RAG pipeline with vector embeddings."),
    ("Story point cap at 3",
     "All stories are capped at 3 story points regardless of complexity. Point estimation "
     "uses word count heuristics (<=14 words = 1, <=28 words = 2, else 3)."),
]

for title, desc in decisions:
    pdf.sub_title(title)
    pdf.bullet(desc)

# ===== SAVE =====
pdf.output("/Users/jaimin/Documents/HLDD-AI/HLDD_AI_Architecture.pdf")
print("PDF generated: HLDD_AI_Architecture.pdf")
