"""
Authentication Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .. import models, schemas, auth
from app.schemas import SignupRequest, LoginRequest, RefreshTokenRequest, UpdateProfileRequest, UpdatePasswordRequest
from app.service_manager.auth_manager import AuthManager
from app.utils import get_user_context

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/signup")
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account"""
    response = await AuthManager.signup(request, db)
    return response


@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password"""
    response = await AuthManager.login(request, db)
    return response


@router.post("/logout")
async def logout(
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout and revoke all refresh tokens"""
    response = await AuthManager.logout(current_user, db)
    return response


@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token"""
    response = await AuthManager.refresh_token(request, db)
    return response


@router.get("/me", response_model=schemas.UserContext)
async def get_user_context_route(current_user: models.User = Depends(auth.get_current_user)):
    """Get current user context"""
    return get_user_context(current_user)



@router.patch("/profile", response_model=schemas.UserContext)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile"""
    response = await AuthManager.update_profile(request, current_user, db)
    return response


@router.post("/change-password")
async def change_password(
    request: UpdatePasswordRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    response = await AuthManager.change_password(request, current_user, db)
    return response
