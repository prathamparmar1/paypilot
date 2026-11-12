import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.routers import health
from app.routers import insights, reminders, ai, auth, business, customers, dashboard, health, invoices, payments, public_pay, webhooks

setup_logging()
settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(title="PayPilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "https://paypilotpaypal.vercel.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(business.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(invoices.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(public_pay.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(reminders.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")

@app.on_event("startup")
def on_startup():
    logger.info("PayPilot API started (env=%s)", settings.app_env)