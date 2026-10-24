from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import json

from app.config import settings
from app.db import Base, engine, get_db, SessionLocal
from app import models
from app.schemas import RegisterIn, LoginIn, TokenOut, UserOut, WorkspaceIn, WorkspaceOut, ProjectIn, ProjectOut, TaskIn, TaskUpdate, TaskOut, CommentIn, CommentOut
from app.security import hash_password, verify_password, create_access_token, get_current_user, require_workspace_role
from app.realtime import manager

app = FastAPI(title=settings.app_name, description="Real-time collaborative workspace API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://syncspace-web-9hfs.onrender.com",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"name": settings.app_name, "status": "running", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/v1/auth/register", response_model=TokenOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = str(data.email).lower().strip()
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = models.User(email=email, display_name=data.display_name.strip(), password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered")
    return {"access_token": create_access_token(user.id), "user": user}

@app.post("/api/v1/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    email = str(data.email).lower().strip()
    user = db.scalar(select(models.User).where(models.User.email == email))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token(user.id), "user": user}

@app.get("/api/v1/auth/me", response_model=UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user

@app.get("/api/v1/workspaces", response_model=list[WorkspaceOut])
def list_workspaces(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = db.scalars(select(models.Membership).where(models.Membership.user_id == user.id)).all()
    return [{"id": m.workspace.id, "name": m.workspace.name, "owner_id": m.workspace.owner_id, "role": m.role} for m in memberships]

@app.post("/api/v1/workspaces", response_model=WorkspaceOut, status_code=201)
def create_workspace(data: WorkspaceIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = models.Workspace(name=data.name.strip(), owner_id=user.id)
    db.add(workspace)
    db.flush()
    db.add(models.Membership(workspace_id=workspace.id, user_id=user.id, role="owner"))
    db.commit()
    db.refresh(workspace)
    return {"id": workspace.id, "name": workspace.name, "owner_id": workspace.owner_id, "role": "owner"}

@app.get("/api/v1/workspaces/{workspace_id}/members")
def list_workspace_members(workspace_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_workspace_role(db, workspace_id, user.id)
    memberships = db.scalars(select(models.Membership).where(models.Membership.workspace_id == workspace_id).order_by(models.Membership.id.asc())).all()
    return [{"user_id": m.user.id, "email": m.user.email, "display_name": m.user.display_name, "role": m.role} for m in memberships]

@app.delete("/api/v1/workspaces/{workspace_id}/members/{member_user_id}", status_code=204)
def remove_member(workspace_id: int, member_user_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_workspace_role(db, workspace_id, user.id, {"owner", "admin"})
    workspace = db.get(models.Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if member_user_id == workspace.owner_id:
        raise HTTPException(status_code=400, detail="The workspace owner cannot be removed")
    membership = db.scalar(select(models.Membership).where(models.Membership.workspace_id == workspace_id, models.Membership.user_id == member_user_id))
    if not membership:
        raise HTTPException(status_code=404, detail="Workspace member not found")
    if user.id != workspace.owner_id and membership.role == "admin":
        raise HTTPException(status_code=403, detail="Only the workspace owner can remove an admin")
    db.delete(membership)
    db.commit()
    return None

@app.get("/api/v1/workspaces/{workspace_id}/notes")
def get_workspace_notes(workspace_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_workspace_role(db, workspace_id, user.id)
    note = db.scalar(select(models.WorkspaceNote).where(models.WorkspaceNote.workspace_id == workspace_id))
    if not note:
        return {"workspace_id": workspace_id, "body": "", "updated_by": None, "updated_at": None}
    return {"workspace_id": workspace_id, "body": note.body, "updated_by": note.updated_by, "updated_at": note.updated_at}

@app.put("/api/v1/workspaces/{workspace_id}/notes")
async def save_workspace_notes(workspace_id: int, data: dict = Body(...), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_workspace_role(db, workspace_id, user.id, {"owner", "admin", "member"})
    body = data.get("body", "")
    if not isinstance(body, str) or len(body) > 50000:
        raise HTTPException(status_code=422, detail="Notes must be text under 50,000 characters")
    note = db.scalar(select(models.WorkspaceNote).where(models.WorkspaceNote.workspace_id == workspace_id))
    if not note:
        note = models.WorkspaceNote(workspace_id=workspace_id, body=body, updated_by=user.id)
        db.add(note)
    else:
        note.body = body
        note.updated_by = user.id
        note.updated_at = models.utcnow()
    db.commit()
    db.refresh(note)
    result = {"workspace_id": workspace_id, "body": note.body, "updated_by": note.updated_by, "updated_at": note.updated_at.isoformat()}
    await manager.broadcast(workspace_id, {"type": "notes.updated", "notes": result})
    return result

@app.delete("/api/v1/workspaces/{workspace_id}", status_code=204)
def delete_workspace(workspace_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = db.get(models.Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if workspace.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the workspace owner can delete this workspace")
    db.delete(workspace)
    db.commit()
    return None

@app.post("/api/v1/workspaces/{workspace_id}/members", status_code=201)
def add_member(workspace_id: int, email: str, role: str = "member", user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_workspace_role(db, workspace_id, user.id, {"owner", "admin"})
    if role not in {"admin", "member", "viewer"}:
        raise HTTPException(status_code=422, detail="Invalid role")
    invitee = db.scalar(select(models.User).where(models.User.email == email.lower().strip()))
    if not invitee:
        raise HTTPException(status_code=404, detail="User must register before being added")
    existing = db.scalar(select(models.Membership).where(models.Membership.workspace_id == workspace_id, models.Membership.user_id == invitee.id))
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")
    db.add(models.Membership(workspace_id=workspace_id, user_id=invitee.id, role=role))
    db.commit()
    return {"workspace_id": workspace_id, "user_id": invitee.id, "role": role}

@app.get("/api/v1/workspaces/{workspace_id}/projects", response_model=list[ProjectOut])
def list_projects(workspace_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_workspace_role(db, workspace_id, user.id)
    return db.scalars(select(models.Project).where(models.Project.workspace_id == workspace_id).order_by(models.Project.id.desc())).all()

@app.post("/api/v1/workspaces/{workspace_id}/projects", response_model=ProjectOut, status_code=201)
def create_project(workspace_id: int, data: ProjectIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_workspace_role(db, workspace_id, user.id, {"owner", "admin", "member"})
    project = models.Project(workspace_id=workspace_id, name=data.name.strip(), description=data.description)
    db.add(project); db.commit(); db.refresh(project)
    return project

def task_to_out(task: models.Task):
    return {"id": task.id, "project_id": task.project_id, "title": task.title, "description": task.description,
            "status": task.status, "priority": task.priority, "assignee_id": task.assignee_id, "version": task.version}

@app.get("/api/v1/projects/{project_id}/completion")
def get_project_completion(project_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_workspace_role(db, project.workspace_id, user.id)
    status = db.scalar(select(models.ProjectCompletion).where(models.ProjectCompletion.project_id == project_id))
    return {"project_id": project_id, "is_completed": bool(status.is_completed) if status else False}

@app.put("/api/v1/projects/{project_id}/completion")
async def set_project_completion(project_id: int, data: dict = Body(...), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_workspace_role(db, project.workspace_id, user.id, {"owner", "admin", "member"})
    is_completed = data.get("is_completed")
    if not isinstance(is_completed, bool):
        raise HTTPException(status_code=422, detail="is_completed must be true or false")
    status = db.scalar(select(models.ProjectCompletion).where(models.ProjectCompletion.project_id == project_id))
    if not status:
        status = models.ProjectCompletion(project_id=project_id, is_completed=is_completed, updated_by=user.id)
        db.add(status)
    else:
        status.is_completed = is_completed
        status.updated_by = user.id
        status.updated_at = models.utcnow()
    db.commit()
    result = {"project_id": project_id, "is_completed": status.is_completed}
    await manager.broadcast(project.workspace_id, {"type": "project.completion.updated", "completion": result})
    return result

@app.get("/api/v1/projects/{project_id}/tasks", response_model=list[TaskOut])
def list_tasks(project_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if not project: raise HTTPException(status_code=404, detail="Project not found")
    require_workspace_role(db, project.workspace_id, user.id)
    return [task_to_out(t) for t in db.scalars(select(models.Task).where(models.Task.project_id == project_id).order_by(models.Task.id.desc())).all()]

@app.post("/api/v1/projects/{project_id}/tasks", response_model=TaskOut, status_code=201)
async def create_task(project_id: int, data: TaskIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if not project: raise HTTPException(status_code=404, detail="Project not found")
    require_workspace_role(db, project.workspace_id, user.id, {"owner", "admin", "member"})
    if data.assignee_id: require_workspace_role(db, project.workspace_id, data.assignee_id)
    task = models.Task(project_id=project_id, title=data.title.strip(), description=data.description, status=data.status,
                       priority=data.priority, assignee_id=data.assignee_id, created_by=user.id, version=1)
    db.add(task); db.flush()
    db.add(models.ActivityEvent(workspace_id=project.workspace_id, actor_id=user.id, event_type="task.created",
                                entity_type="task", entity_id=task.id, payload_json=json.dumps({"title": task.title})))
    db.commit(); db.refresh(task)
    await manager.broadcast(project.workspace_id, {"type": "task.created", "workspace_id": project.workspace_id, "task": task_to_out(task)})
    return task_to_out(task)

@app.patch("/api/v1/tasks/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, data: TaskUpdate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    project = db.get(models.Project, task.project_id)
    require_workspace_role(db, project.workspace_id, user.id, {"owner", "admin", "member"})
    if data.assignee_id: require_workspace_role(db, project.workspace_id, data.assignee_id)
    if task.version != data.version:
        raise HTTPException(status_code=409, detail="Task changed since you loaded it. Refresh and try again.")
    changes = data.model_dump(exclude_unset=True, exclude={"version"})
    for key, value in changes.items(): setattr(task, key, value)
    task.version += 1
    db.add(models.ActivityEvent(workspace_id=project.workspace_id, actor_id=user.id, event_type="task.updated",
                                entity_type="task", entity_id=task.id, payload_json=json.dumps(changes)))
    db.commit(); db.refresh(task)
    await manager.broadcast(project.workspace_id, {"type": "task.updated", "workspace_id": project.workspace_id, "task": task_to_out(task)})
    return task_to_out(task)

@app.post("/api/v1/tasks/{task_id}/comments", response_model=CommentOut, status_code=201)
async def create_comment(task_id: int, data: CommentIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    project = db.get(models.Project, task.project_id)
    require_workspace_role(db, project.workspace_id, user.id, {"owner", "admin", "member"})
    comment = models.Comment(task_id=task.id, author_id=user.id, body=data.body.strip())
    db.add(comment)
    db.add(models.ActivityEvent(workspace_id=project.workspace_id, actor_id=user.id, event_type="comment.created",
                                entity_type="task", entity_id=task.id, payload_json=json.dumps({"comment": data.body[:120]})))
    db.commit(); db.refresh(comment)
    await manager.broadcast(project.workspace_id, {"type": "comment.created", "workspace_id": project.workspace_id,
                                                   "task_id": task.id, "comment": {"id": comment.id, "author_id": comment.author_id, "body": comment.body}})
    return {"id": comment.id, "task_id": comment.task_id, "author_id": comment.author_id, "body": comment.body}

@app.get("/api/v1/tasks/{task_id}/comments", response_model=list[CommentOut])
def list_comments(task_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    project = db.get(models.Project, task.project_id)
    require_workspace_role(db, project.workspace_id, user.id)
    return db.scalars(select(models.Comment).where(models.Comment.task_id == task_id).order_by(models.Comment.id)).all()

@app.get("/api/v1/workspaces/{workspace_id}/activity")
def workspace_activity(workspace_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_workspace_role(db, workspace_id, user.id)
    events = db.scalars(select(models.ActivityEvent).where(models.ActivityEvent.workspace_id == workspace_id).order_by(models.ActivityEvent.id.desc()).limit(100)).all()
    return [{"id": e.id, "actor_id": e.actor_id, "event_type": e.event_type, "entity_type": e.entity_type,
             "entity_id": e.entity_id, "payload": json.loads(e.payload_json), "created_at": e.created_at.isoformat()} for e in events]

@app.websocket("/ws/workspaces/{workspace_id}")
async def workspace_socket(websocket: WebSocket, workspace_id: int, token: str = Query(...)):
    db = SessionLocal()
    try:
        from app.config import settings
        import jwt as jwt_lib
        try:
            payload = jwt_lib.decode(token, settings.secret_key, algorithms=["HS256"])
            user_id = int(payload["sub"])
        except Exception:
            await websocket.close(code=1008, reason="Invalid token"); return
        membership = db.scalar(select(models.Membership).where(models.Membership.workspace_id == workspace_id,
                                                               models.Membership.user_id == user_id))
        if not membership:
            await websocket.close(code=1008, reason="Not a workspace member"); return
        await manager.connect(workspace_id, websocket)
        await websocket.send_json({"type": "connection.ready", "workspace_id": workspace_id, "user_id": user_id})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(workspace_id, websocket)
        db.close()
