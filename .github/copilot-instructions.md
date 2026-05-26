# HLDD AI Agent - Microsoft 365 Copilot run guide

This repository contains a FastAPI backend and React + Vite frontend for uploading an HLDD and generating a project delivery dashboard.

## Project overview

- Backend: FastAPI app in `backend/app`
- Frontend: React + Vite app in `frontend/src`
- Sample HLDD template: `frontend/public/sample-hldd-template.txt`
- Architecture diagram: rendered in the frontend `Architecture` tab
- Feature summaries: development and testing story points are shown separately and combined in the `Features` tab

## Step-by-step Copilot Agent instructions

1. Open the repository root at `/Users/jaimin/Documents/HLDD-AI`.
2. Confirm whether the backend is already running on `http://localhost:8000`.
3. If the backend is not running, start it using:

```bash
cd /Users/jaimin/Documents/HLDD-AI/backend
/Users/jaimin/Documents/HLDD-AI/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

4. Confirm the backend logs show `Application startup complete` and `Uvicorn running on http://0.0.0.0:8000`.
5. Confirm whether the frontend is already running on `http://localhost:3000` or another available port.
6. If the frontend is not running, start it using:

```bash
cd /Users/jaimin/Documents/HLDD-AI/frontend
npm run dev -- --host 0.0.0.0 --port 3000
```

7. If port `3000` is unavailable, try `3001` or another free port and note the chosen port in the response.
8. Open the frontend in the browser and verify the dashboard loads.
9. Upload the sample HLDD file from `frontend/public/sample-hldd-template.txt`.
10. After upload, verify the dashboard shows:
    - dashboard summary
    - features with separate `Dev SP`, `Testing SP`, and `Total SP`
    - development stories
    - testing stories
    - architecture diagram
    - project structure
    - expanded cloud recommendations when the cloud badge or cloud platform node is clicked
11. If the UI cannot reach the backend, verify the backend is running and the frontend is using the correct API endpoint.
12. If the backend cannot start, check whether the port is in use and stop the conflicting process before retrying.
13. If the frontend build fails, run `npm run build` and report the exact error.
14. Keep `README.md` and `prompt.txt` aligned with any changes to run commands, UI behavior, or architecture updates.

## Run commands

### Backend

```bash
cd /Users/jaimin/Documents/HLDD-AI/backend
/Users/jaimin/Documents/HLDD-AI/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd /Users/jaimin/Documents/HLDD-AI/frontend
npm run dev -- --host 0.0.0.0 --port 3000
```

## Expected behavior

1. The backend should respond on `http://localhost:8000`
2. The frontend should be available on `http://localhost:3000` or a fallback port
3. Uploading the sample HLDD template should populate:
   - dashboard summary
   - features with separate development and testing story points
   - development stories
   - testing stories
   - architecture diagram
   - project structure
   - expanded cloud recommendations when the cloud badge or cloud platform node is clicked

## Troubleshooting

- If the backend port is already in use, stop the existing Uvicorn process and rerun the backend command.
- If the frontend port is unavailable, use `npm run dev -- --host 0.0.0.0 --port 3001` or another free port.
- If the frontend cannot reach the backend, confirm the backend is running and CORS is enabled.
- If the build fails, run `cd /Users/jaimin/Documents/HLDD-AI/frontend && npm run build` and use the reported error output.

## Copilot usage notes

Use this file as the workspace guidance for running and validating the application from Microsoft 365 Copilot. Keep the commands and validation steps aligned with the current README and prompt.txt updates.
