# HLDD AI Agent Dashboard

This repository contains a Python FastAPI backend and a React + Vite frontend for uploading a High Level Design Document (HLDD) and transforming it into a delivery dashboard.

## Features

- **Modern GUI** with glassmorphism design, animated gradients, glow effects, and smooth transitions
- **Download options** — PDF export on all tabs; Features, Stories, and Testing additionally support Excel (.xlsx) and plain-text (.txt) export
- **AI Chatbot icon** — animated inline SVG robot icon (44px) with multi-color gradient details in the Chatbot Agent tab with a pulsing animation
- **Hero AI icon** — animated inline SVG robot icon next to the prominent "HLDD AI Agent" heading, featuring a multi-color gradient (blue→purple→pink) and amber/pink glowing eyes with floating animation
- **Tab icons** — contextual SVG icons for each dashboard tab: dashboard (grid), features (checkmark), stories (file), testing (test), architecture (code), structure (compass), agent (robot), chatbot (chat)
- **Loading animations** — animated dot indicators for chatbot generation and status message pulse effects
- Upload HLDD documents in `.txt`, `.md`, `.docx`, or `.pdf`
- Extract title, functional requirements, project management tool, technology stack, acceptance criteria, and architecture notes
- Preserve additional technology aliases during parsing so the dashboard reflects entries such as Python, Oracle, .NET, SQL, and SQL Server alongside the other declared stack items
- Harden PDF parsing so inline technology stack text—such as `Azure, React, Python` or `Azure Cloud`—is split correctly and normalized into the expected dashboard values
- Read all technologies listed under the `Technology Stack` section even when the header is formatted as a bullet, uses punctuation, or contains compact PDF text such as `GCP, React, FastAPI`
- Generate:
  - Dashboard bullet-point view
  - Feature backlog entries in `IPMA#NNN` format
  - Feature-level story point summaries in the `Features` tab, with separate `Dev SP`, `Testing SP`, and `Total SP` columns
  - Development stories in `E-CRM#NNN` format
  - Testing stories in `TEST-E-CRM#NNN` format
  - Industry-standard, icon-rich architecture diagrams derived from the HLDD technology workflow, including explicit cloud, runtime, and repository nodes such as AWS Cloud, Azure Cloud, GCP Cloud, Kubernetes Cluster, Docker Runtime, and the parsed repository source
  - A clearer, more legible architecture layout with a larger visual footprint, broader spacing, and stronger color separation
  - A clickable cloud badge or cloud platform node in the Architecture tab that expands to recommended services for the target cloud platform
  - Every legend pill in the Architecture tab is clickable and shows the technology description for each layer when expanded
  - A Git/Bitbucket-ready project structure with root-level repository files and platform-specific package metadata
  - A nested directory tree in the `Structure` tab so the proposed repository layout is easy to scan
  - A manual `Refresh payload` action that clears the current dashboard view so the UI can be reset when no document is uploaded or the user wants to wipe the current payload
- A `Chatbot` tab that references the uploaded HLDD context, recommends the best-fit model for the current stack, and answers questions about project functionality, framework choices, alternate frontend/backend/cloud options, cost breakdowns, and the tradeoffs around efficiency, security, and turnaround time
- A separate `Agent` tab with a LangGraph-based Agentic AI that autonomously parses HLDD documents, generates project plans, answers questions via Gemini, and creates JIRA items (Epics, Stories, Subtasks) with human-in-the-loop confirmation
- The chatbot returns `Out of Scope Information` when the prompt is unrelated to the uploaded HLDD context
- The `Structure` tab uses a side-by-side layout — directory tree on the left, quick overview card on the right
- **JIRA integration** — a `Create in JIRA` button in the Features tab that creates JIRA issues for each feature in the SCRUM project, with feature ID and title as the issue summary

## LLM, RAG, MCP, and Agentic AI status

- **LLM:** The chatbot supports optional external model calls through **OpenAI**, **Google Gemini**, and **Groq**. The LangGraph Agent uses **Groq (`llama-3.1-8b-instant`)** by default (falls back to Gemini if no `GROQ_API_KEY` is set, or to a local response when no API keys are configured). Set `GROQ_MODEL` to use a different model (e.g. `llama-3.3-70b-versatile` for higher quality).
- **RAG:** **Implemented** — ChromaDB vector store indexes HLDD document chunks on upload (non-critical — uploads succeed even if ChromaDB embedding fails). The agent has a `retrieve_hldd_context` tool for vector search. See `backend/app/rag.py`.
- **MCP:** **Implemented** — HTTP endpoint at `POST /mcp/call` exposes parse_hldd, generate_plan, and ask_chatbot tools. Standalone stdio MCP server at `backend/app/mcp_server.py`. The agent has a `mcp_call` tool.
- **Agentic AI (LangGraph):** **Implemented** — a LangGraph-based agent at `backend/app/agent/` provides autonomous multi-step reasoning with tool-calling. The agent can parse HLDD documents, generate project plans, ask Gemini for analysis, and create JIRA items (Epics, Stories, Subtasks) using the same logic as the manual endpoints. It uses `gemini-2.5-flash-lite` bound with tool definitions and follows a ReAct loop (Agent → Tool → Agent → Tool → END). Human-in-the-loop is enforced: the agent always asks for confirmation before creating any JIRA items. Access via `POST /api/agent` with `{ prompt, hldd_text, history, confirm }`.

## Copilot agent instructions

A workspace agent file is available at `.github/copilot-instructions.md` to guide Microsoft 365 Copilot on how to configure and run the project.

Use the file to start the backend and frontend, verify the ports, and confirm the dashboard is available after upload.

## Verified local run flow

The project has been verified locally with the current parser and UI changes:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- Upload validation: a compact HLDD payload containing `Technology Stack: GCP, React, FastAPI` returned `technology_stack: ["GCP", "React", "FastAPI"]` and generated a `GCP Cloud` architecture node with `GKE`, `Cloud Run`, `Cloud Functions`, and `Cloud SQL for PostgreSQL` recommendations.
- Build verification: `cd frontend && npm run build`

## Sample upload expectation

When you upload an HLDD that contains `Technology Stack: GCP, React, FastAPI`, the dashboard should expect:

- `technology_stack` to include `GCP`, `React`, and `FastAPI`
- the architecture diagram to render a `GCP Cloud` node
- the expanded cloud recommendations to include `GKE`, `Cloud Run`, `Cloud Functions`, and `Cloud SQL for PostgreSQL`

## Ready-to-paste Copilot Agent prompts

### One-shot prompt

Use this short version when you want to start the project quickly:

> Run the HLDD AI Agent project in /Users/jaimin/Documents/HLDD-AI. Start the backend on port 8000 if it is not already running, start the frontend on port 3000 if it is not already running, open the UI in the browser, upload the sample HLDD from frontend/public/sample-hldd-template.txt, and confirm the dashboard shows the summary, Features tab with Dev SP / Testing SP / Total SP, Stories, Testing, Architecture, and Structure.

### Detailed prompt

Use this exact longer prompt in Copilot Agent chat:

> Open the repository at /Users/jaimin/Documents/HLDD-AI. Check whether the backend is already running on http://localhost:8000. If it is not running, start it with:
>
> cd /Users/jaimin/Documents/HLDD-AI/backend
> /Users/jaimin/Documents/HLDD-AI/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
>
> Confirm the backend logs show Application startup complete and Uvicorn running on http://0.0.0.0:8000.
>
> Check whether the frontend is already running on http://localhost:3000 or another available port. If it is not running, start it with:
>
> cd /Users/jaimin/Documents/HLDD-AI/frontend
> npm run dev -- --host 0.0.0.0 --port 3000
>
> If port 3000 is unavailable, try another free port such as 3001 and tell me which port is used.
>
> Open the frontend in the browser and verify the dashboard loads. Upload the sample HLDD file from frontend/public/sample-hldd-template.txt.
>
> After upload, verify that the dashboard shows the summary, Features tab with Dev SP, Testing SP, and Total SP, Stories, Testing, Architecture, and Structure.
>
> If the frontend cannot reach the backend, confirm the backend is running and that the frontend is using the correct API endpoint.
>
> Keep README.md and prompt.txt aligned with any run, UI, or architecture changes.

## Project Structure

- `backend/app/` – FastAPI backend and parsing logic
- `frontend/src/` – React UI
- `.github/copilot-instructions.md` – Microsoft 365 Copilot run and configuration guidance
- `README.md` – project instructions
- `prompt.txt` – prompt trace and execution notes

## Step-by-Step Run Instructions

### 1. Create and activate a Python virtual environment

```bash
cd /Users/jaimin/Documents/HLDD-AI
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install backend dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Start the backend

```bash
cd /Users/jaimin/Documents/HLDD-AI/backend
/Users/jaimin/Documents/HLDD-AI/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Install frontend dependencies

Open a separate terminal:

```bash
cd /Users/jaimin/Documents/HLDD-AI/frontend
npm install
```

### 5. Start the frontend

```bash
npm run dev -- --host 0.0.0.0 --port 3000
```

If port `3000` is unavailable, use `3001` or another free port and update the browser URL accordingly.

### 6. Open the dashboard

Open `http://localhost:3000` in your browser.

### 7. Upload an HLDD

Use the upload panel to select a `.txt`, `.md`, `.docx`, or `.pdf` HLDD document.

### 8. Use the Chatbot Agent tab

- Open the `Chatbot Agent` tab to review the recommended model for the uploaded HLDD stack.
- If you want live model calls, configure `OPENAI_API_KEY` or `GEMINI_API_KEY` in the backend environment before starting the server.
- If no API key is configured, the backend still returns a context-aware fallback response so the tab remains usable.

### 9. Use the Agentic AI Chat

The `Agent` tab provides a conversational interface to the LangGraph agent.

**Upload HLDD to the agent:**
1. Open the `Agent` tab in the navigation bar
2. Use the file upload card at the top to select a `.txt`, `.md`, `.docx`, or `.pdf` HLDD document
3. For `.pdf` and `.docx` files, the frontend uploads to `POST /api/extract-text` first to extract the text, then passes it to the agent
4. The agent automatically parses the document and generates a project plan
5. Continue the conversation: ask questions, request JIRA sync, or get recommendations

**Type messages directly:**
- Ask the agent to parse HLDD text, generate plans, answer questions, or create JIRA items
- The agent remembers conversation history across messages
- Before creating JIRA items, the agent asks for confirmation — respond "Yes" to proceed

**Example prompts for the agent:**
| Prompt | What the agent does |
|--------|-------------------|
| "Upload an HLDD file and parse it" | Prompts user to upload; agent auto-parses on file select |
| "What can you do? Describe your capabilities" | Lists all tools and workflows |
| "Summarize the current HLDD delivery plan" | Summarizes the parsed plan |
| "Create Epics in JIRA for all features" | Creates Epics (asks confirmation first) |
| "Create Stories linked to the Epics" | Creates Stories for each feature (asks confirmation) |
| "Create Subtasks for all Stories" | Creates Subtasks (asks confirmation) |
| "Compare AWS vs GCP for this project" | Calls ask_gemini tool for analysis |
| "What are the risks in this project?" | Calls ask_gemini for risk assessment |
| "Yes" / "Proceed" | Confirms pending JIRA action |
| "No" / "Cancel" | Cancels pending JIRA action |

**API usage:**
- Send `POST /api/agent` with `{ prompt, hldd_text, history }`.
- The agent parses the HLDD, generates a project plan, and decides which tools to call.
- Before creating JIRA items, the agent asks for confirmation. Send `{ prompt: "yes" }` to proceed.
- Requires `GROQ_API_KEY` (preferred) or `GEMINI_API_KEY` environment variable.

### 10. Sync features to JIRA

- Open the `Features` tab and click **Create in JIRA** to push all features as **Epics** in the SCRUM project.
- Each feature becomes an Epic with its ID and title as the summary.
- After syncing features, open the `Stories` tab and click **Create in JIRA** to push all development stories as **Story** issues linked to their parent Epic.
- After syncing stories, open the `Testing` tab and click **Create in JIRA** to push all testing stories as **Subtask** issues linked to their parent Story.
- Requires `JIRA_EMAIL` and `JIRA_API_TOKEN` environment variables to be set on the backend.
- Results (success/failure per item with JIRA keys) display below the respective table.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | No | Enables live OpenAI model calls in the Chatbot Agent |
| `GEMINI_API_KEY` | No | Enables live Google Gemini model calls in the Chatbot Agent; also used as fallback for the LangGraph Agent when `GROQ_API_KEY` is not set |
| `GROQ_API_KEY` | No | Enables Groq (llama-3.1-8b-instant) for the LangGraph Agentic AI endpoint. Preferred over `GEMINI_API_KEY` when both are set |
| `GROQ_MODEL` | No | Override the default Groq model (default: `llama-3.1-8b-instant`; use `llama-3.3-70b-versatile` for higher quality on paid tiers) |
| `JIRA_EMAIL` | For JIRA | Email address for JIRA Cloud authentication |
| `JIRA_API_TOKEN` | For JIRA | API token for JIRA Cloud authentication (generate at https://id.atlassian.com/manage/api-tokens) |
| `CHROMA_PERSIST_DIR` | No | Directory for persistent ChromaDB storage (default: ephemeral in-memory) |

Example backend start command with Groq and JIRA configured:

```bash
GROQ_API_KEY=gsk_... JIRA_EMAIL=your-email@example.com JIRA_API_TOKEN=your-api-token \
  /Users/jaimin/Documents/HLDD-AI/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Deployment checklist

1. Build the frontend: `cd frontend && npm run build`
2. Deploy the FastAPI backend to a hosting environment (for example Render, Railway, or Azure App Service)
3. Configure environment variables and CORS if needed
4. Serve the built frontend assets using a static host or a reverse proxy

## Notes

- Story points are capped at 3 per story and automatically split into smaller work items.
- The backend uses deterministic heuristics to parse HLDD content and generate the project artifacts.
- Feature entries are parent-level deliverables and now include separate development and testing story point totals, plus a combined total for each feature.
- Development and testing stories are expanded into stack-aware tasks, such as React UI work, FastAPI implementation, persistence work, Docker packaging, and delivery tracking.
- The architecture view reflects the HLDD technology workflow rather than the upload-processing pipeline, uses icons for the core technology stack, and explicitly shows cloud/runtime/repository relationships such as AWS Cloud, Azure Cloud, GCP Cloud, Kubernetes Cluster, Docker Runtime, and the parsed repository source.
- The Architecture tab legend is now dynamic and visually maps each rendered node type, including cloud, runtime, and repository categories, to the corresponding diagram elements. Every legend pill is clickable and expands a detail card describing the technologies used or proposed for that layer.
- The architecture diagram has been reworked for better legibility with wider spacing, stronger contrast, and a clearer left-to-right layout.
- The `Structure` tab now renders a hierarchical directory tree so the proposed repository layout is easier to interpret at a glance, with the tree on the left and a quick overview card on the right.
- The generated structure now follows the Enterprise Directory Map layout, including `.github` workflows, backend modules, frontend feature folders, docs, and root-level orchestration files.
- The dashboard no longer renders a standalone CI/CD Pipeline card, while the parsed repository information is now surfaced in the Architecture tab.
- The Chatbot Agent now returns `Out of Scope Information` for prompts unrelated to the uploaded HLDD context.
- The Chatbot Agent answers cost-comparison questions by providing a cross-provider service category overview (compute, storage, databases, serverless, CDN, containers, AI/ML, analytics, monitoring, data transfer), direct links to each provider's pricing calculator and free tier, and general cost guidance on reserved/spot pricing and hidden egress charges.
- Google Cloud is now preserved during parsing, which enables GCP-specific cloud recommendations and a GCP Cloud node in the diagram.
- The clickable cloud badge or cloud platform node now expands to a richer inline service list with hover-aware summaries, status badges, compact recommendation text, and provider-specific database suggestions.
- The generated project structure now includes repository-friendly files such as `.gitignore`, `README.md`, `frontend/package.json`, and `backend/requirements.txt` so it can be uploaded directly to Git or Bitbucket.
- A short explanatory hint now appears under the legend so users can understand what Frontend, Backend, Cloud, Runtime, Container, and Delivery represent.
- The frontend no longer auto-refreshes the HLDD payload on a timer. The manual `Refresh payload` action now clears the current dashboard view instead.
- The `Refresh payload` action now clears the dashboard view when the user wants to reset the current payload state.
- The `Structure` tab layout was reworked into a side-by-side grid — directory tree on the left, quick overview card on the right.
- The upload card now keeps the `Generate Dashboard` and `Refresh payload` controls aligned and consistently spaced.
- The parser now preserves additional technology aliases such as Python, Oracle, .NET, SQL, and SQL Server so the uploaded stack is shown accurately in the dashboard and chatbot context.
- PDF uploads now preserve inline technology stack values such as Azure, React, and Python even when the extracted text is collapsed onto a single line.
- Azure variants such as `Microsoft Azure Cloud` and `Azure Cloud` are normalized to `Azure` so the dashboard and architecture logic receive the expected value.
- The parser now reads every technology listed under `Technology Stack`, including entries formatted as bullets, punctuation-based headers, or compact PDF text such as `GCP, React, FastAPI`.
- A `Chatbot Agent` tab was added so the page can reference the uploaded HLDD context, recommend a model, and answer questions about functionality, implementation choices, alternate frontend/backend/cloud options, cost breakdowns, and efficiency/security/turnaround tradeoffs.
- README.md and prompt.txt were refreshed to document the reset behavior, Chatbot Agent usage, the current LLM/RAG/MCP status, and the optional external LLM configuration.
- A ready-to-paste Copilot Agent prompt is documented in this README for direct chat usage.
- **JIRA integration**: The Features tab includes a `Create in JIRA` button that posts each feature as an **Epic** in the SCRUM project. The Stories tab includes a `Create in JIRA` button that posts each story as a **Story** issue linked to the parent Epic. The Testing tab includes a `Create in JIRA` button that posts each testing story as a **Subtask** linked to the parent Story. Requires `JIRA_EMAIL` and `JIRA_API_TOKEN` environment variables.
