# src/app/v1/pricing.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from decimal import Decimal

# Adjust this import if your get_db function is located elsewhere (like an api/deps.py file)
from src.app.core.database import get_db
from src.app.models.pricing import PartnerPriceBook

router = APIRouter()


# --- Pydantic Schemas for Validation ---

class CustomPriceSet(BaseModel):
    partner_type: str
    partner_id: int
    product_id: int
    custom_selling_price: Decimal


class CustomPriceResponse(BaseModel):
    id: int
    partner_type: str
    partner_id: int
    product_id: int
    custom_selling_price: Decimal
    is_active: bool

    class Config:
        from_attributes = True


# --- API Routes ---

@router.post("/custom-price/", response_model=CustomPriceResponse)
def set_custom_price(price_data: CustomPriceSet, db: Session = Depends(get_db)):
    """
    Sets a custom selling price for a specific partner and product.
    If a price already exists, it updates it. Otherwise, it creates a new entry.
    """
    # Check if a custom price already exists for this partner and product
    existing_price = db.query(PartnerPriceBook).filter(
        PartnerPriceBook.partner_type == price_data.partner_type,
        PartnerPriceBook.partner_id == price_data.partner_id,
        PartnerPriceBook.product_id == price_data.product_id
    ).first()

    if existing_price:
        # Update the existing record
        existing_price.custom_selling_price = price_data.custom_selling_price
        existing_price.is_active = True
        db.commit()
        db.refresh(existing_price)
        return existing_price
    else:
        # Create a new record
        new_price = PartnerPriceBook(
            partner_type=price_data.partner_type,
            partner_id=price_data.partner_id,
            product_id=price_data.product_id,
            custom_selling_price=price_data.custom_selling_price,
            is_active=True
        )
        db.add(new_price)
        db.commit()
        db.refresh(new_price)
        return new_price


@router.get("/custom-price/{partner_type}/{partner_id}", response_model=List[CustomPriceResponse])
def get_custom_prices(partner_type: str, partner_id: int, db: Session = Depends(get_db)):
    """
    Retrieves all active custom prices set for a specific partner.
    """
    prices = db.query(PartnerPriceBook).filter(
        PartnerPriceBook.partner_type == partner_type,
        PartnerPriceBook.partner_id == partner_id,
        PartnerPriceBook.is_active == True
    ).all()

    return prices