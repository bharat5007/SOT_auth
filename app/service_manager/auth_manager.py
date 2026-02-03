from app.models import User, UserRole, RefreshToken
from app.schemas import (
    SignupRequest,
    AuthResponse,
    LoginRequest,
    RefreshTokenRequest,
    UserContext,
    AddVendorRoleRequest,
)
from app.utils import (
    get_user_context,
    create_tokens,
    decode_frontend_password,
    is_email,
)
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import select, update
from app.auth import hash_password, verify_password, decode_token
from datetime import datetime, timezone


class AuthManager:
    @classmethod
    async def signup(cls, request: SignupRequest, db: AsyncSession) -> AuthResponse:
        try:
            """Register a new user account"""
            result = await db.execute(select(User).filter(User.phone == request.phone))
            existing_user = result.scalar_one_or_none()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

            # Decode frontend-encoded password
            decoded_password = decode_frontend_password(request.password)

            # During signup, default to user role only, ignore any roles in request
            roles_to_assign = [UserRole.USER.value]

            # Create new user
            user = User(
                name=request.name,
                phone=request.phone,
                email=request.email,
                hashed_password=hash_password(decoded_password),
                roles=roles_to_assign,
            )

            db.add(user)
            await db.flush()
            await db.commit()
            await db.refresh(user)

            token = await create_tokens(user, db)
            return user, token
        except Exception as e:
            raise Exception(str(e))

    @classmethod
    async def login(cls, request: LoginRequest, db: AsyncSession) -> AuthResponse:
        """Login with email and password"""
        if is_email(request.identifier):
            result = await db.execute(
                select(User).filter(User.email == request.identifier)
            )
        else:
            result = await db.execute(
                select(User).filter(User.phone == request.identifier)
            )
        user = result.scalar_one_or_none()

        # Decode frontend-encoded password
        decoded_password = decode_frontend_password(request.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="No user found"
            )

        if not verify_password(decoded_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
            )

        tokens = await create_tokens(user, db)
        return user, tokens

    @classmethod
    async def refresh_token(
        cls, request: RefreshTokenRequest, db: AsyncSession
    ) -> AuthResponse:
        """Refresh access token using refresh token"""
        # Decode refresh token
        try:
            payload = decode_token(request.refresh_token)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        # Check if token exists and is not revoked
        result = await db.execute(
            select(RefreshToken).filter(
                RefreshToken.token == request.refresh_token,
                not RefreshToken.is_revoked,
            )
        )
        db_token = result.scalar_one_or_none()

        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or revoked",
            )

        if db_token.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
            )

        # Revoke old refresh token (token rotation)
        db_token.is_revoked = True

        # Get user and create new tokens
        user_result = await db.execute(select(User).filter(User.id == db_token.user_id))
        user = user_result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        tokens = await create_tokens(user, db)

        # Return same format as login: (user, tokens)
        return user, tokens

    @classmethod
    async def logout(cls, current_user: User, db: AsyncSession) -> dict:
        """Logout and revoke all refresh tokens"""
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == current_user.id,
                not RefreshToken.is_revoked,
            )
            .values(is_revoked=True)
        )
        await db.commit()

        return {"message": "Successfully logged out"}

    @classmethod
    async def add_vendor_role(
        cls, request: AddVendorRoleRequest, db: AsyncSession
    ) -> UserContext:
        """
        Add VENDOR role to a user identified by phone number.
        This is typically used to upgrade regular users to vendors.
        """
        # Find user by phone number
        result = await db.execute(select(User).filter(User.phone == request.phone))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with phone number {request.phone} not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add vendor role to inactive user",
            )

        # Convert current roles to list of string values
        current_roles = []
        if user.roles:
            for role in user.roles:
                if hasattr(role, "value"):
                    current_roles.append(role.value)
                else:
                    current_roles.append(str(role))

        # Check if user already has vendor role
        if UserRole.VENDOR.value in current_roles:
            get_user_context(user)

        # Add vendor role to the list
        current_roles.append(UserRole.VENDOR.value)

        # Update user roles
        user.roles = current_roles

        await db.commit()
        await db.refresh(user)

        return get_user_context(user)
