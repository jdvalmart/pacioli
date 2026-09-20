"""Pacioli API entry point.

Creates the FastAPI application, wires routers, CORS and the startup
lifespan (schema migration + daily automatic backup).

In production the API also serves the built frontend (frontend/dist),
so a single uvicorn process hosts the whole application.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.database import auto_backup, init_db
from app.routers import (
    accounts,
    ai,
    budgets,
    categories,
    chat,
    credit_cards,
    reports,
    transactions,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run schema migrations and the daily backup at startup."""
    init_db()
    auto_backup()
    yield


app = FastAPI(title="Pacioli API", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All domain endpoints live under /api so the SPA owns the root path
# in production without colliding with API routes.
api_prefix = "/api"
app.include_router(categories.router, prefix=api_prefix)
app.include_router(transactions.router, prefix=api_prefix)
app.include_router(budgets.router, prefix=api_prefix)
app.include_router(reports.router, prefix=api_prefix)
app.include_router(chat.router, prefix=api_prefix)
app.include_router(ai.router, prefix=api_prefix)
app.include_router(accounts.router, prefix=api_prefix)
app.include_router(credit_cards.router, prefix=api_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    """Return API health status."""
    return {"status": "ok"}


def _frontend_dist() -> Path | None:
    """Return the built frontend directory, or None if not built.

    The location can be overridden with PACIOLI_FRONTEND_DIST (used by
    tests). Resolution is lazy so the build only has to exist at
    request time, not at import time.
    """
    override = os.environ.get("PACIOLI_FRONTEND_DIST")
    if override:
        candidate = Path(override)
    else:
        candidate = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    return candidate if candidate.is_dir() else None


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str) -> FileResponse:
    """Serve the built SPA, falling back to index.html for client routes.

    Registered last, so API routes always take precedence. Static
    assets are resolved inside the dist directory only.
    """
    dist = _frontend_dist()
    if dist is None:
        raise HTTPException(status_code=404, detail="Frontend not built")
    target = (dist / full_path).resolve()
    if target.is_file() and dist.resolve() in target.parents:
        return FileResponse(target)
    return FileResponse(dist / "index.html")
