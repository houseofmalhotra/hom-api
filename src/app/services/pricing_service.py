from sqlalchemy.orm import Session
from src.app.models.pricing import TradeScheme, PartnerPriceBook
from decimal import Decimal
from src.app.models.product import ProductMaster # FIX: Added missing ProductMaster import

# 🚨 DELETED the top-level import of get_base_unit_multiplier to break the loop!

def calculate_invoice_line_price(db: Session, partner_id: int, product_id: int, order_qty: int):
    product = db.query(ProductMaster).filter(ProductMaster.id == product_id).first()

    # 🚨 FIX: Import the helper function INSIDE this function.
    # This forces Python to wait until the function is actually called before trying to load it.
    from src.app.services.order_service import get_base_unit_multiplier

    # 1. Get dynamic multiplier
    pkg_multiplier = get_base_unit_multiplier(db, product_id)

    # 2. Find total volume for discount thresholds
    total_base_volume = order_qty * pkg_multiplier

    # 3. Determine the unit price
    # If base_price is the price of 1 base unit (e.g., 1 Tuck = ₹10),
    # then the SKU price is base_price * multiplier
    sku_base_price = product.base_price * pkg_multiplier

    final_sku_price = sku_base_price
    applied_discount_percent = Decimal("0.00")

    # 4. Evaluate Trade Schemes based on actual volume, NOT just the box quantity
    active_schemes = db.query(TradeScheme).filter(
        TradeScheme.partner_id == partner_id,
        TradeScheme.is_active == True
    ).all()

    for scheme in active_schemes:
        # Evaluate against the unpacked total_base_volume
        if total_base_volume >= scheme.min_base_volume_threshold:
            if scheme.discount_percent > applied_discount_percent:
                applied_discount_percent = scheme.discount_percent

    # 5. Apply the best scheme discount
    if applied_discount_percent > 0:
        discount_multiplier = (Decimal("100") - applied_discount_percent) / Decimal("100")
        final_sku_price = final_sku_price * discount_multiplier

    line_total = final_sku_price * order_qty

    return {
        "sku_price": final_sku_price,
        "line_total": line_total,
        "total_base_units_calculated": total_base_volume,
        "discount_applied": applied_discount_percent
    }

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