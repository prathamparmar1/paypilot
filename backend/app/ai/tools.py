import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable, Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models import (
    ActionStatus, Business, Customer, Invoice, InvoiceStatus, PendingAction, Payment, PaymentStatus,
)
from app.services import dashboard_service
from app.services import invoice_service as svc

logger = logging.getLogger(__name__)


@dataclass
class ToolContext:
    db: Session
    business: Business
    pending: list = field(default_factory=list)
    calls: list = field(default_factory=list)


def _money(x) -> str:
    return f"{Decimal(x):.2f}"


# ---------- argument models ----------
class RevenueArgs(BaseModel):
    period: Literal["this_month", "last_month", "last_30_days", "this_year", "all_time"] = "this_month"


class ListInvoicesArgs(BaseModel):
    status: Literal["ALL", "DRAFT", "PENDING", "OVERDUE", "PAID", "CANCELLED"] = "ALL"
    customer_name: str | None = Field(default=None, max_length=160)
    limit: int = Field(default=10, ge=1, le=25)


class NoArgs(BaseModel):
    pass


class TopArgs(BaseModel):
    limit: int = Field(default=5, ge=1, le=10)


class InvoiceNumberArgs(BaseModel):
    invoice_number: str = Field(min_length=3, max_length=32)


# ---------- read tools ----------
def _range(period: str):
    now = datetime.now(timezone.utc)
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period == "this_month":
        return first, None
    if period == "last_month":
        return (first - timedelta(days=1)).replace(day=1), first
    if period == "last_30_days":
        return now - timedelta(days=30), None
    if period == "this_year":
        return first.replace(month=1), None
    return None, None


def get_revenue(ctx: ToolContext, a: RevenueArgs) -> dict:
    start, end = _range(a.period)
    q = select(func.coalesce(func.sum(Payment.amount), 0), func.count(Payment.id)).where(
        Payment.business_id == ctx.business.id, Payment.status == PaymentStatus.COMPLETED
    )
    if start:
        q = q.where(Payment.verified_at >= start)
    if end:
        q = q.where(Payment.verified_at < end)
    total, count = ctx.db.execute(q).one()
    return {"period": a.period, "total_revenue_usd": _money(total), "payment_count": count}


def _inv_row(i: Invoice) -> dict:
    row = {
        "number": i.number,
        "customer": i.customer.name,
        "amount_usd": _money(i.amount),
        "due_date": i.due_date.isoformat(),
        "status": svc.effective_status(i),
    }
    if row["status"] == "OVERDUE":
        row["days_overdue"] = (datetime.now(timezone.utc).date() - i.due_date).days
    return row


def list_invoices(ctx: ToolContext, a: ListInvoicesArgs) -> dict:
    rows = svc.list_invoices(ctx.db, ctx.business.id, None if a.status == "ALL" else a.status, 200, 0)
    if a.customer_name:
        rows = [i for i in rows if a.customer_name.lower() in i.customer.name.lower()]
    total = sum((i.amount for i in rows), Decimal("0"))
    return {
        "filter": a.status,
        "count": len(rows),
        "total_amount_usd": _money(total),
        "invoices": [_inv_row(i) for i in rows[: a.limit]],
        "truncated": len(rows) > a.limit,
    }


def pending_by_customer(ctx: ToolContext, a: NoArgs) -> dict:
    groups: dict[str, dict] = {}
    for i in svc.list_invoices(ctx.db, ctx.business.id, "SENT", 200, 0):
        g = groups.setdefault(
            i.customer.name,
            {"customer": i.customer.name, "outstanding": Decimal("0"), "invoice_count": 0, "overdue_count": 0},
        )
        g["outstanding"] += i.amount
        g["invoice_count"] += 1
        if svc.effective_status(i) == "OVERDUE":
            g["overdue_count"] += 1
    items = sorted(groups.values(), key=lambda g: g["outstanding"], reverse=True)
    for g in items:
        g["outstanding_usd"] = _money(g.pop("outstanding"))
    return {"customers_with_pending": len(items), "customers": items[:25]}


def get_outstanding_total(ctx: ToolContext, a: NoArgs) -> dict:
    s = dashboard_service.get_summary(ctx.db, ctx.business.id)
    return {
        "unpaid_total_usd": _money(s.pending_amount),
        "unpaid_invoice_count": s.pending_count,
        "overdue_total_usd": _money(s.overdue_amount),
        "overdue_invoice_count": s.overdue_count,
        "paid_invoice_count": s.paid_count,
        "all_time_revenue_usd": _money(s.total_revenue),
    }


def top_transactions(ctx: ToolContext, a: TopArgs) -> dict:
    rows = ctx.db.execute(
        select(Payment, Invoice.number, Customer.name)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .join(Customer, Customer.id == Invoice.customer_id)
        .where(Payment.business_id == ctx.business.id, Payment.status == PaymentStatus.COMPLETED)
        .order_by(Payment.amount.desc())
        .limit(a.limit)
    ).all()
    return {
        "transactions": [
            {
                "invoice": num,
                "customer": name,
                "amount_usd": _money(p.amount),
                "paid_on": p.verified_at.date().isoformat(),
            }
            for p, num, name in rows
        ]
    }


def _find_invoice(ctx: ToolContext, number: str) -> Invoice | None:
    return ctx.db.scalar(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.business_id == ctx.business.id, func.lower(Invoice.number) == number.strip().lower())
    )


def get_invoice_details(ctx: ToolContext, a: InvoiceNumberArgs) -> dict:
    inv = _find_invoice(ctx, a.invoice_number)
    if not inv:
        return {"error": f"No invoice {a.invoice_number} found"}
    out = _inv_row(inv)
    out["description"] = inv.description
    pay = ctx.db.scalar(select(Payment).where(Payment.invoice_id == inv.id).order_by(Payment.verified_at.desc()))
    if pay:
        out["payment"] = {"paid_on": pay.verified_at.date().isoformat(), "paypal_capture_id": pay.paypal_capture_id}
    return out


# ---------- write tools (propose only; user must confirm) ----------
def _propose(ctx: ToolContext, number: str, action_type: str) -> dict:
    inv = _find_invoice(ctx, number)
    if not inv:
        return {"error": f"No invoice {number} found"}
    if action_type == "send_invoice" and inv.status != InvoiceStatus.DRAFT:
        return {"error": f"Only draft invoices can be sent. {inv.number} is {inv.status.value.lower()}."}
    if action_type == "cancel_invoice" and inv.status not in (InvoiceStatus.DRAFT, InvoiceStatus.SENT):
        return {"error": f"{inv.number} is {inv.status.value.lower()} and cannot be cancelled."}

    now = datetime.now(timezone.utc)
    existing = ctx.db.scalar(
        select(PendingAction).where(
            PendingAction.business_id == ctx.business.id,
            PendingAction.action_type == action_type,
            PendingAction.status == ActionStatus.PENDING,
            PendingAction.expires_at > now,
            PendingAction.payload["invoice_id"].astext == str(inv.id),
        )
    )
    verb = "Send" if action_type == "send_invoice" else "Cancel"
    summary = f"{verb} invoice {inv.number} ({inv.customer.name}, ${_money(inv.amount)})"
    pa = existing or PendingAction(
        business_id=ctx.business.id,
        action_type=action_type,
        payload={"invoice_id": str(inv.id), "number": inv.number, "summary": summary},
        expires_at=now + timedelta(minutes=10),
    )
    if not existing:
        ctx.db.add(pa)
        ctx.db.commit()
        ctx.db.refresh(pa)
    ctx.pending.append(pa.id)
    return {
        "status": "awaiting_user_confirmation",
        "summary": summary,
        "note": "NOT executed yet. The user must press Confirm on the card shown in the chat.",
    }


def send_invoice(ctx: ToolContext, a: InvoiceNumberArgs) -> dict:
    return _propose(ctx, a.invoice_number, "send_invoice")


def cancel_invoice(ctx: ToolContext, a: InvoiceNumberArgs) -> dict:
    return _propose(ctx, a.invoice_number, "cancel_invoice")


# ---------- registry ----------
@dataclass
class ToolSpec:
    args_model: type[BaseModel]
    fn: Callable
    description: str
    parameters: dict


def _obj(props: dict, required: list[str] | None = None) -> dict:
    d = {"type": "OBJECT", "properties": props}
    if required:
        d["required"] = required
    return d


_INV_NUM = {"invoice_number": {"type": "STRING", "description": "Invoice number like INV-0003"}}

TOOLS: dict[str, ToolSpec] = {
    "get_revenue": ToolSpec(
        RevenueArgs, get_revenue,
        "Total verified revenue and payment count for a period.",
        _obj({"period": {"type": "STRING", "enum": ["this_month", "last_month", "last_30_days", "this_year", "all_time"]}}),
    ),
    "list_invoices": ToolSpec(
        ListInvoicesArgs, list_invoices,
        "List invoices with count and total. status PENDING = sent and not yet due; OVERDUE = sent and past due.",
        _obj({
            "status": {"type": "STRING", "enum": ["ALL", "DRAFT", "PENDING", "OVERDUE", "PAID", "CANCELLED"]},
            "customer_name": {"type": "STRING", "description": "Optional partial customer name filter"},
            "limit": {"type": "INTEGER", "description": "Max rows to return (1-25)"},
        }),
    ),
    "pending_by_customer": ToolSpec(
        NoArgs, pending_by_customer,
        "Customers who currently owe money, with outstanding amounts, sorted largest first.", _obj({}),
    ),
    "get_outstanding_total": ToolSpec(
        NoArgs, get_outstanding_total,
        "Total unpaid and overdue amounts and counts, plus paid count and all-time revenue.", _obj({}),
    ),
    "top_transactions": ToolSpec(
        TopArgs, top_transactions,
        "Largest verified payments, highest first.",
        _obj({"limit": {"type": "INTEGER", "description": "How many (1-10)"}}),
    ),
    "get_invoice_details": ToolSpec(
        InvoiceNumberArgs, get_invoice_details,
        "Details and status of one invoice by number.", _obj(_INV_NUM, ["invoice_number"]),
    ),
    "send_invoice": ToolSpec(
        InvoiceNumberArgs, send_invoice,
        "Prepare sending a DRAFT invoice to the customer. Requires user confirmation; does not execute.",
        _obj(_INV_NUM, ["invoice_number"]),
    ),
    "cancel_invoice": ToolSpec(
        InvoiceNumberArgs, cancel_invoice,
        "Prepare cancelling an unpaid invoice. Requires user confirmation; does not execute.",
        _obj(_INV_NUM, ["invoice_number"]),
    ),
}


def execute_tool(ctx: ToolContext, name: str, args: dict) -> dict:
    spec = TOOLS.get(name)
    if not spec:
        return {"error": f"Unknown tool {name}"}
    try:
        parsed = spec.args_model(**(args or {}))
    except ValidationError as e:
        return {"error": f"Invalid arguments: {e.errors()[0]['msg']}"}
    try:
        return spec.fn(ctx, parsed)
    except AppError as e:
        return {"error": e.message}
    except Exception:
        logger.exception("Tool %s failed", name)
        ctx.db.rollback()
        return {"error": "Tool failed"}