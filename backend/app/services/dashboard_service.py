import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, Invoice, InvoiceStatus, Payment, PaymentStatus
from app.schemas.dashboard import DashboardSummary, RecentPayment


def get_summary(db: Session, business_id: uuid.UUID) -> DashboardSummary:
    today = date.today()

    revenue = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.business_id == business_id, Payment.status == PaymentStatus.COMPLETED
        )
    )

    def sent_stats(*extra):
        row = db.execute(
            select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0)).where(
                Invoice.business_id == business_id, Invoice.status == InvoiceStatus.SENT, *extra
            )
        ).one()
        return row[0], row[1]

    pending_count, pending_amount = sent_stats()  # all unpaid sent invoices (includes overdue)
    overdue_count, overdue_amount = sent_stats(Invoice.due_date < today)

    paid_count = db.scalar(
        select(func.count(Invoice.id)).where(
            Invoice.business_id == business_id, Invoice.status == InvoiceStatus.PAID
        )
    )

    rows = db.execute(
        select(Payment, Invoice.number, Customer.name)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .join(Customer, Customer.id == Invoice.customer_id)
        .where(Payment.business_id == business_id, Payment.status == PaymentStatus.COMPLETED)
        .order_by(Payment.verified_at.desc())
        .limit(5)
    ).all()

    return DashboardSummary(
        total_revenue=revenue,
        pending_amount=pending_amount,
        pending_count=pending_count,
        overdue_amount=overdue_amount,
        overdue_count=overdue_count,
        paid_count=paid_count or 0,
        recent_payments=[
            RecentPayment(
                id=p.id,
                invoice_number=num,
                customer_name=name,
                amount=p.amount,
                currency=p.currency,
                verified_at=p.verified_at,
            )
            for p, num, name in rows
        ],
    )