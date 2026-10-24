# SyncSpace — Real-Time Collaborative Workspace

Portfolio-ready collaborative task workspace using FastAPI, SQLAlchemy, PostgreSQL, WebSockets, React, TypeScript, and Docker Compose.

## Run locally (recommended)
1. Install Docker Desktop and start it.
2. Copy `.env.example` to `.env` in the repository root.
3. Replace `SECRET_KEY` with a long random value.
4. Open a terminal in this folder and run:
   ```bash
   docker compose up --build
   ```
5. Open http://localhost:5173 for the app and http://localhost:8000/docs for API docs.

Stop with `Ctrl+C`, then optionally run `docker compose down`. To remove the local database volume too, run `docker compose down -v` (this permanently deletes local app data).

## Run backend tests without Docker
Install Python 3.11+, then:
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```
Tests use a temporary SQLite database.

## Frontend features
- Responsive dark workspace UI with gradient accents and interactive navigation
- Workspace creation, switching, and owner-only workspace deletion from Settings
- Project creation and project selection
- Task creation with descriptions and priority, task search, and status changes
- Task discussion/comments, workspace member management, recent activity, and activity-based notifications
- Live task updates over WebSockets while connected
- API documentation link opens the local FastAPI Swagger UI

After extracting an updated project, keep your existing `.env` file and database volume. Start with `docker compose up --build -d`. Do not use `docker compose down -v` unless you intentionally want to erase the local database volume.

## Stack
- FastAPI, SQLAlchemy, PyJWT, Argon2 password hashing
- PostgreSQL for local Docker development; SQLite fallback for tests
- React, TypeScript, Vite
- WebSockets for live task events
- Docker Compose

## Deployment
Deploy frontend and backend separately and use a managed PostgreSQL database. Configure `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `VITE_API_BASE_URL`, and `VITE_WS_BASE_URL` on the relevant host. Production frontend URLs must use HTTPS and the WebSocket URL must use `wss://`. Free hosting policies, sleep behavior, storage, and quotas change often; verify provider terms before deploying.

## Security and production notes
This is a runnable portfolio MVP, not a fully audited commercial product. Before production use, add email verification, password reset, token revocation/rotation, rate limiting, a transactional outbox, Redis-backed WebSocket fanout for multiple backend workers, structured logs/metrics, and load/security testing. The in-memory WebSocket manager works with one backend process only.

## Latest collaboration and UX updates

- **Ocean/graphite visual theme** with mint and warm-sand accents; subtle entry, hover, and modal animations (respects reduced-motion preferences).
- **Read-to-dismiss notifications**: click an unread notification to mark it read. Read IDs are persisted in browser local storage per user and workspace.
- **Member removal** from the Members dialog, with confirmation and server-side owner/admin permission checks. Adding registered members remains available there.
- **Live shared team notes**: each workspace has one shared notes document. Edits auto-save and broadcast to connected workspace clients over the existing WebSocket connection. This is a shared scratchpad, not a multi-cursor code editor.
- **Task completion confirmation**: selecting Done prompts for confirmation. Confirmed tasks leave the active board and appear in a collapsible Completed tasks area, where they can be reopened.
- **Project completion confirmation**: project completion state is stored separately from the existing projects table to avoid requiring a destructive database reset. Projects can be marked complete and reopened.

### Rebuild after updating

From the directory containing `docker-compose.yml`:

```powershell
docker compose up --build -d
```

The backend uses SQLAlchemy `create_all` to create the new notes and project-completion tables on startup. Keep your `.env` and database volume; do not use `docker compose down -v` for this update.
