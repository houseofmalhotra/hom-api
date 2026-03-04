from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from src.app.core.database import get_db
from src.app.core.security import get_current_user, check_permissions
from src.app.models.user import User
from src.app.models.partner import SuperStockist, Distributor, Retailer
from src.app.services.permission_service import PermissionService
from src.app.schemas.inventory import ProductionLogCreate, StockLedgerRead, StockUpdate, FactoryCreate
from src.app.models.inventory import DailyProductionLog, FactoryInventory, StockLedger, SSInventory, \
    DistributorInventory, RetailerInventory, FactoryMaster
from src.app.services.stock_service import StockService

router = APIRouter()



@router.get("/factory/{factory_id}")
def get_factory_stock(
        factory_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("view_inventory"))
):
    role_name = current_user.role.name if current_user.role else ""
    if role_name in ["SuperStockist", "Distributor", "Retailer"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Partners cannot view internal factory stock.")

    stock = db.query(FactoryInventory).filter(FactoryInventory.factory_id == factory_id).all()
    return [{"product_id": s.product_id, "batch_number": s.batch_number, "current_stock": s.current_stock_qty} for s in
            stock]


@router.get("/ss/{ss_id}")
def get_ss_stock(
        ss_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("view_inventory"))
):
    role_name = current_user.role.name if current_user.role else ""
    if role_name == "SuperStockist":
        partner = db.query(SuperStockist).filter(SuperStockist.user_id == current_user.id).first()
        if not partner or partner.id != ss_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view competitor inventory.")
    elif role_name in ["Distributor", "Retailer"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to view upstream tier stock.")

    stock = db.query(SSInventory).filter(SSInventory.ss_id == ss_id).all()
    return [{"product_id": s.product_id, "batch_number": s.batch_number, "current_stock": s.current_stock_qty} for s in
            stock]


@router.get("/distributor/{distributor_id}")
def get_distributor_stock(
        distributor_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("view_inventory"))
):
    role_name = current_user.role.name if current_user.role else ""
    if role_name == "Distributor":
        partner = db.query(Distributor).filter(Distributor.user_id == current_user.id).first()
        if not partner or partner.id != distributor_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view competitor inventory.")
    elif role_name == "Retailer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to view upstream tier stock.")

    stock = db.query(DistributorInventory).filter(DistributorInventory.distributor_id == distributor_id).all()
    return [{"product_id": s.product_id, "batch_number": s.batch_number, "current_stock": s.current_stock_qty} for s in
            stock]


@router.get("/retailer/{retailer_id}")
def get_retailer_stock(
        retailer_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("view_inventory"))
):
    role_name = current_user.role.name if current_user.role else ""
    if role_name == "Retailer":
        partner = db.query(Retailer).filter(Retailer.user_id == current_user.id).first()
        if not partner or partner.id != retailer_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view competitor inventory.")

    stock = db.query(RetailerInventory).filter(RetailerInventory.retailer_id == retailer_id).all()
    return [{"product_id": s.product_id, "batch_number": s.batch_number, "current_stock": s.current_stock_qty} for s in
            stock]


@router.get("/ledger", response_model=list[StockLedgerRead])
def get_stock_ledger(
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("view_inventory"))
):
    query = db.query(StockLedger)

    if not current_user.role:
        return []

    user_perms = [p.name for p in current_user.role.permissions] if current_user.role else []
    is_admin = "manage_roles" in user_perms
    role_name = current_user.role.name

    if is_admin:
        return query.order_by(StockLedger.created_at.desc()).limit(100).all()


    if role_name == "SuperStockist":
        partner = db.query(SuperStockist).filter(SuperStockist.user_id == current_user.id).first()
        if not partner: return []
        query = query.filter(StockLedger.entity_type == "SuperStockist", StockLedger.entity_id == partner.id)

    elif role_name == "Distributor":
        partner = db.query(Distributor).filter(Distributor.user_id == current_user.id).first()
        if not partner: return []
        query = query.filter(StockLedger.entity_type == "Distributor", StockLedger.entity_id == partner.id)

    elif role_name == "Retailer":
        partner = db.query(Retailer).filter(Retailer.user_id == current_user.id).first()
        if not partner: return []
        query = query.filter(StockLedger.entity_type == "Retailer", StockLedger.entity_id == partner.id)

    else:
        ss_id_query = db.query(SuperStockist.id)
        dist_id_query = db.query(Distributor.id)
        ret_id_query = db.query(Retailer.id)

        allowed_ss = [s[0] for s in PermissionService.apply_geo_filter(ss_id_query, SuperStockist, current_user).all()]
        allowed_dist = [d[0] for d in
                        PermissionService.apply_geo_filter(dist_id_query, Distributor, current_user).all()]
        allowed_ret = [r[0] for r in PermissionService.apply_geo_filter(ret_id_query, Retailer, current_user).all()]

        conditions = []
        conditions.append(StockLedger.entity_type == "Factory")

        if allowed_ss:
            conditions.append(and_(StockLedger.entity_type == "SuperStockist", StockLedger.entity_id.in_(allowed_ss)))
        if allowed_dist:
            conditions.append(and_(StockLedger.entity_type == "Distributor", StockLedger.entity_id.in_(allowed_dist)))
        if allowed_ret:
            conditions.append(and_(StockLedger.entity_type == "Retailer", StockLedger.entity_id.in_(allowed_ret)))

        if conditions:
            query = query.filter(or_(*conditions))
        else:
            return []

    return query.order_by(StockLedger.created_at.desc()).limit(100).all()



@router.post("/factory/produce", status_code=status.HTTP_201_CREATED)
def log_factory_production(
        log_in: ProductionLogCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_inventory"))
):
    try:
        production_log = DailyProductionLog(
            product_id=log_in.product_id,
            factory_id=log_in.factory_id,
            quantity_produced=log_in.quantity_produced,
            batch_number=log_in.batch_number,
            production_date=log_in.production_date
        )
        db.add(production_log)

        StockService.update_stock(
            db=db,
            entity_type="Factory",
            entity_id=log_in.factory_id,
            product_id=log_in.product_id,
            qty_change=log_in.quantity_produced,
            ref_doc=f"BATCH-{log_in.batch_number}",
            trans_type="PRODUCTION",
            batch_number=log_in.batch_number
        )

        db.commit()
        return {"message": f"Successfully produced {log_in.quantity_produced} units and updated inventory."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{entity_type}/{entity_id}/adjust", status_code=status.HTTP_200_OK)
def adjust_stock(
        entity_type: str,
        entity_id: int,
        update_in: StockUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_inventory"))
):
    formatted_entity_type = entity_type.capitalize()
    if formatted_entity_type == "Superstockist":
        formatted_entity_type = "SuperStockist"

    role_name = current_user.role.name if current_user.role else ""
    if role_name in ["SuperStockist", "Distributor", "Retailer"]:
        if formatted_entity_type != role_name:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Partners can only audit {role_name} inventory.")

        partner_model = globals()[role_name]
        partner = db.query(partner_model).filter(partner_model.user_id == current_user.id).first()
        if not partner or partner.id != entity_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot audit a competitor's inventory.")

    try:
        stock_record = StockService.update_stock(
            db=db,
            entity_type=formatted_entity_type,
            entity_id=entity_id,
            product_id=update_in.product_id,
            qty_change=update_in.quantity_change,
            ref_doc=update_in.reference_document,
            trans_type=update_in.transaction_type
        )
        db.commit()
        return {
            "message": "Stock adjusted successfully",
            "new_balance": stock_record.current_stock_qty,
            "product_id": update_in.product_id
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise e


@router.post("/factories", status_code=status.HTTP_201_CREATED)
def create_factory(
        factory_in: FactoryCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("create_plant"))
):
    new_factory = FactoryMaster(
        name=factory_in.name,
        location="India",
        batch_number="N/A"
    )

    db.add(new_factory)
    db.commit()
    db.refresh(new_factory)

    return {"id": new_factory.id, "name": new_factory.name}


@router.get("/factories")
def get_all_factories(
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("view_inventory"))
):
    role_name = current_user.role.name if current_user.role else ""
    if role_name in ["SuperStockist", "Distributor", "Retailer"]:
        return []

    return db.query(FactoryMaster).all()