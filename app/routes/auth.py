"""
Authentication Routes
"""

from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .. import models, schemas, auth
from app.schemas import (
    SignupRequest,
    LoginRequest,
    RefreshTokenRequest,
    AddVendorRoleRequest,
)
from app.service_manager.auth_manager import AuthManager
from app.utils import get_user_context, generate_shared_context

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/signup")
async def signup(
    response: Response, request: SignupRequest, db: AsyncSession = Depends(get_db)
):
    """Register a new user account"""
    try:
        user, token = await AuthManager.signup(request, db)
        user_context = get_user_context(user)
        shared_context = generate_shared_context(user)
        response.headers["X-Shared-Context"] = shared_context
        return {
            "message": "Signup Successful",
            "user": user_context,
            "tokens": token,
            "shared_context": shared_context,
        }
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": f"Signup failed {str(e)}"}


@router.post("/login")
async def login(
    response: Response, request: LoginRequest, db: AsyncSession = Depends(get_db)
):
    """Login with email and password"""
    try:
        user, token = await AuthManager.login(request, db)
        user_context = get_user_context(user)
        shared_context = generate_shared_context(user)
        return {"user": user_context, "tokens": token, "shared_context": shared_context}
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": f"Login failed {str(e)}"}


@router.post("/logout")
async def logout(
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout and revoke all refresh tokens"""
    response = await AuthManager.logout(current_user, db)
    return response


@router.post("/refresh")
async def refresh_token(
    response: Response, request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        user, tokens = await AuthManager.refresh_token(request, db)
        user_context = get_user_context(user)
        shared_context = generate_shared_context(user)
        return {
            "user": user_context,
            "tokens": tokens,
            "shared_context": shared_context,
        }
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": f"Token refresh failed: {str(e)}"}


@router.get("/me", response_model=schemas.UserContext)
async def get_user_context_route(
    current_user: models.User = Depends(auth.get_current_user),
):
    """Get current user context"""
    return get_user_context(current_user)


@router.post("/add-vendor-role")
async def add_vendor_role(
    request: AddVendorRoleRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(auth.verify_auth_service),
):
    response = await AuthManager.add_vendor_role(request, db)
    return response
