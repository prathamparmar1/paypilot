import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import ActionStatus, AIMessage, Business, PendingAction
from app.services import invoice_service as svc


def _load_locked(db: Session, business_id, action_id: uuid.UUID) -> PendingAction:
    pa = db.scalar(
        select(PendingAction)
        .where(PendingAction.id == action_id, PendingAction.business_id == business_id)
        .with_for_update()
    )
    if not pa:
        raise AppError("Action not found", 404, "not_found")
    if pa.status != ActionStatus.PENDING:
        db.rollback()
        raise AppError("This action was already handled", 409, "already_handled")
    return pa


def confirm_action(db: Session, business: Business, action_id: uuid.UUID):
    pa = _load_locked(db, business.id, action_id)
    if pa.expires_at < datetime.now(timezone.utc):
        pa.status = ActionStatus.EXPIRED
        db.commit()
        raise AppError("This action expired. Please ask again.", 409, "expired")

    pa.status = ActionStatus.CONFIRMED  # committed together with the service call below
    try:
        inv = svc.get_invoice(db, business.id, uuid.UUID(pa.payload["invoice_id"]))
        if pa.action_type == "send_invoice":
            inv = svc.send_invoice(db, inv)
            message = f"Done: invoice {inv.number} has been sent."
        elif pa.action_type == "cancel_invoice":
            inv = svc.cancel_invoice(db, inv)
            message = f"Done: invoice {inv.number} has been cancelled."
        else:
            raise AppError("Unsupported action", 400, "bad_action")
    except AppError:
        db.rollback()
        raise

    db.add(AIMessage(business_id=business.id, role="assistant", content=message))
    db.commit()
    return inv, message


def cancel_action(db: Session, business: Business, action_id: uuid.UUID) -> None:
    pa = _load_locked(db, business.id, action_id)
    pa.status = ActionStatus.CANCELLED
    db.add(AIMessage(business_id=business.id, role="assistant", content="Okay, I cancelled that action."))
    db.commit()