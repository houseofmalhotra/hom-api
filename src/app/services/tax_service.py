from sqlalchemy.orm import Session
from src.app.models.geography import Territory, Area, Region
from decimal import Decimal


class TaxService:
    @staticmethod
    def get_retailer_state_id(db: Session, territory_id: int) -> int:
        """Traverses the geographic hierarchy to find the State ID of a Retailer's Territory."""
        state_id = db.query(Region.state_id) \
            .join(Area, Area.region_id == Region.id) \
            .join(Territory, Territory.area_id == Area.id) \
            .filter(Territory.id == territory_id) \
            .scalar()

        return state_id

    @staticmethod
    def calculate_gst(base_amount: Decimal, gst_percent: Decimal, seller_state_id: int, buyer_state_id: int):
        """Calculates CGST/SGST vs IGST based on location."""
        gst_pct_dec = Decimal(str(gst_percent))

        total_tax_amount = base_amount * (gst_pct_dec / Decimal("100"))

        tax_breakdown = {
            "base_amount": base_amount,
            "cgst": Decimal("0.00"),
            "sgst": Decimal("0.00"),
            "igst": Decimal("0.00"),
            "total_tax": total_tax_amount,
            "final_amount": base_amount + total_tax_amount
        }

        if seller_state_id == buyer_state_id:
            tax_breakdown["cgst"] = total_tax_amount / Decimal("2")
            tax_breakdown["sgst"] = total_tax_amount / Decimal("2")
        else:
            tax_breakdown["igst"] = total_tax_amount

        return tax_breakdown