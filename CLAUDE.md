# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A FastAPI Server-Sent Events (SSE) implementation. Currently in early scaffolding stage.

- **Python**: 3.14 (managed via `.python-version`)
- **Package manager**: `uv`
- **Framework**: FastAPI >= 0.136.0

## Commands

```bash
# Install dependencies
uv sync

# Run the app (once a FastAPI app is defined)
uv run uvicorn main:app --reload

# Add a dependency
uv add <package>
```

## Architecture

The project entry point is [main.py](main.py). It currently contains a placeholder `main()` function; the FastAPI `app` instance and SSE route handlers should be defined here (or in modules imported here).

SSE in FastAPI is typically implemented using `StreamingResponse` with `media_type="text/event-stream"` and an async generator that yields `data: ...\n\n`-formatted strings.