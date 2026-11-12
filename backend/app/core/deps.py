from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Business

bearer = HTTPBearer(auto_error=False)


def get_current_business(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> Business:
    if not creds:
        raise AppError("Not authenticated", 401, "unauthorized")
    business_id = decode_access_token(creds.credentials)
    if not business_id:
        raise AppError("Invalid or expired token", 401, "unauthorized")
    business = db.get(Business, business_id)
    if not business:
        raise AppError("Account not found", 401, "unauthorized")
    return business