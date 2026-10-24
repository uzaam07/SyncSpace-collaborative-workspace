from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Literal

class RegisterIn(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class WorkspaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class WorkspaceOut(BaseModel):
    id: int
    name: str
    owner_id: int
    role: str

class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)

class ProjectOut(BaseModel):
    id: int
    workspace_id: int
    name: str
    description: str

class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=10000)
    status: Literal["todo", "in_progress", "done"] = "todo"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    assignee_id: int | None = None

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=10000)
    status: Literal["todo", "in_progress", "done"] | None = None
    priority: Literal["low", "medium", "high", "urgent"] | None = None
    assignee_id: int | None = None
    version: int = Field(ge=1)

class TaskOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: str
    status: str
    priority: str
    assignee_id: int | None
    version: int

class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)

class CommentOut(BaseModel):
    id: int
    task_id: int
    author_id: int
    body: str
