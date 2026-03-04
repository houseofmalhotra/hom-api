HOM Backend - Codebase Documentation
===================================

``This project follows a modular monolith architecture using FastAPI.

Root Level Files
``----------------

.env
- Stores environment variables (secrets & config).
- Example: DB_URL, JWT_SECRET.

requirements.txt
- List of Python dependencies.
- Used by pip: `pip install -r requirements.txt`.

alembic.ini
- Configuration for Alembic (database migrations).
- Used to version control DB schema.


Main Application
----------------

src/app/main.py
- Entry point of the application.
- Creates FastAPI app.
- Registers all API routes.


Core Layer (Infrastructure)
---------------------------

src/app/core/config.py
- Loads environment variables from .env.

src/app/core/database.py
- Creates database engine and session.
- Defines SQLAlchemy Base.

src/app/core/security.py
- JWT token generation.
- Password hashing and verification.


Models Layer (Database Tables)
------------------------------

src/app/models/
- Contains SQLAlchemy ORM models.
- Each file represents one business domain.

Files:
    - user.py → USERS, ROLES, PERMISSIONS tables
    - geography.py → ZONE, STATE, REGION, AREA, TERRITORY
    - product.py → PRODUCT_MASTER
    - production.py → FACTORY, DAILY_PRODUCTION_LOG
    - inventory.py → INVENTORY + STOCK_LEDGER
    - sales_primary.py → PRIMARY_ORDER
    - sales_secondary.py → SECONDARY_ORDER
    - sales_tertiary.py → TERTIARY_ORDER


Schemas Layer (API Contracts)
-----------------------------

src/app/schemas/
- Pydantic models for request/response validation.
- Defines what client sends and receives.

Files:
- user.py → User input/output
- geography.py → Geography APIs
- product.py → Product APIs
- inventory.py → Stock APIs
- orders.py → Order APIs


CRUD Layer (Database Operations)
--------------------------------

src/app/crud/
- All direct database queries live here.
- No business logic, only SQL operations.

Files:
- user.py → User queries
- geography.py → Geo queries
- inventory.py → Stock queries
- primary_sales.py → Primary sales DB ops
- secondary_sales.py → Secondary sales DB ops
- tertiary_sales.py → Tertiary sales DB ops


Services Layer (Business Logic)
-------------------------------

src/app/services/
- Core business rules and workflows.

Files:
- stock_service.py → Stock movement + ledger
- order_service.py → Order processing logic
- permission_service.py → Role & permission checks


API Layer (HTTP Endpoints)
--------------------------

src/app/api/
- FastAPI routes (controllers).
- Calls services and returns responses.

Files:
- auth.py → Login & JWT
- users.py → User APIs
- geography.py → Geo APIs
- product.py → Product APIs
- production.py → Factory APIs
- inventory.py → Stock APIs
- primary_sales.py → Primary sales APIs
- secondary_sales.py → Secondary sales APIs
- tertiary_sales.py → Tertiary sales APIs


Migrations
----------

src/app/migrations/
- Alembic auto-generated migration files.
- Used to update DB schema safely.


Tests
-----

tests/
- Automated test cases.

Files:
- test_auth.py → Auth tests
- test_inventory.py → Stock tests
- test_orders.py → Order tests


Architecture Rule
-----------------

API → Services → CRUD → Models → Database

Never skip layers.
Never mix business logic with SQL.
