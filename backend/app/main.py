"""Pacioli API entry point.

Creates the FastAPI application. Routers arrive in later phases;
this skeleton exposes a health endpoint to validate the wiring.
"""

from fastapi import FastAPI

app = FastAPI(title="Pacioli API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Return API health status."""
    return {"status": "ok"}
