import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.errors import AppError
from app.db.session import get_db
from app.services import payment_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/paypal")
async def paypal_webhook(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    try:
        event = json.loads(raw)
    except ValueError:
        raise AppError("Invalid JSON", 400, "bad_request")
    return await run_in_threadpool(payment_service.handle_webhook, db, request.headers, event)