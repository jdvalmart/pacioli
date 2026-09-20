"""Chat endpoints: per-month conversation with the AI assistant."""

from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from app import database as db
from app.schemas import ChatMessageIn, ChatMessageOut, ChatReply, MessageOut
from app.services.ai import ai_service


def _build_context(month: int, year: int) -> str:
    """Build a prompt-ready context with the financial state of a month."""
    summary = db.get_monthly_summary(month, year)
    budget_rows = db.get_budget_vs_actual(month, year)
    recent = db.get_recent_chat_context(month, year, turns=10)
    learnings = db.get_learnings_context()

    lines = [
        f"Mes: {month}/{year}",
        f"Ingresos: {summary.total_income}",
        f"Gastos: {summary.total_expense}",
        f"Balance: {summary.balance}",
    ]
    if budget_rows:
        lines.append("Presupuesto vs real:")
        for row in budget_rows:
            lines.append(
                f"- {row['name']}: presupuesto {row['budget']}, "
                f"gastado {row['actual']} ({row['percent']:.0f}%)"
            )
    if recent:
        lines.append("Conversación reciente:")
        lines.append(recent)
    if learnings:
        lines.append(learnings)
    return "\n".join(lines)


router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("", response_model=list[ChatMessageOut])
def chat_history(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
) -> list[ChatMessageOut]:
    """Return the chat history of a month, oldest first."""
    return [ChatMessageOut(**row) for row in db.get_chat_history(month, year)]


@router.delete("", response_model=MessageOut)
def clear_chat(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2100),
) -> MessageOut:
    """Delete all chat messages of a month."""
    db.clear_chat_history(month, year)
    return MessageOut(message="Chat history cleared")


@router.post("", response_model=ChatReply)
async def ask(payload: ChatMessageIn) -> ChatReply:
    """Ask a question to the AI assistant with financial context.

    The user's question is always persisted. If the AI service is
    unreachable, the answer is empty and an error is returned.
    """
    db.save_chat_message("user", payload.question, payload.month, payload.year)
    context = _build_context(payload.month, payload.year)
    response = await run_in_threadpool(ai_service.ask_question, payload.question, context)
    if response.success:
        db.save_chat_message("ai", response.text, payload.month, payload.year)
        return ChatReply(answer=response.text)
    return ChatReply(answer="", error=response.error or "Unknown error from AI service")
