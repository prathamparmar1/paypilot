from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_business
from app.db.session import get_db
from app.models import Business
from app.schemas.business import BusinessOut, BusinessUpdate

router = APIRouter(prefix="/business", tags=["business"])


@router.get("/me", response_model=BusinessOut)
def get_me(business: Business = Depends(get_current_business)):
    return business


@router.patch("/me", response_model=BusinessOut)
def update_me(
    data: BusinessUpdate,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None or field == "phone":
            setattr(business, field, value)
    db.commit()
    db.refresh(business)
    return business