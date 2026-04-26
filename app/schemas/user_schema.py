from pydantic import BaseModel


class UserResponse(BaseModel):
    """
    What we return to the client after registration.
    We deliberately exclude hashed_password — never expose it.
    """
    id: int
    username: str
    role: str
    tenant_id: str

    model_config = {"from_attributes": True}
