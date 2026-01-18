"""
Authentication Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import json

from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def create_tokens(user: models.User, db: Session) -> schemas.TokenResponse:
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
    db.commit()
    
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


def get_user_context(user: models.User) -> schemas.UserContext:
    """Get user context with vendor_id if applicable"""
    vendor_id = None
    if user.role.value == "vendor" and user.vendor:
        vendor_id = user.vendor.id
    
    return schemas.UserContext(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role.value,
        vendor_id=vendor_id,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.post("/login", response_model=schemas.AuthResponse)
def login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password"""
    user = db.query(models.User).filter(models.User.email == request.email).first()
    
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
    
    tokens = create_tokens(user, db)
    user_context = get_user_context(user)
    
    return schemas.AuthResponse(user=user_context, tokens=tokens)


@router.post("/signup", response_model=schemas.AuthResponse)
def signup(request: schemas.SignupRequest, db: Session = Depends(get_db)):
    """Register a new user account"""
    # Check if email already exists
    if db.query(models.User).filter(models.User.email == request.email).first():
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
    db.commit()
    db.refresh(user)
    
    tokens = create_tokens(user, db)
    user_context = get_user_context(user)
    
    return schemas.AuthResponse(user=user_context, tokens=tokens)


@router.post("/vendor/signup", response_model=schemas.AuthResponse)
def vendor_signup(request: schemas.VendorSignupRequest, db: Session = Depends(get_db)):
    """Register a new vendor account with business details"""
    # Check if email already exists
    if db.query(models.User).filter(models.User.email == request.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user with vendor role
    user = models.User(
        email=request.email,
        username=request.username,
        hashed_password=auth.hash_password(request.password),
        role=models.UserRole.VENDOR
    )
    db.add(user)
    db.flush()  # Get user.id without committing
    
    # Create vendor record if details provided
    if request.vendor_details:
        vd = request.vendor_details
        vendor = models.Vendor(
            user_id=user.id,
            name=vd.name,
            phone1=vd.phone1,
            phone2=vd.phone2,
            email=vd.email,
            address=vd.address,
            service_type=vd.service_type,
            city=vd.city,
            district=vd.district,
            lower_range=vd.lower_range,
            upper_range=vd.upper_range
        )
        db.add(vendor)
        db.flush()
        
        # Create vendor meta if provided
        if vd.meta:
            meta = models.VendorMeta(
                vendor_id=vendor.id,
                about=vd.meta.get("about"),
                services_offered=json.dumps(vd.meta.get("service_offered", [])),
                experience=vd.meta.get("highlights", {}).get("experience"),
                events_done=vd.meta.get("highlights", {}).get("events_done")
            )
            db.add(meta)
    
    db.commit()
    db.refresh(user)
    
    tokens = create_tokens(user, db)
    user_context = get_user_context(user)
    
    return schemas.AuthResponse(user=user_context, tokens=tokens)


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(request: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
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
    db_token = db.query(models.RefreshToken).filter(
        models.RefreshToken.token == request.refresh_token,
        models.RefreshToken.is_revoked == False
    ).first()
    
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
    user = db.query(models.User).filter(models.User.id == db_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    tokens = create_tokens(user, db)
    
    return tokens


@router.get("/me", response_model=schemas.UserContext)
def get_user_context_route(current_user: models.User = Depends(auth.get_current_user)):
    """Get current user context"""
    return get_user_context(current_user)


@router.post("/logout")
def logout(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Logout and revoke all refresh tokens"""
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == current_user.id,
        models.RefreshToken.is_revoked == False
    ).update({"is_revoked": True})
    db.commit()
    
    return {"message": "Successfully logged out"}


@router.patch("/profile", response_model=schemas.UserContext)
def update_profile(
    request: schemas.UpdateProfileRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    if request.email and request.email != current_user.email:
        if db.query(models.User).filter(models.User.email == request.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = request.email
    
    if request.username:
        current_user.username = request.username
    
    db.commit()
    db.refresh(current_user)
    
    return get_user_context(current_user)


@router.post("/change-password")
def change_password(
    request: schemas.UpdatePasswordRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    if not auth.verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    current_user.hashed_password = auth.hash_password(request.new_password)
    
    # Revoke all refresh tokens for security
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == current_user.id
    ).update({"is_revoked": True})
    
    db.commit()
    
    return {"message": "Password changed successfully"}
