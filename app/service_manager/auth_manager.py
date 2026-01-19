from app.models import User, UserRole, RefreshToken
from app.schemas import SignupRequest, AuthResponse, LoginRequest, RefreshTokenRequest, TokenResponse, UpdateProfileRequest, UserContext, UpdatePasswordRequest
from app.utils import get_user_context, create_tokens, base36_encode, decode_frontend_password
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import select, update
from app.auth import hash_password, verify_password, decode_token
from datetime import datetime

class AuthManager:
    
    @classmethod
    async def signup(cls, request: SignupRequest, db: AsyncSession) -> AuthResponse:
        """Register a new user account"""
        result = await db.execute(
            select(User).filter(User.phone == request.phone)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Decode frontend-encoded password
        decoded_password = decode_frontend_password(request.password)
        print(f"!!!!!!!!!!!! {decoded_password}")
        x = hash_password(decoded_password)
        print(f"<<<<<<<<<<<<<<<<<< {x}")
        # Create new user
        user = User(
            phone=request.phone,
            email=request.email,
            hashed_password=hash_password(decoded_password),
            role=UserRole(request.role.value)
        )

        db.add(user)
        await db.flush()
        user.username = f"user_{base36_encode(user.id)}"
        await db.commit()
        await db.refresh(user)

        token = await create_tokens(user, db)
        return user, token
    
    @classmethod
    async def login(cls, request: LoginRequest, db: AsyncSession) -> AuthResponse:
        """Login with email and password"""
        
        if request.email:
            result = await db.execute(
                select(User).filter(User.email == request.email)
            )
        else:
            result = await db.execute(
                select(User).filter(User.phone == request.phone)
            )
        user = result.scalar_one_or_none()
        
        # Decode frontend-encoded password
        decoded_password = decode_frontend_password(request.password)
        
        if not user or not verify_password(decoded_password, user.hashed_password):
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
        return user, tokens
    
    @classmethod
    async def refresh_token(cls, request: RefreshTokenRequest, db: AsyncSession) -> TokenResponse:
        """Refresh access token using refresh token"""
        # Decode refresh token
        try:
            payload = decode_token(request.refresh_token)
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
            select(RefreshToken).filter(
                RefreshToken.token == request.refresh_token,
                RefreshToken.is_revoked == False
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
            select(User).filter(User.id == db_token.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        tokens = await create_tokens(user, db)
        
        return tokens
    
    @classmethod
    async def logout(cls, current_user: User, db: AsyncSession) -> dict:
        """Logout and revoke all refresh tokens"""
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == current_user.id,
                RefreshToken.is_revoked == False
            )
            .values(is_revoked=True)
        )
        await db.commit()
        
        return {"message": "Successfully logged out"}
    
    @classmethod
    async def update_profile(cls, request: UpdateProfileRequest, current_user: User, db: AsyncSession) -> UserContext:
        """Update user profile"""
        if request.email and request.email != current_user.email:
            result = await db.execute(
                select(User).filter(User.email == request.email)
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
    
    @classmethod
    async def change_password(cls, request: UpdatePasswordRequest, current_user: User, db: AsyncSession) -> dict:
        """Change user password"""
        # Decode frontend-encoded passwords
        decoded_current = decode_frontend_password(request.current_password)
        decoded_new = decode_frontend_password(request.new_password)
        
        if not verify_password(decoded_current, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        current_user.hashed_password = hash_password(decoded_new)
        
        # Revoke all refresh tokens for security
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == current_user.id)
            .values(is_revoked=True)
        )
        
        await db.commit()
        
        return {"message": "Password changed successfully"}