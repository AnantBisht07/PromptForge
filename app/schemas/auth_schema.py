from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "developer"

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v):
        allowed = {"admin", "developer", "reviewer", "analyst"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {allowed}")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    """
    Returned after a successful login.
    The client must store access_token and send it in the
    Authorization: Bearer <token> header on subsequent requests.
    """
    access_token: str
    token_type: str = "bearer"
