# FastAPI SSE — Task Progress

A hands-on implementation of **Server-Sent Events (SSE)** using FastAPI. Create a background task and watch its progress stream to the browser in real time — no WebSockets, no polling.

---

## How it works

1. Client clicks **Create Task** → `POST /tasks` returns a `task_id` immediately (202)
2. A background worker starts running concurrently, advancing progress every second
3. Browser opens an SSE connection to `GET /tasks/{task_id}/progress`
4. The server streams a progress event **only when the value changes** — via an `asyncio.Queue` shared between the worker and the stream
5. Stream closes automatically when the task reaches `done` or `failed`

---

## Stack

- **Python 3.14** — managed via `.python-version`
- **FastAPI** — HTTP framework + SSE via `StreamingResponse`
- **uvicorn** — ASGI server
- **uv** — package manager

---

## Running locally

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

---

## Project structure

```
app/
├── store.py          # shared in-memory state (tasks dict + queues dict)
├── worker.py         # background job — simulates work, pushes progress events
├── models.py         # Pydantic models (Task, ProgressEvent, TaskStatus …)
├── main.py           # FastAPI app + frontend route
└── routers/
    ├── health.py     # GET /health
    └── tasks.py      # POST /tasks  |  GET /tasks/{id}/progress (SSE)
```

---

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the frontend |
| `GET` | `/health` | Health check |
| `POST` | `/tasks` | Create a task, returns `task_id` |
| `GET` | `/tasks/{task_id}/progress` | SSE stream of progress events |

Interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Demo

https://github.com/user-attachments/assets/76b079e7-e6f7-41b7-ada5-518c760ac8c1
