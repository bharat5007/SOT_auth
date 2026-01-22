from app.models import User
from app.schemas import UserContext
from app.models import User, UserRole, RefreshToken
from app.schemas import TokenResponse
from app.auth import create_access_token, create_refresh_token, settings
from sqlalchemy.ext.asyncio import AsyncSession
import string
from datetime import datetime, timedelta, timezone
import jwt
import base64


def decode_frontend_password(encoded_password: str) -> str:
    """
    Decode password encoded by frontend.
    
    Frontend encoding format: base64(password):timestamp_base36
    Example: "bWtrcDc2cHQ6MTIzNDU2" -> "mkkp76pt:123456"
    
    This function extracts the actual password from the encoded payload.
    """
    try:
        # Decode from base64
        decoded_bytes = base64.b64decode(encoded_password)
        decoded_str = decoded_bytes.decode('utf-8')
        
        # Split by delimiter ':'
        if ':' in decoded_str:
            _, password = decoded_str.split(':', 1)
            return password
        else:
            # If no delimiter, treat entire string as password
            return decoded_str
    except Exception as e:
        # If decoding fails, return original (for backward compatibility)
        return encoded_password


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
    

def base36_encode(number: int) -> str:
    ALPHABET = string.digits + string.ascii_lowercase
    if number < 0:
        raise ValueError("Number must be non-negative")

    if number == 0:
        return "0"

    base36 = []
    while number:
        number, rem = divmod(number, 36)
        base36.append(ALPHABET[rem])

    return ''.join(reversed(base36))


def generate_shared_context(user: User) -> str:
    """
    Generate a signed shared context token for internal microservices.

    This token is:
    - Short-lived
    - Tamper-proof
    - Meant ONLY for service-to-service communication
    """

    now = datetime.now(timezone.utc)

    payload = {
        "uid": user.id,
        "email": user.email,
        "phone": user.phone,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=settings.SHARED_CONTEXT_EXPIRE_MINUTES)).timestamp()
        ),
        "iss": "sot-auth",
        "typ": "shared-context"
    }

    token = jwt.encode(
        payload,
        settings.SHARED_CONTEXT_SECRET,
        algorithm="HS256"
    )

    return token