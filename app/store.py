import asyncio

from app.models import Task, ProgressEvent

# ---------------------------------------------------------------------------
# In-memory store
#
# Think of these two dicts as our mock database.
# Both are keyed by task_id so we can look up any task instantly.
#
# In a real app you would replace these with Redis or a proper database,
# but for learning purposes a plain dict is perfectly fine.
# ---------------------------------------------------------------------------

# Holds the current state of every task (status, progress).
tasks: dict[str, Task] = {}

# Holds one asyncio.Queue per task.
# The background worker PUTS progress events into the queue.
# The SSE stream GETS events out of the queue and sends them to the browser.
queues: dict[str, asyncio.Queue[ProgressEvent]] = {}


def create_task_entry(task_id: str) -> None:
    """
    Registers a brand-new task in both dicts.
    Call this once when a task is first created, before starting the worker.
    """
    tasks[task_id] = Task(task_id=task_id)
    queues[task_id] = asyncio.Queue()
