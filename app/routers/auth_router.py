from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.db.database import get_session
from app.schemas.auth_schema import RegisterRequest, LoginRequest, TokenResponse
from app.schemas.user_schema import UserResponse
from app.services.auth_service import register_user, login_user
from app.services.workspace_service import get_current_workspace

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(request: RegisterRequest, session: Session = Depends(get_session)):
    """
    Create a new user account.

    - Assigns a unique tenant_id automatically
    - Hashes the password before storage
    - Returns user info (no password in response)
    """
    user = register_user(request, session)
    workspace = get_current_workspace({"user_id": user.id}, session)
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "workspace_id": workspace.id,
    }


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, session: Session = Depends(get_session)):
    """
    Authenticate and receive a JWT.

    The token encodes: user_id, tenant_id, role
    Pass it in subsequent requests as:
        Authorization: Bearer <token>
    """
    token = login_user(request, session)
    return TokenResponse(access_token=token)
