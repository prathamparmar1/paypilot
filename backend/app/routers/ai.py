import time
import uuid
from collections import defaultdict, deque

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai import actions
from app.ai.assistant import active_pending, run_chat
from app.ai.invoice_parser import parse_invoice_text
from app.core.deps import get_current_business
from app.core.errors import AppError
from app.db.session import get_db
from app.models import AIMessage, Business, PendingAction
from app.schemas.ai import (
    ActionResultOut, ChatOut, ChatRequest, HistoryOut, InvoiceConfirm, MessageOut,
    ParseOut, ParseRequest, PendingActionOut,
)
from app.schemas.invoice import InvoiceOut
from app.services import invoice_service as svc

router = APIRouter(prefix="/ai", tags=["ai"])

_hits: dict = defaultdict(deque)


def _rate_limit(business_id, limit: int = 20, window: int = 60):
    now = time.time()
    q = _hits[business_id]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise AppError("Too many requests. Please wait a moment.", 429, "rate_limited")
    q.append(now)


def _pa_out(pa: PendingAction) -> PendingActionOut:
    return PendingActionOut(
        id=pa.id, action_type=pa.action_type, summary=pa.payload.get("summary", pa.action_type),
        expires_at=pa.expires_at,
    )


# ---------- invoice generation (Phase 7) ----------
@router.post("/invoice/parse", response_model=ParseOut)
def parse_invoice(
    data: ParseRequest, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    _rate_limit(business.id)
    return parse_invoice_text(db, business.id, data.text.strip())


@router.post("/invoice/confirm", response_model=InvoiceOut, status_code=201)
def confirm_invoice(
    data: InvoiceConfirm, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    inv = svc.create_invoice(db, business, data)
    if data.send:
        inv = svc.send_invoice(db, inv)
    return svc.to_out(inv)


# ---------- assistant (Phase 8) ----------
@router.post("/chat", response_model=ChatOut)
def chat(data: ChatRequest, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    _rate_limit(business.id)
    res = run_chat(db, business, data.message.strip())
    return ChatOut(
        reply=res["reply"],
        pending_actions=[_pa_out(p) for p in res["pending_actions"]],
        tools_used=res["tools_used"],
    )


@router.get("/chat/history", response_model=HistoryOut)
def history(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    msgs = list(
        reversed(
            db.scalars(
                select(AIMessage)
                .where(AIMessage.business_id == business.id)
                .order_by(AIMessage.created_at.desc())
                .limit(40)
            ).all()
        )
    )
    return HistoryOut(
        messages=[MessageOut(role=m.role, content=m.content, created_at=m.created_at) for m in msgs],
        pending_actions=[_pa_out(p) for p in active_pending(db, business.id)],
    )


@router.delete("/chat/history")
def clear_history(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    db.execute(delete(AIMessage).where(AIMessage.business_id == business.id))
    db.commit()
    return {"ok": True}


@router.post("/actions/{action_id}/confirm", response_model=ActionResultOut)
def confirm_action(
    action_id: uuid.UUID, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    inv, message = actions.confirm_action(db, business, action_id)
    return ActionResultOut(message=message, invoice=svc.to_out(svc.get_invoice(db, business.id, inv.id)))


@router.post("/actions/{action_id}/cancel", response_model=ActionResultOut)
def cancel_action(
    action_id: uuid.UUID, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    actions.cancel_action(db, business, action_id)
    return ActionResultOut(message="Okay, I cancelled that action.")