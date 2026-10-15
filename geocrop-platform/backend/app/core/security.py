"""Password hashing and JWT auth. Behind small functions so an identity provider can replace it later."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user_id: UUID) -> str:
    s = get_settings()
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours=s.jwt_expiry_hours)}
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        s = get_settings()
        if s.auth_required:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")
        guest = db.scalar(select(User).where(User.username == s.guest_username))
        if guest is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                                "Guest account not found. Run `make seed` to create it.")
        return guest
    try:
        payload = jwt.decode(creds.credentials, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Sign in again.")
    user = db.get(User, UUID(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found.")
    return user


def internal_only(x_internal_token: str | None = Header(default=None)) -> None:
    """Guard for service-to-service routes (tile service asking for layer details)."""
    if x_internal_token != get_settings().internal_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Internal route.")
