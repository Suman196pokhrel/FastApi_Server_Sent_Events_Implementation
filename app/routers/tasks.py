import asyncio
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models import Task, TaskCreatedResponse, TaskStatus, ProgressEvent

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Simple dictionary acting as our "database" — holds all tasks in memory.
# Key = task_id, Value = Task object with current status and progress.
tasks: dict[str, Task] = {}


async def _simulate_work(task_id: str) -> None:
    """
    Pretends to be a worker (like a Celery task) doing real work in the background.
    It updates the shared task object in 10 steps, sleeping 1 second between each.
    The SSE stream will pick up these changes and send them to the browser.
    """

    # Mark the task as running so the stream knows work has started
    tasks[task_id].status = TaskStatus.RUNNING

    # Simulate 10 steps of work — each step = 10% progress
    for step in range(1, 11):
        await asyncio.sleep(1)          # pretend this step takes 1 second
        tasks[task_id].progress = step * 10

    # All steps done — mark the task complete
    tasks[task_id].status = TaskStatus.DONE


@router.post("", response_model=TaskCreatedResponse, status_code=202)
async def create_task() -> TaskCreatedResponse:
    # Create a unique ID for this task
    task_id = str(uuid.uuid4())

    # Save a fresh task object in our in-memory store
    tasks[task_id] = Task(task_id=task_id)

    # Fire off the background worker WITHOUT waiting for it to finish.
    # asyncio.create_task() lets it run concurrently while we immediately
    # return the 202 response to the client.
    asyncio.create_task(_simulate_work(task_id))

    return TaskCreatedResponse(task_id=task_id, message="Task accepted")


async def _progress_event_generator(task_id: str) -> AsyncGenerator[str, None]:
    """
    This is an async generator — a function that yields values over time
    instead of returning one value and stopping.

    FastAPI's StreamingResponse calls this repeatedly and sends each
    yielded string to the browser over the open HTTP connection.

    The SSE wire format the browser expects:
        event: <event-name>\n
        data: <json-string>\n
        \n                       <-- blank line = end of one event
    """

    # If someone requests progress for a task that doesn't exist, send an
    # error event and stop immediately.
    if task_id not in tasks:
        error = ProgressEvent(
            task_id=task_id,
            status=TaskStatus.FAILED,
            progress=0,
            message="Task not found",
        )
        yield f"event: error\ndata: {error.model_dump_json()}\n\n"
        return

    # Keep looping and sending updates until the task is finished.
    while True:
        # Read the latest state of this task from our in-memory store
        task = tasks[task_id]

        # Package the current state into a ProgressEvent and serialise it to JSON
        event = ProgressEvent(
            task_id=task_id,
            status=task.status,
            progress=task.progress,
            message=_progress_message(task),
        )

        # Yield one SSE event — the browser receives this immediately
        # try/except GeneratorExit catches the moment the client disconnects
        # (closes the tab, navigates away, calls es.close()) so we can stop cleanly.
        try:
            yield f"event: progress\ndata: {event.model_dump_json()}\n\n"
        except GeneratorExit:
            break

        # Task finished — no more updates to send, close the stream
        if task.status in (TaskStatus.DONE, TaskStatus.FAILED):
            break

        # Wait 0.5 s before reading the task state again.
        # This controls how often the browser receives an update.
        await asyncio.sleep(0.5)


def _progress_message(task: Task) -> str:
    """Returns a human-readable message based on the current task state."""
    if task.status == TaskStatus.PENDING:
        return "Waiting to start…"
    if task.status == TaskStatus.RUNNING:
        return f"Processing… step {task.progress // 10} of 10"
    if task.status == TaskStatus.DONE:
        return "All done!"
    return "Something went wrong."


@router.get("/{task_id}/progress")
async def stream_task_progress(task_id: str) -> StreamingResponse:
    return StreamingResponse(
        _progress_event_generator(task_id),
        media_type="text/event-stream",
        headers={
            # Tell browsers and proxies not to buffer this response —
            # every event must be sent to the client right away.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )