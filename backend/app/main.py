"""Pacioli API entry point.

Creates the FastAPI application, wires routers, CORS and the startup
lifespan (schema migration + daily automatic backup).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import auto_backup, init_db
from app.routers import budgets, categories, reports, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run schema migrations and the daily backup at startup."""
    init_db()
    auto_backup()
    yield


app = FastAPI(title="Pacioli API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(reports.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Return API health status."""
    return {"status": "ok"}
