"""
Authentication Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
import json

from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


async def create_tokens(user: models.User, db: AsyncSession) -> schemas.TokenResponse:
    """Create access and refresh tokens for a user"""
    # Create access token
    access_token = auth.create_access_token(data={"sub": str(user.id)})
    
    # Create refresh token
    refresh_token, expires_at = auth.create_refresh_token(data={"sub": str(user.id)})
    
    # Store refresh token in database
    db_refresh_token = models.RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    await db.commit()
    
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


def get_user_context(user: models.User) -> schemas.UserContext:
    """Get user context"""
    return schemas.UserContext(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.post("/login", response_model=schemas.AuthResponse)
async def login(request: schemas.LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password"""
    result = await db.execute(
        select(models.User).filter(models.User.email == request.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not auth.verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    tokens = await create_tokens(user, db)
    user_context = get_user_context(user)
    
    return schemas.AuthResponse(user=user_context, tokens=tokens)


@router.post("/signup", response_model=schemas.AuthResponse)
async def signup(request: schemas.SignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account"""
    # Check if email already exists
    result = await db.execute(
        select(models.User).filter(models.User.email == request.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = models.User(
        email=request.email,
        username=request.username,
        hashed_password=auth.hash_password(request.password),
        role=models.UserRole(request.role.value)
    )
    db.add(user)
    await db.flush()
    
    # Create initial role entry
    role = models.Role(
        user_id=user.id,
        role=user.role
    )
    db.add(role)
    
    await db.commit()
    await db.refresh(user)
    
    tokens = await create_tokens(user, db)
    user_context = get_user_context(user)
    
    return schemas.AuthResponse(user=user_context, tokens=tokens)


@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh_token(request: schemas.RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token"""
    # Decode refresh token
    try:
        payload = auth.decode_token(request.refresh_token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    # Check if token exists and is not revoked
    result = await db.execute(
        select(models.RefreshToken).filter(
            models.RefreshToken.token == request.refresh_token,
            models.RefreshToken.is_revoked == False
        )
    )
    db_token = result.scalar_one_or_none()
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked"
        )
    
    if db_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )
    
    # Revoke old refresh token (token rotation)
    db_token.is_revoked = True
    
    # Get user and create new tokens
    user_result = await db.execute(
        select(models.User).filter(models.User.id == db_token.user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    tokens = await create_tokens(user, db)
    
    return tokens


@router.get("/me", response_model=schemas.UserContext)
async def get_user_context_route(current_user: models.User = Depends(auth.get_current_user)):
    """Get current user context"""
    return get_user_context(current_user)


@router.post("/logout")
async def logout(
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout and revoke all refresh tokens"""
    await db.execute(
        update(models.RefreshToken)
        .where(
            models.RefreshToken.user_id == current_user.id,
            models.RefreshToken.is_revoked == False
        )
        .values(is_revoked=True)
    )
    await db.commit()
    
    return {"message": "Successfully logged out"}


@router.patch("/profile", response_model=schemas.UserContext)
async def update_profile(
    request: schemas.UpdateProfileRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile"""
    if request.email and request.email != current_user.email:
        result = await db.execute(
            select(models.User).filter(models.User.email == request.email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = request.email
    
    if request.username:
        current_user.username = request.username
    
    await db.commit()
    await db.refresh(current_user)
    
    return get_user_context(current_user)


@router.post("/change-password")
async def change_password(
    request: schemas.UpdatePasswordRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    if not auth.verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    current_user.hashed_password = auth.hash_password(request.new_password)
    
    # Revoke all refresh tokens for security
    await db.execute(
        update(models.RefreshToken)
        .where(models.RefreshToken.user_id == current_user.id)
        .values(is_revoked=True)
    )
    
    await db.commit()
    
    return {"message": "Password changed successfully"}
