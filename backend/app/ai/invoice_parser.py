import logging
import re
import uuid
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.gemini_client import generate_json
from app.ai.prompts import invoice_system_prompt, wrap_user_text
from app.ai.schemas import ParsedInvoiceLLM
from app.models import Customer
from app.schemas.ai import InvoiceDraft, ParseOut, SimilarCustomer

logger = logging.getLogger(__name__)
_email = TypeAdapter(EmailStr)

LABELS = {
    "customer_name": "the customer's name",
    "amount": "the amount (USD)",
    "description": "what the invoice is for",
    "due_date": "the due date",
}
MAX_AMOUNT = Decimal("99999999.99")


def _numbers_in(text: str) -> set[Decimal]:
    nums: set[Decimal] = set()
    for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)(\s?[kK]\b)?", text):
        try:
            val = Decimal(m.group(1).replace(",", ""))
        except InvalidOperation:
            continue
        if m.group(2):
            val *= 1000
        nums.add(val)
    return nums


def parse_invoice_text(db: Session, business_id: uuid.UUID, text: str) -> ParseOut:
    raw = generate_json(invoice_system_prompt(), wrap_user_text(text), ParsedInvoiceLLM)
    p = ParsedInvoiceLLM(**{k: raw.get(k) for k in ParsedInvoiceLLM.model_fields})
    today = date.today()
    text_l = text.lower()
    notes: list[str] = []

    # customer name (must appear in user text)
    name = (p.customer_name or "").strip() or None
    if name and name.lower() not in text_l:
        name = None

    # email (valid + must appear in user text)
    email = None
    if p.customer_email and p.customer_email.lower() in text_l:
        try:
            email = str(_email.validate_python(p.customer_email))
        except ValidationError:
            email = None

    # description
    desc = (p.description or "").strip() or None
    if desc and len(desc) < 3:
        desc = None

    # amount (must be a number that appears in user text)
    amount = None
    if p.amount is not None:
        try:
            a = Decimal(str(p.amount)).quantize(Decimal("0.01"))
            if 0 < a <= MAX_AMOUNT and a in _numbers_in(text):
                amount = a
        except (InvalidOperation, ValueError):
            amount = None

    # currency: app is USD-only
    cur = (p.currency or "").strip().upper()
    if cur and cur not in ("USD", "$"):
        amount = None
        notes.append(
            f"PayPilot invoices are in USD, but you mentioned {cur}. "
            "Please give the amount in USD."
        )

    # due date (backend resolves relative days)
    due = None
    if p.due_date:
        try:
            due = date.fromisoformat(p.due_date)
        except ValueError:
            due = None
    if due is None and p.due_in_days is not None and 0 <= p.due_in_days <= 365:
        due = today + timedelta(days=p.due_in_days)
    if due is not None and due < today:
        notes.append(f"The due date {due.isoformat()} is in the past. What due date should I use?")
        due = None

    draft = InvoiceDraft(
        customer_name=name, customer_email=email, description=desc, amount=amount, due_date=due
    )
    missing = [k for k in ("customer_name", "amount", "description", "due_date") if getattr(draft, k) is None]

    # customer matching
    existing, similar = False, []
    if name:
        rows = db.execute(select(Customer.id, Customer.name).where(Customer.business_id == business_id)).all()
        nl = name.lower()
        for cid, cname in rows:
            cl = cname.lower()
            if cl == nl:
                existing = True
            elif nl in cl or cl in nl:
                similar.append(SimilarCustomer(id=cid, name=cname))
        similar = similar[:3] if not existing else []

    if missing or notes:
        question = " ".join(notes)
        if missing:
            labels = [LABELS[m] for m in missing]
            joined = labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + " and " + labels[-1]
            question = (question + " " if question else "") + f"I still need {joined}."
        status = "needs_clarification"
    else:
        question, status = None, "ready"

    logger.info("AI invoice parse business=%s status=%s missing=%s", business_id, status, missing)
    return ParseOut(
        status=status,
        draft=draft,
        missing_fields=missing,
        question=question,
        existing_customer=existing,
        similar_customers=similar,
    )