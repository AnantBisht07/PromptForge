from fastapi import APIRouter, Depends
from app.core.security import get_current_user, require_role

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """
    Returns the identity of the currently logged-in user.
    No DB query needed — everything is in the JWT payload.
    """
    return {
        "user_id": current_user.get("user_id"),
        "tenant_id": current_user.get("tenant_id"),
        "role": current_user.get("role"),
    }


@router.get("/admin-only")
def admin_panel(current_user: dict = Depends(require_role(["admin"]))):
    """
    Example of a route locked to admins only.
    Developers and reviewers get a 403 here.

    require_role(["admin"]) is a dependency factory:
        1. It first calls get_current_user to validate the JWT
        2. Then checks the role field in the payload
        3. Raises 403 if the role isn't in the allowed list
    """
    return {
        "message": "Welcome to the admin panel",
        "user": current_user,
    }


@router.get("/reviewer-or-admin")
def review_dashboard(
    current_user: dict = Depends(require_role(["admin", "reviewer"]))
):
    """
    Example of a route accessible by multiple roles.
    Developers cannot access this.
    """
    return {
        "message": "Review dashboard — approve or reject prompts here",
        "user": current_user,
    }
