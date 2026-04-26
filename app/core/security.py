from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings

# bcrypt is the industry standard for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FastAPI reads the Bearer token from the Authorization header automatically
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """
    Sign a JWT containing whatever dict you pass in.
    We include user_id, tenant_id, and role so every request
    carries full context without a DB lookup.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI dependency — extracts and validates the JWT from the request.
    Use with: current_user: dict = Depends(get_current_user)
    Returns the decoded payload: {user_id, tenant_id, role}
    """
    return decode_token(token)


def require_role(required_roles: list):
    """
    Factory that returns a FastAPI dependency enforcing role-based access.

    Usage:
        @router.post("/admin-action")
        def action(current_user = Depends(require_role(["admin"]))):
            ...

    How it works:
        1. get_current_user extracts and validates the JWT
        2. We then check if the user's role is in the allowed list
        3. If not — 403 Forbidden
    """
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Allowed roles: {required_roles}. Your role: {current_user.get('role')}",
            )
        return current_user

    return role_checker
