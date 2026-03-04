from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from src.app.core.database import get_db
from src.app.schemas.finance import PaymentCreate, FinancialLedgerRead
from src.app.services.finance_service import FinanceService
from src.app.models.finance import FinancialLedger
from src.app.models.partner import SuperStockist, Distributor, Retailer
from src.app.core.security import check_permissions, get_current_user
from src.app.models.user import User
from src.app.services.permission_service import PermissionService

router = APIRouter()


@router.post("/payments", status_code=status.HTTP_201_CREATED)
def receive_payment(
        payment_in: PaymentCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_payments"))
):
    user_perms = [p.name for p in current_user.role.permissions] if current_user.role else []
    if "manage_roles" not in user_perms:  # If not Admin
        model_map = {"SuperStockist": SuperStockist, "Distributor": Distributor, "Retailer": Retailer}
        if payment_in.party_type in model_map:
            target_model = model_map[payment_in.party_type]
            PermissionService.verify_internal_jurisdiction(db, current_user, target_model, payment_in.party_id)

    """Logs a payment received from a partner and reduces their outstanding balance."""
    try:
        entry = FinanceService.record_transaction(
            db=db,
            party_type=payment_in.party_type,
            party_id=payment_in.party_id,
            trans_type="PAYMENT",
            amount=payment_in.amount,
            ref_doc=payment_in.reference_document
        )
        db.commit()
        return {
            "message": "Payment recorded successfully",
            "new_outstanding_balance": entry.closing_balance
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ledger/{party_type}/{party_id}", response_model=list[FinancialLedgerRead])
def get_party_ledger(
        party_type: str,
        party_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("view_ledgers"))
):
    """Fetches the financial history/statement of account for a specific partner."""
    return db.query(FinancialLedger).filter(
        FinancialLedger.party_type == party_type,
        FinancialLedger.party_id == party_id
    ).order_by(FinancialLedger.created_at.desc()).all()


@router.get("/summary", summary="Get Scoped Finance Summary")
def get_company_finance_summary(
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("view_ledgers"))
):
    """Calculates receivables and recent transactions scoped to the user's hierarchy."""

    user_perms = [p.name for p in current_user.role.permissions] if current_user.role else []
    is_admin = "manage_roles" in user_perms

    ss_query = db.query(func.sum(SuperStockist.outstanding_balance))
    dist_query = db.query(func.sum(Distributor.outstanding_balance))
    ret_query = db.query(func.sum(Retailer.outstanding_balance))

    ss_id_query = db.query(SuperStockist.id)
    dist_id_query = db.query(Distributor.id)
    ret_id_query = db.query(Retailer.id)

    ledger_query = db.query(FinancialLedger)

    if not is_admin:
        ss_query = PermissionService.apply_geo_filter(ss_query, SuperStockist, current_user)
        dist_query = PermissionService.apply_geo_filter(dist_query, Distributor, current_user)
        ret_query = PermissionService.apply_geo_filter(ret_query, Retailer, current_user)

        allowed_ss = [s[0] for s in PermissionService.apply_geo_filter(ss_id_query, SuperStockist, current_user).all()]
        allowed_dist = [d[0] for d in
                        PermissionService.apply_geo_filter(dist_id_query, Distributor, current_user).all()]
        allowed_ret = [r[0] for r in PermissionService.apply_geo_filter(ret_id_query, Retailer, current_user).all()]

        ledger_query = ledger_query.filter(
            or_(
                and_(FinancialLedger.party_type == "SuperStockist", FinancialLedger.party_id.in_(allowed_ss)),
                and_(FinancialLedger.party_type == "Distributor", FinancialLedger.party_id.in_(allowed_dist)),
                and_(FinancialLedger.party_type == "Retailer", FinancialLedger.party_id.in_(allowed_ret))
            )
        )

    ss_owed = ss_query.scalar() or 0.00
    dist_owed = dist_query.scalar() or 0.00
    ret_owed = ret_query.scalar() or 0.00
    total_receivables = float(ss_owed) + float(dist_owed) + float(ret_owed)

    recent_transactions = ledger_query.order_by(FinancialLedger.created_at.desc()).limit(50).all()

    return {
        "metrics": {
            "total_receivables": total_receivables,
            "breakdown": {
                "super_stockists": float(ss_owed),
                "distributors": float(dist_owed),
                "retailers": float(ret_owed)
            }
        },
        "recent_global_transactions": recent_transactions
    }