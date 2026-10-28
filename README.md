# SyncSpace — Real-Time Collaborative Workspace

SyncSpace is a full-stack collaborative workspace for organizing projects, managing tasks, sharing notes, and tracking team activity. It combines a React + TypeScript frontend with a FastAPI backend, SQLAlchemy, PostgreSQL, and WebSockets.

## 🚀 Live Demo

- **Frontend:** https://syncspace-web-9hfs.onrender.com/
- **Backend API:** https://syncspace-api-g4iu.onrender.com/

> **Important — activate the backend first:** The backend runs on a free hosting service and may sleep after inactivity. First open the [Backend API](https://syncspace-api-g4iu.onrender.com/) and wait for it to respond. Then open the [Frontend](https://syncspace-web-9hfs.onrender.com/) and use the application. The first request may take a little while while the backend wakes up. Authentication and workspace features require both services to be available.

## ✨ Features

### Authentication and workspaces
- User registration and login.
- Workspace creation and switching.
- Permission-aware workspace actions and ownership controls.
- Add registered members and remove members with confirmation.

### Projects and task management
- Create and select projects.
- Create tasks with descriptions and priorities.
- Search tasks, change status, and add task comments/discussions.
- Confirm task completion before moving tasks out of the active board.
- View completed tasks and reopen them.
- Mark projects complete and reopen them.

### Collaboration and activity
- WebSocket-powered live task updates for connected workspace users.
- Shared workspace notes that auto-save and broadcast changes to connected clients.
- Recent activity and activity-based notifications.
- Read-to-dismiss notifications, with read state stored in browser local storage per user/workspace.

### User experience
- Responsive dark interface with ocean/graphite styling and mint and warm-sand accents.
- Interactive navigation, dialogs, and subtle animations.
- Reduced-motion preferences are respected.
- FastAPI Swagger UI for exploring API endpoints.

## 🧰 Tech Stack

| Layer | Technologies | Purpose |
|---|---|---|
| Frontend | React, TypeScript, Vite | Single-page application and production build |
| Backend | Python, FastAPI | REST API and application logic |
| Data access | SQLAlchemy | Database models and persistence |
| Database | PostgreSQL in deployment; SQLite for tests | Persistent data and isolated tests |
| Authentication | PyJWT, Argon2 password hashing | Token-based authentication and password hashing |
| Real-time | WebSockets | Live task and shared-note updates |
| Local development | Docker Compose | Run the application stack locally |
| Hosting | Render | Frontend static site and backend service |

## 🧠 Working Algorithm

### 1. Registration and login
1. A user submits credentials from the React frontend.
2. The frontend sends an HTTPS request to the FastAPI backend.
3. The backend validates the request and checks user records in the database.
4. During registration, the password is stored as an Argon2 hash, not plain text.
5. After successful authentication, the backend returns the authentication result/token.
6. The frontend uses the authentication state/token for protected operations.

### 2. Workspace and project operations
1. The frontend requests the user's workspaces.
2. The backend verifies authentication and access permissions.
3. SQLAlchemy reads or updates the corresponding database records.
4. The API returns the result and the frontend updates the relevant view.
5. Owner/admin permissions are enforced on the server for protected operations.

### 3. Task lifecycle
1. A user creates a task with a description and priority.
2. The backend validates and saves the task under the relevant project/workspace.
3. Users can search tasks, update status, and add comments.
4. Selecting **Done** prompts for confirmation.
5. On confirmation, the task is marked complete and moved from the active board to the completed-tasks area.
6. Completed tasks can be reopened.

### 4. Real-time collaboration
1. A connected client establishes a WebSocket connection to the backend.
2. When a supported task or shared-note change occurs, the backend broadcasts an event to connected clients in the workspace.
3. Clients receive the event and update the UI without a full page refresh.
4. Shared-note edits auto-save and are broadcast to connected workspace clients.

> The current in-memory WebSocket manager supports a single backend process. Multi-worker deployments require a shared event/fan-out mechanism.

## 🏗️ Project Structure

```text
SyncSpace-collaborative-workspace/
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # Main React application
│   │   └── vite-env.d.ts         # Vite client type definitions
│   ├── public/                   # Static assets, if used
│   ├── package.json              # Frontend dependencies and scripts
│   ├── package-lock.json         # Locked npm dependency versions
│   ├── vite.config.ts            # Vite configuration
│   └── tsconfig*.json             # TypeScript configuration
├── backend/
│   ├── app/
│   │   └── main.py               # FastAPI application entry point
│   └── requirements.txt          # Python dependencies
├── .env.example                  # Example environment configuration
├── .gitignore
├── docker-compose.yml            # Local development stack
└── README.md
```

*This is a representative overview of the main files; some application modules and subfolders are omitted for readability.*

## ⚙️ Run Locally

### Prerequisites
- Git
- Docker Desktop (recommended), or Python 3.11+ and Node.js/npm to run services separately

### Option A — Docker Compose (recommended)

1. Clone the repository:

   ```bash
   git clone https://github.com/uzaam07/SyncSpace-collaborative-workspace.git
   cd SyncSpace-collaborative-workspace
   ```

2. Copy `.env.example` to `.env` in the repository root.
3. Replace example secret values with secure local values. Do not commit a real `.env`.
4. Start the stack:

   ```bash
   docker compose up --build
   ```

5. Open the frontend at http://localhost:5173 and API docs at http://localhost:8000/docs.

Stop with `Ctrl+C` or `docker compose down`. **Do not run `docker compose down -v` unless you intentionally want to delete the local database volume.**

### Option B — Run services separately

#### Backend

From the repository root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs.

#### Frontend

Open a second terminal:

```powershell
cd frontend
npm install
```

Create `frontend/.env` for local development if needed:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

Start Vite:

```powershell
npm run dev
```

Open http://localhost:5173.

## 🔐 Environment Variables

Set variables in the relevant local `.env` file or hosting provider. Never commit real secrets.

| Variable | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | Backend | Database connection string; use managed PostgreSQL in deployment |
| `SECRET_KEY` | Backend | Long, unique secret for signing/security-related operations |
| `CORS_ORIGINS` | Backend, if read by the app | Allowed frontend origins |
| `VITE_API_BASE_URL` | Frontend build | FastAPI REST API base URL |
| `VITE_WS_BASE_URL` | Frontend build | WebSocket base URL |

### Render values

Frontend environment:

```env
VITE_API_BASE_URL=https://syncspace-api-g4iu.onrender.com
VITE_WS_BASE_URL=wss://syncspace-api-g4iu.onrender.com
```

Backend configuration should include the managed PostgreSQL `DATABASE_URL`, a strong `SECRET_KEY`, and the exact frontend origin in the FastAPI CORS allowlist:

```text
https://syncspace-web-9hfs.onrender.com
```

The backend code must read the configured variables and apply CORS middleware for these settings to take effect. Never expose database credentials or backend secrets in frontend variables.

## 🧪 Tests

From the `backend/` directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

Tests use a temporary SQLite database to isolate test data from the deployed PostgreSQL database.

## 🚢 Deployment

SyncSpace is deployed as two Render services plus a managed database:

1. **Frontend — Static Site**
   - Root directory: `frontend`
   - Build command: `npm install && npm run build`
   - Publish directory: `dist`

2. **Backend — Web Service**
   - Root directory: `backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

3. **Database**
   - Set the production PostgreSQL connection string as backend `DATABASE_URL`.
   - Confirm the backend reads this variable and initializes or migrates the required tables.

4. **CORS and secure connections**
   - Allow `https://syncspace-web-9hfs.onrender.com` in the FastAPI CORS configuration.
   - Use HTTPS for API requests and `wss://` for WebSocket connections.

Free services may sleep after inactivity. Open the backend URL first, wait for it to respond, then open the frontend.

## 🔎 API Documentation

- Local: http://localhost:8000/docs
- Deployed: https://syncspace-api-g4iu.onrender.com/docs

Swagger UI lists the available routes, request schemas, and response formats.

## 🛡️ Security and Production Notes

SyncSpace is a portfolio MVP, not a fully audited commercial product. Before broader production use, consider adding or strengthening:
- Email verification and password reset/account recovery.
- Token revocation/rotation and stricter session lifecycle controls.
- Rate limiting for authentication endpoints.
- Structured logging, monitoring, backups, and security/load testing.
- Shared WebSocket fan-out for multiple backend instances.

Never commit `.env` files, production database URLs, passwords, or secret keys.

## 📌 Future Improvements

- Email verification and account recovery.
- Shared WebSocket event distribution for scaled deployments.
- More integration and end-to-end tests.
- Improved monitoring and deployment health checks.

## 👤 Author

- **Name:** Uzaam Shaad K
- **GitHub:** [uzaam07](https://github.com/uzaam07)
- **Portfolio:** [uzaam07.github.io](https://uzaam07.github.io/Portfolio/)
- **LinkedIn:** [linkedin.com/in/uzaamshaad](https://linkedin.com/in/uzaamshaad)
