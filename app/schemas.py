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
    email: EmailStr
    password: str = Field(min_length=6)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    username: str = Field(min_length=3, max_length=100)
    role: UserRole = UserRole.USER


class VendorDetails(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    phone1: str = Field(min_length=10, max_length=20)
    phone2: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=500)
    service_type: str
    city: str
    district: str
    lower_range: float = Field(ge=0)
    upper_range: float = Field(ge=0)
    meta: Optional[dict] = None

    @field_validator('upper_range')
    @classmethod
    def validate_price_range(cls, v, info):
        if 'lower_range' in info.data and v < info.data['lower_range']:
            raise ValueError('upper_range must be >= lower_range')
        return v


class VendorSignupRequest(SignupRequest):
    role: UserRole = UserRole.VENDOR
    vendor_details: Optional[VendorDetails] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ============== Response Schemas ==============

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserContext(BaseModel):
    id: int
    email: str
    username: str
    role: UserRole
    vendor_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserContext
    tokens: TokenResponse


class VendorResponse(BaseModel):
    id: int
    name: str
    phone1: str
    phone2: Optional[str] = None
    email: Optional[str] = None
    service_type: str
    city: str
    district: str
    lower_range: float
    upper_range: float
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Update Schemas ==============

class UpdateProfileRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


# ============== Error Schemas ==============

class ErrorResponse(BaseModel):
    detail: str
    status_code: int = 400
