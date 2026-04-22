import asyncio
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models import TaskCreatedResponse, TaskStatus, ProgressEvent
from app import store, worker

# ---------------------------------------------------------------------------
# Tasks router
#
# Handles two endpoints:
#   POST /tasks              → creates a task and starts the background worker
#   GET  /tasks/{id}/progress → opens an SSE stream that sends progress updates
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ---------------------------------------------------------------------------
# POST /tasks  —  Create a new task
# ---------------------------------------------------------------------------

@router.post("", response_model=TaskCreatedResponse, status_code=202)
async def create_task() -> TaskCreatedResponse:
    task_id = str(uuid.uuid4())

    # Register the task in the shared store (creates the dict entry + queue)
    store.create_task_entry(task_id)

    # Start the background worker without waiting for it to finish.
    # asyncio.create_task() schedules it on the event loop and returns immediately,
    # so we can send the 202 response back to the client right away.
    asyncio.create_task(worker.simulate_work(task_id))

    return TaskCreatedResponse(task_id=task_id, message="Task accepted")


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}/progress  —  Stream progress updates via SSE
# ---------------------------------------------------------------------------

async def _sse_generator(task_id: str) -> AsyncGenerator[str, None]:
    """
    Async generator that yields Server-Sent Events for a given task.

    The browser keeps the HTTP connection open and receives each yielded
    string as it arrives. The format the browser expects is:

        event: <event-name>\n
        data: <json-string>\n
        \n                      ← blank line marks the end of one event
    """

    # Guard: if the task doesn't exist, send one error event and stop
    if task_id not in store.tasks:
        error = ProgressEvent(
            task_id=task_id,
            status=TaskStatus.FAILED,
            progress=0,
            message="Task not found",
        )
        yield f"event: error\ndata: {error.model_dump_json()}\n\n"
        return

    queue = store.queues[task_id]

    while True:
        # Wait here until the worker pushes a new ProgressEvent into the queue.
        # This does NOT busy-wait or poll — the event loop parks this coroutine
        # and only wakes it up when queue.put() is called by the worker.
        event = await queue.get()

        # Send the event to the browser.
        # GeneratorExit is raised if the client disconnects mid-stream.
        try:
            yield f"event: progress\ndata: {event.model_dump_json()}\n\n"
        except GeneratorExit:
            break

        # Task is finished — no more events will come, close the stream
        if event.status in (TaskStatus.DONE, TaskStatus.FAILED):
            break


@router.get("/{task_id}/progress")
async def stream_task_progress(task_id: str) -> StreamingResponse:
    return StreamingResponse(
        _sse_generator(task_id),
        media_type="text/event-stream",
        headers={
            # Prevent browsers and proxies from buffering the stream.
            # Without these, events might be held back and delivered in batches.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
