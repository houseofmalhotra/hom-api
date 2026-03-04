from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.app.core.database import get_db
from src.app.services.auth_services import AuthService
from src.app.core.security import create_access_token

router = APIRouter()


@router.post("/login")
def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated or suspended.",
        )

    access_token = create_access_token(subject=user.username)

    permissions = []
    role_name = "Unknown"
    if user.role:
        role_name = user.role.name
        if user.role.permissions:
            permissions = [p.name for p in user.role.permissions]

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": role_name,
            "permissions": permissions
        }
    }