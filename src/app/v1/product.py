from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.app.models.product import ProductMaster
from src.app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from src.app.core.database import get_db
from src.app.core.security import check_permissions
from src.app.models.user import User

router = APIRouter()


@router.post("/", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(ProductMaster).filter(ProductMaster.sku_code == product.sku_code).first()
    if db_product:
        raise HTTPException(status_code=400, detail="SKU already exists")

    # =================================================================
    # 🧠 SMART PACKAGING LOGIC ENGINE
    # =================================================================
    if product.item_type == "FG":
        # 1. Auto-Calculate Tucks based on Blade parameters
        if product.blades_per_box and product.blades_per_tuck:
            product.tucks_per_box = int(product.blades_per_box / product.blades_per_tuck)
            product.units_per_case = product.tucks_per_box  # Sync with legacy logistics

        # 2. Auto-Detect "Saloon" vs "Standard" packaging
        if product.blades_per_box == 12000:
            product.box_type = "Saloon Pack"
        elif product.blades_per_box == 10000:
            product.box_type = "Standard Pack"
    # =================================================================

    new_product = ProductMaster(**product.dict())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@router.get("/", response_model=list[ProductResponse])
def get_all_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permissions("view_products"))
):
    return db.query(ProductMaster).all()


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_update: ProductUpdate, db: Session = Depends(get_db)):
    db_product = db.query(ProductMaster).filter(ProductMaster.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_update.dict(exclude_unset=True)

    # =================================================================
    # 🧠 SMART PACKAGING LOGIC ENGINE (During Updates)
    # =================================================================
    if update_data.get("item_type", db_product.item_type) == "FG":
        blades_box = update_data.get("blades_per_box", db_product.blades_per_box)
        blades_tuck = update_data.get("blades_per_tuck", db_product.blades_per_tuck)

        if blades_box and blades_tuck:
            update_data["tucks_per_box"] = int(blades_box / blades_tuck)
            update_data["units_per_case"] = update_data["tucks_per_box"]

        if blades_box == 12000:
            update_data["box_type"] = "Saloon Pack"
        elif blades_box == 10000:
            update_data["box_type"] = "Standard Pack"
    # =================================================================

    for key, value in update_data.items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permissions("manage_products"))
):
    """Soft delete a product by setting is_active to False"""
    db_product = db.query(ProductMaster).filter(ProductMaster.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db_product.is_active = False
    db.commit()
    return None
