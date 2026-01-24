"""
Pydantic Schemas for Request/Response Validation
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    VENDOR = "vendor"
    ADMIN = "admin"


# ============== Auth Schemas ==============

class LoginRequest(BaseModel):
    identifier: str
    password: str


class SignupRequest(BaseModel):
    name: str
    phone: str
    email: Optional[EmailStr] = None
    password: str = Field(min_length=6)
    roles: List[UserRole] = Field(default_factory=lambda: [UserRole.USER])


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ============== Role Schemas ==============

class RoleBase(BaseModel):
    roles: List[UserRole]
    is_active: bool = True


class RoleResponse(RoleBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============== Response Schemas ==============

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserContext(BaseModel):
    id: int
    email: str
    roles: List[UserRole]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserContext
    tokens: TokenResponse


# ============== Update Schemas ==============

class UpdateProfileRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class AddVendorRoleRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20, description="Phone number of the user to upgrade to vendor")


# ============== Error Schemas ==============

class ErrorResponse(BaseModel):
    detail: str
    status_code: int = 400
