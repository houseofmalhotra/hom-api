from sqlalchemy.orm import Session
from src.app.core.database import engine, Base, SessionLocal
from src.app.core.security import get_password_hash

# CRITICAL: We MUST import every single model file here so SQLAlchemy
# registers all the new "Fat Table" columns before calling create_all().
import src.app.models.user
import src.app.models.partner
import src.app.models.product
import src.app.models.geography
import src.app.models.inventory
import src.app.models.sales_primary
import src.app.models.sales_secondary
import src.app.models.sales_tertiary
import src.app.models.finance
import src.app.models.logistics
import src.app.models.pricing

from src.app.models.user import User, Role, Permission

MASTER_PERMISSIONS = [
    {"name": "view_dashboard", "description": "Can access the main dashboard"},
    {"name": "view_sales_reports", "description": "Access to aggregated data"},
    {"name": "export_data", "description": "Allow downloading CSV/Excel dumps"},

    {"name": "view_all_orders", "description": "Admin/ZSM can see cross-geo orders"},
    {"name": "view_own_orders", "description": "Scoped to the user's assigned geography/entity"},
    {"name": "create_primary_order", "description": "Factory to SS/Distributor"},
    {"name": "create_secondary_order", "description": "SS/Distributor to Retailer"},
    {"name": "create_tertiary_order", "description": "Retailer to Consumer"},
    {"name": "update_order", "description": "Modify items before dispatch"},
    {"name": "cancel_order", "description": "Cancel a pending order"},
    {"name": "approve_order", "description": "For SOs to approve tertiary orders"},

    {"name": "dispatch_order", "description": "Generate shipment tracking and deduct physical stock"},
    {"name": "receive_order", "description": "Mark in-transit stock as arrived"},
    {"name": "manage_logistics", "description": "Update LR numbers, driver details"},

    {"name": "view_inventory", "description": "Check stock ledgers"},
    {"name": "manage_inventory", "description": "Manual stock adjustments, audits, or adding opening stock"},
    {"name": "create_plant", "description": "Register new manufacturing plants/factories"},

    {"name": "view_invoices", "description": "See generated tax invoices"},
    {"name": "manage_payments", "description": "Record offline payments or reconcile ledgers"},
    {"name": "manage_credit_limits", "description": "Set limits for Distributors/SS"},
    {"name": "view_ledgers", "description": "Check outstanding balances"},

    {"name": "view_products", "description": "Browse catalog and prices"},
    {"name": "manage_products", "description": "Add new SKUs, change HSN codes or base prices"},
    {"name": "manage_batches", "description": "Create manufacturing batches and expiry dates"},
    {"name": "manage_schemes", "description": "Create trade promotions"},

    {"name": "view_partners", "description": "See the directory of Retailers/Distributors"},
    {"name": "manage_partners", "description": "Onboard or deactivate entities"},
    {"name": "view_geography", "description": "See Zone/Region/Area/Territory mapping"},
    {"name": "manage_geography", "description": "Create or reassign territories"},
    {"name": "view_users", "description": "See employee list"},
    {"name": "manage_users", "description": "Create user accounts, reset passwords"},
    {"name": "manage_roles", "description": "Create roles and attach permissions"}
]


def seed_permissions(db: Session):
    print("🔑 Seeding master permissions...")
    for perm_data in MASTER_PERMISSIONS:
        new_perm = Permission(name=perm_data["name"], description=perm_data["description"])
        db.add(new_perm)
    db.commit()
    print(f"✅ Successfully seeded {len(MASTER_PERMISSIONS)} permissions.")


def reset_and_seed_database():
    print("🧨 WARNING: Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)

    print("🏗️ Recreating clean tables from latest schema...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Step 1: Seed all permissions
        seed_permissions(db)

        # Step 2: Grab all newly created permissions from the DB
        all_permissions_in_db = db.query(Permission).all()

        print("🌱 Seeding default Admin role and user...")
        # Step 3: Create the Admin role and attach ALL permissions to it instantly
        admin_role = Role(
            name="Admin",
            description="Super Administrator with full access",
            permissions=all_permissions_in_db
        )
        db.add(admin_role)
        db.flush()

        # Step 4: Create the default Admin user
        admin_user = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            is_active=True,
            role_id=admin_role.id
        )
        db.add(admin_user)
        db.commit()

        print("✅ Database reset complete!")
        print("🔐 You can now log into the frontend with:")
        print("   Username: admin")
        print("   Password: admin123")

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    confirm = input("This will DESTROY ALL DATA in the database. Are you sure? (type 'yes'): ")
    if confirm.lower() == 'yes':
        reset_and_seed_database()
    else:
        print("Aborted.")