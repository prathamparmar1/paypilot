import json
import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.gemini_client import generate_text
from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)
settings = get_settings()
MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")

SYSTEM = """You write short payment reminder messages for a small business owner to send to their customer.
Use ONLY the facts in the JSON. Never invent amounts, dates, names, fees, penalties or promises.
Write 2-4 sentences. Mention the invoice number, the amount written exactly as $<amount>, and the due date.
Match the requested tone. If previous_paid_invoices is greater than 0 you may thank them for earlier payments.
Do NOT include links, bank or payment details, phone numbers, threats or legal language, and no subject line.
Start with "Hi <customer>," and end with "Thank you," followed by the business name on a new line.
Plain text only, no markdown. Output only the message."""


def pay_link(inv: Invoice) -> str:
    return f"{settings.frontend_url.rstrip('/')}/pay/{inv.public_token}"


def reminder_facts(db: Session, inv: Invoice) -> dict:
    today = date.today()
    days_overdue = max((today - inv.due_date).days, 0)
    paid_before = db.scalar(
        select(func.count(Invoice.id)).where(
            Invoice.business_id == inv.business_id,
            Invoice.customer_id == inv.customer_id,
            Invoice.status == InvoiceStatus.PAID,
        )
    ) or 0
    if days_overdue >= 14:
        tone = "firm but polite"
    elif days_overdue > 0:
        tone = "friendly, gently mentioning the invoice is overdue"
    else:
        tone = "friendly and light, a heads-up about the due date"
    return {
        "business": inv.business.business_name,
        "customer": inv.customer.name,
        "invoice_number": inv.number,
        "amount": f"{inv.amount:.2f}",
        "due_date": inv.due_date.isoformat(),
        "days_overdue": days_overdue,
        "days_until_due": max((inv.due_date - today).days, 0),
        "previous_paid_invoices": paid_before,
        "tone": tone,
    }


def _template(f: dict) -> str:
    amt = f"${f['amount']}"
    if f["days_overdue"] > 0:
        body = (
            f"Hi {f['customer']}, this is a reminder that invoice {f['invoice_number']} for {amt} "
            f"was due on {f['due_date']} and is now {f['days_overdue']} day(s) overdue. "
            "Please arrange payment at your earliest convenience."
        )
    else:
        body = (
            f"Hi {f['customer']}, a quick reminder that invoice {f['invoice_number']} for {amt} "
            f"is due on {f['due_date']}."
        )
    return f"{body}\n\nThank you,\n{f['business']}"


def _valid(msg: str, f: dict) -> bool:
    if not msg or len(msg) > 900:
        return False
    for m in MONEY.finditer(msg):
        try:
            if Decimal(m.group(1).replace(",", "")) != Decimal(f["amount"]):
                return False
        except InvalidOperation:
            return False
    low = msg.lower()
    if "http" in low or "www." in low:
        return False
    return f["invoice_number"] in msg


def generate_reminder_text(db: Session, inv: Invoice) -> str:
    f = reminder_facts(db, inv)
    try:
        raw = generate_text(SYSTEM, "Facts (JSON):\n" + json.dumps(f))
        raw = raw.replace("**", "").strip()
        body = raw if _valid(raw, f) else None
        if body is None:
            logger.warning("Reminder text failed validation for invoice %s; using template", inv.id)
    except AppError as e:
        logger.warning("Reminder AI unavailable (%s); using template", e.code)
        body = None
    body = body or _template(f)
    return f"{body}\n\nPay securely online: {pay_link(inv)}"