import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, Invoice, InvoiceStatus, Payment, PaymentStatus
from app.services import dashboard_service
from app.services import invoice_service as inv_svc


def _m(x) -> str:
    return f"{Decimal(x):.2f}"


def _last_months(today: date, n: int = 6) -> list[tuple[int, int]]:
    y, m, out = today.year, today.month, []
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def compute_stats(db: Session, business_id: uuid.UUID) -> dict:
    today = date.today()
    summary = dashboard_service.get_summary(db, business_id)

    # monthly revenue (UTC months, last 6)
    months = _last_months(today)
    totals = {k: [Decimal("0"), 0] for k in months}
    pay_rows = db.execute(
        select(Payment, Invoice.due_date, Invoice.created_at, Invoice.number, Customer.name)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .join(Customer, Customer.id == Invoice.customer_id)
        .where(Payment.business_id == business_id, Payment.status == PaymentStatus.COMPLETED)
        .limit(5000)
    ).all()
    for p, *_ in pay_rows:
        t = p.verified_at.astimezone(timezone.utc)
        if (t.year, t.month) in totals:
            totals[(t.year, t.month)][0] += p.amount
            totals[(t.year, t.month)][1] += 1
    monthly = [
        {
            "month": f"{y}-{m:02d}",
            "label": date(y, m, 1).strftime("%b %Y"),
            "revenue_usd": _m(v[0]),
            "payments": v[1],
        }
        for (y, m), v in totals.items()
    ]
    this_m, last_m = totals[months[-1]][0], totals[months[-2]][0]
    mom = round(float((this_m - last_m) / last_m * 100), 1) if last_m > 0 else None

    # largest payments
    largest = sorted(pay_rows, key=lambda r: r[0].amount, reverse=True)[:3]
    largest_payments = [
        {"invoice": num, "customer": cname, "amount_usd": _m(p.amount), "paid_on": p.verified_at.date().isoformat()}
        for p, _due, _c, num, cname in largest
    ]

    # customer payment patterns
    pat: dict[str, dict] = {}
    for p, due, created, _num, cname in pay_rows:
        g = pat.setdefault(cname, {"paid": 0, "total": Decimal("0"), "on_time": 0, "days": []})
        g["paid"] += 1
        g["total"] += p.amount
        g["on_time"] += 1 if p.verified_at.date() <= due else 0
        g["days"].append((p.verified_at.date() - created.date()).days)
    patterns = sorted(
        (
            {
                "customer": c,
                "paid_invoices": g["paid"],
                "total_paid_usd": _m(g["total"]),
                "paid_on_time": g["on_time"],
                "avg_days_to_pay": round(sum(g["days"]) / len(g["days"]), 1),
            }
            for c, g in pat.items()
        ),
        key=lambda x: Decimal(x["total_paid_usd"]),
        reverse=True,
    )[:5]

    # overdue aging + top overdue customers
    buckets = {"1-7 days": [0, Decimal("0")], "8-30 days": [0, Decimal("0")], "31+ days": [0, Decimal("0")]}
    overdue_by_cust: dict[str, list] = {}
    for i in inv_svc.list_invoices(db, business_id, "OVERDUE", 200, 0):
        d = (today - i.due_date).days
        key = "1-7 days" if d <= 7 else "8-30 days" if d <= 30 else "31+ days"
        buckets[key][0] += 1
        buckets[key][1] += i.amount
        c = overdue_by_cust.setdefault(i.customer.name, [0, Decimal("0")])
        c[0] += 1
        c[1] += i.amount

    return {
        "totals": {
            "all_time_revenue_usd": _m(summary.total_revenue),
            "unpaid_total_usd": _m(summary.pending_amount),
            "unpaid_count": summary.pending_count,
            "overdue_total_usd": _m(summary.overdue_amount),
            "overdue_count": summary.overdue_count,
            "paid_invoice_count": summary.paid_count,
        },
        "monthly_revenue": monthly,
        "month_over_month_pct": mom,
        "overdue_aging": [{"bucket": k, "count": v[0], "amount_usd": _m(v[1])} for k, v in buckets.items()],
        "top_overdue_customers": [
            {"customer": c, "overdue_count": v[0], "overdue_usd": _m(v[1])}
            for c, v in sorted(overdue_by_cust.items(), key=lambda kv: kv[1][1], reverse=True)[:3]
        ],
        "largest_payments": largest_payments,
        "customer_patterns": patterns,
    }