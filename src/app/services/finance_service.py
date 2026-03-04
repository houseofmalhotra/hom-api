from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.app.models.finance import FinancialLedger
from src.app.models.partner import SuperStockist, Distributor, Retailer
from decimal import Decimal

class FinanceService:
    @staticmethod
    def record_transaction(db: Session, party_type: str, party_id: int,
                           trans_type: str, amount: Decimal, ref_doc: str):
        amount = Decimal(amount)


        partner = None
        if party_type == "SuperStockist":
            partner = db.query(SuperStockist).filter(SuperStockist.id == party_id).with_for_update().first()
        elif party_type == "Distributor":
            partner = db.query(Distributor).filter(Distributor.id == party_id).with_for_update().first()
        elif party_type == "Retailer":
            partner = db.query(Retailer).filter(Retailer.id == party_id).with_for_update().first()
        else:
            raise ValueError(f"Unknown party type for finance: {party_type}")

        if not partner:
            raise HTTPException(status_code=404, detail=f"{party_type} ID {party_id} not found")


        debit = 0.00
        credit = 0.00

        current_balance = Decimal(partner.outstanding_balance or 0.00)

        if trans_type in ["INVOICE", "DEBIT_NOTE"]:
            debit = amount
            partner.outstanding_balance = current_balance + debit
        elif trans_type in ["PAYMENT", "CREDIT_NOTE"]:
            credit = amount
            partner.outstanding_balance = current_balance - credit
        else:
            raise ValueError(f"Unknown transaction type: {trans_type}")


        ledger_entry = FinancialLedger(
            party_type=party_type,
            party_id=party_id,
            transaction_type=trans_type,
            reference_document=ref_doc,
            debit_amount=debit,
            credit_amount=credit,
            closing_balance=partner.outstanding_balance
        )
        db.add(ledger_entry)

        
        db.flush()
        return ledger_entry