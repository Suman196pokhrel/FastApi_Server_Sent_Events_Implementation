from pydantic import BaseModel
from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Task(BaseModel):
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0  # 0–100


class TaskCreatedResponse(BaseModel):
    task_id: str
    message: str


class ProgressEvent(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int
    message: str