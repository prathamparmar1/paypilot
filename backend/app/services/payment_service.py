import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import (
    Invoice, InvoiceStatus, Payment, PaymentStatus, WebhookEvent, WebhookStatus,
)
from app.paypal import client as paypal
from app.paypal.client import PayPalError
from app.schemas.payment import PublicInvoice
from app.services.invoice_service import effective_status

logger = logging.getLogger(__name__)
settings = get_settings()


def get_payable_invoice(db: Session, token: str) -> Invoice:
    inv = db.scalar(
        select(Invoice)
        .options(joinedload(Invoice.customer), joinedload(Invoice.business))
        .where(Invoice.public_token == token)
    )
    if not inv or inv.status == InvoiceStatus.DRAFT:
        raise AppError("Invoice not found", 404, "not_found")
    return inv


def public_view(inv: Invoice) -> PublicInvoice:
    return PublicInvoice(
        business_name=inv.business.business_name,
        number=inv.number,
        customer_name=inv.customer.name,
        description=inv.description,
        amount=inv.amount,
        currency=inv.currency,
        due_date=inv.due_date,
        status=inv.status.value,
        display_status=effective_status(inv),
        paypal_client_id=settings.paypal_client_id,
    )


def record_capture(db: Session, invoice: Invoice, order: dict) -> Payment:
    """Validate a PayPal order payload and idempotently record the payment."""
    if order.get("status") != "COMPLETED":
        raise AppError("Payment was not completed", 402, "not_completed")
    try:
        unit = order["purchase_units"][0]
        cap = next(c for c in unit["payments"]["captures"] if c.get("status") == "COMPLETED")
        amount = Decimal(cap["amount"]["value"])
        currency = cap["amount"]["currency_code"]
    except (KeyError, IndexError, StopIteration, InvalidOperation):
        raise AppError("No completed capture found", 402, "not_completed")

    if unit.get("custom_id") != str(invoice.id):
        logger.error("Order %s does not belong to invoice %s", order.get("id"), invoice.id)
        raise AppError("Order does not match invoice", 400, "order_mismatch")
    if amount != invoice.amount or currency != invoice.currency:
        logger.error("Amount mismatch for invoice %s: %s %s", invoice.id, amount, currency)
        raise AppError("Paid amount does not match invoice", 409, "amount_mismatch")

    existing = db.scalar(select(Payment).where(Payment.paypal_capture_id == cap["id"]))
    if existing:
        return existing

    db.refresh(invoice, with_for_update=True)  # serialize concurrent captures/webhooks
    if invoice.status == InvoiceStatus.PAID:
        logger.warning("Invoice %s already PAID; recording additional capture %s", invoice.id, cap["id"])

    payment = Payment(
        invoice_id=invoice.id,
        business_id=invoice.business_id,
        paypal_order_id=order["id"],
        paypal_capture_id=cap["id"],
        amount=amount,
        currency=currency,
        status=PaymentStatus.COMPLETED,
        payer_email=(order.get("payer") or {}).get("email_address"),
        raw_response=order,
    )
    db.add(payment)
    invoice.status = InvoiceStatus.PAID
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.scalar(select(Payment).where(Payment.paypal_capture_id == cap["id"]))
    db.refresh(payment)
    return payment


def create_order(db: Session, token: str) -> str:
    inv = get_payable_invoice(db, token)
    if inv.status != InvoiceStatus.SENT:
        raise AppError("This invoice is not payable", 409, "invalid_state")

    if inv.paypal_order_id:
        try:
            existing = paypal.get_order(inv.paypal_order_id)
        except PayPalError:
            existing = None
        if existing and existing.get("status") == "COMPLETED":
            record_capture(db, inv, existing)
            raise AppError("This invoice has already been paid", 409, "already_paid")
        if existing and existing.get("status") == "CREATED":
            return inv.paypal_order_id

    try:
        order = paypal.create_order(inv.id, inv.number, inv.description, inv.amount, inv.currency)
    except PayPalError:
        raise AppError("Could not start payment. Please try again.", 502, "paypal_error")
    inv.paypal_order_id = order["id"]
    db.commit()
    return order["id"]


def capture(db: Session, token: str, order_id: str) -> Invoice:
    inv = get_payable_invoice(db, token)
    if inv.status == InvoiceStatus.PAID:
        return inv
    if order_id != inv.paypal_order_id:
        raise AppError("Order does not match invoice", 400, "order_mismatch")
    try:
        order = paypal.capture_order(order_id)
    except PayPalError as e:
        if e.issue == "ORDER_ALREADY_CAPTURED":
            try:
                order = paypal.get_order(order_id)
            except PayPalError:
                raise AppError("Could not verify payment", 502, "paypal_error")
        else:
            raise AppError("Payment could not be captured", 402, "capture_failed")
    record_capture(db, inv, order)
    db.refresh(inv)
    return inv


def _process_capture_completed(db: Session, event: dict) -> str:
    res = event.get("resource") or {}
    order_id = ((res.get("supplementary_data") or {}).get("related_ids") or {}).get("order_id")
    inv = None
    if order_id:
        inv = db.scalar(select(Invoice).where(Invoice.paypal_order_id == order_id))
    if not inv and res.get("custom_id"):
        try:
            inv = db.get(Invoice, uuid.UUID(res["custom_id"]))
        except ValueError:
            inv = None
    if not inv:
        return "ignored"
    # Never trust the webhook payload for money: re-fetch the order from PayPal.
    order = paypal.get_order(order_id or inv.paypal_order_id)
    record_capture(db, inv, order)
    return "processed"


def handle_webhook(db: Session, headers, event: dict) -> dict:
    if not settings.paypal_webhook_id:
        raise AppError("Webhook not configured", 503, "webhook_not_configured")
    if not paypal.verify_webhook(headers, event):
        raise AppError("Invalid webhook signature", 400, "invalid_signature")

    event_id = event.get("id")
    if not event_id:
        raise AppError("Missing event id", 400, "bad_event")

    row = db.scalar(select(WebhookEvent).where(WebhookEvent.paypal_event_id == event_id))
    if row and row.status in (WebhookStatus.PROCESSED, WebhookStatus.IGNORED):
        return {"status": "duplicate"}
    if not row:
        row = WebhookEvent(
            paypal_event_id=event_id, event_type=event.get("event_type", ""), payload=event
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return {"status": "duplicate"}
    row_id = row.id

    try:
        if event.get("event_type") == "PAYMENT.CAPTURE.COMPLETED":
            result = _process_capture_completed(db, event)
        else:
            result = "ignored"
        row = db.get(WebhookEvent, row_id)
        row.status = WebhookStatus.PROCESSED if result == "processed" else WebhookStatus.IGNORED
        row.processed_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": result}
    except Exception:
        db.rollback()
        logger.exception("Webhook %s failed", event_id)
        row = db.get(WebhookEvent, row_id)
        row.status = WebhookStatus.FAILED
        db.commit()
        raise AppError("Webhook processing failed", 500, "webhook_failed")