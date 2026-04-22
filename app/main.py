import pathlib

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.routers import health, tasks

app = FastAPI(title="FastAPI SSE — Task Progress")

app.include_router(health.router)
app.include_router(tasks.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend() -> HTMLResponse:
    html = pathlib.Path("index.html").read_text()
    return HTMLResponse(html)