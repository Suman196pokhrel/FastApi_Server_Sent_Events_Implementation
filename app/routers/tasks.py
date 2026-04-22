import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models import Task, TaskCreatedResponse, TaskStatus, ProgressEvent

router = APIRouter(prefix="/tasks", tags=["tasks"])

# In-memory store — fine for learning; swap for Redis/DB in production
tasks: dict[str, Task] = {}


@router.post("", response_model=TaskCreatedResponse, status_code=202)
async def create_task() -> TaskCreatedResponse:
    task_id = str(uuid.uuid4())
    tasks[task_id] = Task(task_id=task_id)

    # TODO: kick off background work here (e.g. asyncio.create_task or BackgroundTasks)
    # The background work should update tasks[task_id].progress and tasks[task_id].status
    # as it runs so the SSE stream below can read those changes in real time.

    # Call a background or asyncIO function that updates the values in this created task , mocking clelery workers

    return TaskCreatedResponse(task_id=task_id, message="Task accepted")


async def _progress_event_generator(task_id: str) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE-formatted strings.

    The SSE wire format for a single event is:
        data: <payload>\n\n

    An event with an explicit event type looks like:
        event: progress\n
        data: <payload>\n\n

    Each field line ends with \n and the *event* ends with an extra \n.
    """
    if task_id not in tasks:
        # Yield a single error event then stop — client will see it and close.
        error = ProgressEvent(
            task_id=task_id,
            status=TaskStatus.FAILED,
            progress=0,
            message="Task not found",
        )
        yield f"event: error\ndata: {error.model_dump_json()}\n\n"
        return

    # TODO: poll (or await) real progress from tasks[task_id] in a loop.
    # Guidelines:
    #   - Check tasks[task_id].status / .progress each iteration.
    #   - Build a ProgressEvent, serialise it to JSON, and yield the SSE string.
    #   - Use `await asyncio.sleep(interval)` between polls so you don't busy-wait.
    #   - Break out of the loop when status is DONE or FAILED.
    #   - Handle client disconnect: wrap the yield in try/except GeneratorExit.

    # One illustrative yield so you can see the format while you build the loop:
    snapshot = tasks[task_id]
    event = ProgressEvent(
        task_id=task_id,
        status=snapshot.status,
        progress=snapshot.progress,
        message="Connected — waiting for progress updates",
    )
    yield f"event: progress\ndata: {event.model_dump_json()}\n\n"

    # TODO: replace the line above with your polling/push loop


@router.get("/{task_id}/progress")
async def stream_task_progress(task_id: str) -> StreamingResponse:
    return StreamingResponse(
        _progress_event_generator(task_id),
        media_type="text/event-stream",
        headers={
            # Tell proxies/browsers not to buffer the stream
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
