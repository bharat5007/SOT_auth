from app.models import User
from app.schemas import UserContext
from app.models import User, UserRole, RefreshToken
from app.schemas import TokenResponse
from app.auth import create_access_token, create_refresh_token, settings
from sqlalchemy.ext.asyncio import AsyncSession

def get_user_context(user: User) -> UserContext:
    """Get user context"""
    return UserContext(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )
    
async def create_tokens(user: User, db: AsyncSession) -> TokenResponse:
    """Create access and refresh tokens for a user"""
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Create refresh token
    refresh_token, expires_at = create_refresh_token(data={"sub": str(user.id)})
    
    # Store refresh token in database
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )