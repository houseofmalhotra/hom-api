from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from src.app.v1 import (
    auth,
    users,
    inventory,
    primary_sales,
    secondary_sales,
    tertiary_sales,
    geography,
    product,
)
from src.app.core.config import settings
from src.app.v1 import partner
from src.app.v1 import finance

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Backend system for House of Malhotra"
)



def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/api/v1/auth/login",
                    "scopes": {}
                }
            }
        }
    }

    openapi_schema["security"] = [{"OAuth2PasswordBearer": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, prefix="/api/v1/auth", tags=["01. Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["02. User Management"])
app.include_router(geography.router, prefix="/api/v1/geo", tags=["03. Geography"])
app.include_router(product.router, prefix="/api/v1/products",  tags=["04. Products"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["05. Stock Management"])
app.include_router(primary_sales.router, prefix="/api/v1/primary-orders", tags=["06. Primary Sales (Factory -> SS)"])
app.include_router(secondary_sales.router, prefix="/api/v1/secondary-sales",tags=["07. Secondary Sales (DB -> Retailer)"])
app.include_router(tertiary_sales.router, prefix="/api/v1/tertiary-sales",tags=["08. Tertiary Sales (Retailer -> Barber)"])
app.include_router(partner.router, prefix="/api/v1/partners", tags=["9. Partners"])
app.include_router(finance.router, prefix="/api/v1/finance", tags=["10. Finance & A/R"])


@app.get("/", tags=["Health Check"])
def root():
    return {
        "status": "online",
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.app.main:app", host="127.0.0.1", port=8000, reload=True)