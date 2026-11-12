import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.ai import reminder_writer
from app.core.errors import AppError
from app.models import Business, Invoice, InvoiceStatus, Reminder, ReminderStatus
from app.schemas.reminder import ReminderCandidate, ReminderOut
from app.services import invoice_service as inv_svc


def to_out(r: Reminder) -> ReminderOut:
    inv = r.invoice
    return ReminderOut(
        id=r.id,
        invoice_id=r.invoice_id,
        invoice_number=inv.number,
        customer_name=inv.customer.name,
        amount=inv.amount,
        currency=inv.currency,
        due_date=inv.due_date,
        invoice_status=inv_svc.effective_status(inv),
        message=r.message,
        status=r.status.value,
        created_at=r.created_at,
        approved_at=r.approved_at,
    )


def get_owned(db: Session, business_id: uuid.UUID, reminder_id: uuid.UUID) -> Reminder:
    r = db.scalar(
        select(Reminder)
        .options(joinedload(Reminder.invoice).joinedload(Invoice.customer))
        .where(Reminder.id == reminder_id, Reminder.business_id == business_id)
    )
    if not r:
        raise AppError("Reminder not found", 404, "not_found")
    return r


def list_reminders(db: Session, business_id: uuid.UUID, status: str | None) -> list[Reminder]:
    q = (
        select(Reminder)
        .options(joinedload(Reminder.invoice).joinedload(Invoice.customer))
        .where(Reminder.business_id == business_id)
    )
    if status:
        s = status.upper()
        if s not in ReminderStatus.__members__:
            raise AppError("Invalid status filter", 422, "validation_error")
        q = q.where(Reminder.status == ReminderStatus[s])
    return list(db.scalars(q.order_by(Reminder.created_at.desc()).limit(100)).unique())


def generate(db: Session, business: Business, invoice_id: uuid.UUID) -> Reminder:
    inv = inv_svc.get_invoice(db, business.id, invoice_id)
    if inv.status != InvoiceStatus.SENT:
        raise AppError("Reminders can only be created for sent, unpaid invoices", 409, "invalid_state")
    message = reminder_writer.generate_reminder_text(db, inv)
    r = db.scalar(
        select(Reminder).where(
            Reminder.invoice_id == inv.id,
            Reminder.business_id == business.id,
            Reminder.status == ReminderStatus.DRAFT,
        )
    )
    if r:
        r.message = message  # regenerate the existing draft instead of duplicating
    else:
        r = Reminder(business_id=business.id, invoice_id=inv.id, message=message)
        db.add(r)
    db.commit()
    return get_owned(db, business.id, r.id)


def edit(db: Session, business: Business, reminder_id: uuid.UUID, message: str) -> Reminder:
    r = get_owned(db, business.id, reminder_id)
    if r.status != ReminderStatus.DRAFT:
        raise AppError("Only draft reminders can be edited", 409, "invalid_state")
    r.message = message.strip()
    db.commit()
    return get_owned(db, business.id, r.id)


def approve(db: Session, business: Business, reminder_id: uuid.UUID) -> Reminder:
    r = get_owned(db, business.id, reminder_id)
    if r.status != ReminderStatus.DRAFT:
        raise AppError("This reminder was already handled", 409, "already_handled")
    if r.invoice.status != InvoiceStatus.SENT:
        raise AppError("This invoice is no longer unpaid", 409, "invalid_state")
    r.status = ReminderStatus.APPROVED
    r.approved_at = datetime.now(timezone.utc)
    db.commit()
    return get_owned(db, business.id, r.id)


def dismiss(db: Session, business: Business, reminder_id: uuid.UUID) -> Reminder:
    r = get_owned(db, business.id, reminder_id)
    if r.status != ReminderStatus.DRAFT:
        raise AppError("This reminder was already handled", 409, "already_handled")
    r.status = ReminderStatus.DISMISSED
    db.commit()
    return get_owned(db, business.id, r.id)


def candidates(db: Session, business_id: uuid.UUID) -> list[ReminderCandidate]:
    today = date.today()
    invoices = inv_svc.list_invoices(db, business_id, "SENT", 200, 0)
    drafts = set(
        db.scalars(
            select(Reminder.invoice_id).where(
                Reminder.business_id == business_id, Reminder.status == ReminderStatus.DRAFT
            )
        )
    )
    last = dict(
        db.execute(
            select(Reminder.invoice_id, func.max(Reminder.approved_at))
            .where(Reminder.business_id == business_id, Reminder.status == ReminderStatus.APPROVED)
            .group_by(Reminder.invoice_id)
        ).all()
    )
    out = [
        ReminderCandidate(
            invoice_id=i.id,
            number=i.number,
            customer_name=i.customer.name,
            amount=i.amount,
            currency=i.currency,
            due_date=i.due_date,
            display_status=inv_svc.effective_status(i),
            days_overdue=max((today - i.due_date).days, 0),
            has_draft=i.id in drafts,
            last_reminded_at=last.get(i.id),
        )
        for i in invoices
    ]
    out.sort(key=lambda c: (-c.days_overdue, c.due_date))
    return out