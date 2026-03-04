from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.app.core.security import verify_password, create_access_token
from src.app.models.user import User

class AuthService:
    @staticmethod
    def authenticate_user(db: Session, login_id: str, password: str):
        user = db.query(User).filter(
            or_(User.username == login_id, User.email == login_id)
        ).first()

        if not user or not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def generate_token(user_username: str):
        return create_access_token(subject=user_username)