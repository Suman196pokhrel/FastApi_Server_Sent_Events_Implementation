import asyncio

from app.models import ProgressEvent, TaskStatus
from app import store

# ---------------------------------------------------------------------------
# Background worker
#
# This is the part that does the "real work" — in a production app this
# would be replaced by actual business logic (processing a file, running a
# report, calling an external API, etc.).
#
# It runs concurrently alongside the HTTP server thanks to asyncio.
# Every time it finishes a step it pushes a ProgressEvent into the task's
# queue so the SSE stream can forward it to the browser immediately.
# ---------------------------------------------------------------------------

TOTAL_STEPS = 10


async def simulate_work(task_id: str) -> None:
    """
    Simulates a long-running job that completes in TOTAL_STEPS steps.
    Each step takes 1 second. Progress goes from 0 → 100 in equal increments.
    """
    queue = store.queues[task_id]

    # --- Signal that work has started ---
    # We push the very first event BEFORE the loop so the browser knows the
    # task is running right away, without waiting for the first sleep to finish.
    store.tasks[task_id].status = TaskStatus.RUNNING
    await queue.put(ProgressEvent(
        task_id=task_id,
        status=TaskStatus.RUNNING,
        progress=0,
        message="Starting…",
    ))

    # --- Do the work, one step at a time ---
    for step in range(1, TOTAL_STEPS + 1):

        # Simulate the time this step takes.
        # await yields control back to the event loop while we wait,
        # so the SSE stream and other requests keep working normally.
        await asyncio.sleep(1)

        # Calculate how far along we are
        progress = (step * 100) // TOTAL_STEPS
        is_last_step = step == TOTAL_STEPS
        new_status = TaskStatus.DONE if is_last_step else TaskStatus.RUNNING

        # Update the shared task state
        store.tasks[task_id].progress = progress
        store.tasks[task_id].status = new_status

        # Push a progress event — the SSE stream will pick this up instantly
        await queue.put(ProgressEvent(
            task_id=task_id,
            status=new_status,
            progress=progress,
            message="All done!" if is_last_step else f"Step {step} of {TOTAL_STEPS} complete",
        ))
