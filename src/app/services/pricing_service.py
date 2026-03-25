# src/app/services/pricing_service.py

from sqlalchemy.orm import Session
from src.app.models.pricing import TradeScheme, PartnerPriceBook
from decimal import Decimal


class PricingService:
    @staticmethod
    def get_base_price_for_partner(db: Session, product_id: int, default_base_price: Decimal, partner_type: str = None,
                                   partner_id: int = None) -> Decimal:

        # --- DEBUG LOGS TO TERMINAL ---
        print(f"\n--- PRICING DEBUG ---")
        print(
            f"Looking for custom price -> Product ID: {product_id}, Partner Type: '{partner_type}', Partner ID: {partner_id}")

        if partner_type and partner_id:
            custom_pricing = db.query(PartnerPriceBook).filter(
                PartnerPriceBook.product_id == product_id,
                PartnerPriceBook.partner_type == partner_type,
                PartnerPriceBook.partner_id == partner_id,
                PartnerPriceBook.is_active == True
            ).first()

            if custom_pricing:
                print(f"✅ SUCCESS: Custom Price Found -> ₹{custom_pricing.custom_selling_price}")
                return custom_pricing.custom_selling_price
            else:
                print(
                    f"❌ FAIL: No matching custom price found in database. Falling back to default: ₹{default_base_price}")
        else:
            print("❌ FAIL: Missing partner_type or partner_id. Falling back to default base price.")

        print("---------------------\n")
        return default_base_price

    @staticmethod
    def calculate_item_pricing(db: Session, product_id: int, base_price: Decimal, dispatch_qty: int,
                               partner_type: str = None, partner_id: int = None):
        """
        Evaluates active trade schemes for a product and applies partner-specific pricing.
        """
        actual_base_price = PricingService.get_base_price_for_partner(
            db=db,
            product_id=product_id,
            default_base_price=base_price,
            partner_type=partner_type,
            partner_id=partner_id
        )

        scheme = db.query(TradeScheme).filter(
            TradeScheme.product_id == product_id,
            TradeScheme.is_active == True
        ).first()

        final_price = actual_base_price
        free_qty = 0

        if scheme and dispatch_qty >= scheme.min_qty:
            if scheme.discount_percent > 0:
                discount_amount = actual_base_price * (Decimal(scheme.discount_percent) / 100)
                final_price = actual_base_price - discount_amount

            if scheme.free_qty > 0:
                multiplier = dispatch_qty // scheme.min_qty
                free_qty = multiplier * scheme.free_qty

        return final_price, free_qty