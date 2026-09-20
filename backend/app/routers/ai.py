"""AI service configuration endpoints."""

from dataclasses import asdict

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.config import AIConfig, config_manager
from app.schemas import AIConfigIn, AIConfigOut, ConnectionTestOut, MessageOut
from app.services.ai import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/config", response_model=AIConfigOut)
def get_config() -> AIConfigOut:
    """Return the current AI service configuration."""
    return AIConfigOut(**asdict(config_manager.get_ai_config()))


@router.put("/config", response_model=MessageOut)
def update_config(payload: AIConfigIn) -> MessageOut:
    """Update the AI service configuration and persist it."""
    config_manager.set_ai_config(AIConfig(**payload.model_dump()))
    ai_service.reload_config()
    return MessageOut(message="AI configuration saved")


@router.post("/test-connection", response_model=ConnectionTestOut)
async def test_connection() -> ConnectionTestOut:
    """Check whether the AI service is reachable with the current config."""
    success, message = await run_in_threadpool(ai_service.check_connection)
    return ConnectionTestOut(success=success, message=message)
