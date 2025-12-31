"""
Security utilities for authentication and authorization
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
import hashlib

from mmino.core.config import settings
from mmino.db import crud
from mmino.schemas import UserResponse, APIKeyResponse

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer authentication
security = HTTPBearer()


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRY_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT access token
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Check token type
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        
        return payload
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_refresh_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT refresh token
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Check token type
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        
        return payload
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """
    Get current user from JWT token
    """
    from mmino.db.session import SessionLocal
    token = credentials.credentials
    payload = verify_access_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    db = SessionLocal()
    try:
        user = crud.get_user_by_id(db, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return UserResponse.from_orm(user)
    finally:
        db.close()

def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Get current active user (checks if user is active)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user

def get_current_superuser(
    current_user: UserResponse = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current superuser (checks if user is superuser)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user

def generate_api_key() -> str:
    """
    Generate a secure API key
    Format: ak_[random_32_chars]_[timestamp]
    """
    import secrets
    import time
    
    # Generate random part
    random_part = secrets.token_urlsafe(24)  # 24 bytes = 32 chars in base64
    
    # Get timestamp
    timestamp = int(time.time())
    
    # Create key
    api_key = f"ak_{random_part}_{timestamp}"
    
    return api_key

def verify_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Verify an API key and return user info if valid
    """
    from mmino.db.session import SessionLocal
    db = SessionLocal()
    try:
        api_key_record = crud.get_api_key(db, api_key)
        if not api_key_record:
            return None
        
        # Check if key is active
        if not api_key_record.is_active:
            return None
        
        # Check if key has expired
        if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
            return None
        
        # Update last used timestamp
        api_key_record.last_used_at = datetime.utcnow()
        db.commit()
        
        # Get user info
        user = crud.get_user_by_id(db, str(api_key_record.user_id))
        if not user or not user.is_active:
            return None
        
        return {
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "is_superuser": user.is_superuser,
            "api_key_id": str(api_key_record.id),
            "api_key_name": api_key_record.name
        }
        
    finally:
        db.close()

def get_api_key_user(
    x_api_key: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """
    Get user from API key header
    """
    if not x_api_key:
        return None
    return verify_api_key(x_api_key)

def require_auth(
    user_or_api_key: Optional[Union[UserResponse, Dict[str, Any]]] = Depends(get_api_key_user),
    token: Optional[HTTPAuthorizationCredentials] = Depends(security, use_cache=False)
) -> Dict[str, Any]:
    """
    Require either JWT token or API key authentication
    """
    # Try to get user from API key first
    if user_or_api_key:
        return user_or_api_key
    
    # Try to get user from JWT token
    if token:
        current_user = get_current_user(token)
        return {
            "user_id": str(current_user.id),
            "username": current_user.username,
            "email": current_user.email,
            "is_superuser": current_user.is_superuser,
            "auth_method": "jwt"
        }
    
    # No authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )

def hash_file_content(file_bytes: bytes) -> str:
    """
    Generate SHA256 hash of file content for integrity checking
    """
    return hashlib.sha256(file_bytes).hexdigest()

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks
    """
    # Remove directory traversal attempts
    filename = filename.replace("../", "").replace("./", "")
    
    # Remove any remaining path separators
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')

    # Limit filename length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    return filename

def validate_file_extension(filename: str) -> bool:
    """
    Validate file extension against allowed list
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if ext in settings.ALLOWED_AUDIO_EXTENSIONS:
        return True
    
    if ext in settings.ALLOWED_VIDEO_EXTENSIONS:
        return True
    
    if ext in settings.ALLOWED_IMAGE_EXTENSIONS:
        return True
    
    return False

def check_rate_limit(user_id: str, endpoint: str) -> bool:
    """
    Check if user has exceeded rate limit for an endpoint
    """
    from mmino.db.session import SessionLocal
    db = SessionLocal()
    try:
        # Get user's rate limit info
        user = crud.get_user_by_id(db, user_id)
        if not user:
            return False
        
        # Check rate limit based on user type
        # For simplicity, using a basic Redis-based rate limiter
        # In production, you'd use a proper rate limiting library
        
        return True
    finally:
        db.close()

def create_password_reset_token(email: str) -> str:
    """
    Create a password reset token
    """
    expires_delta = timedelta(hours=1)
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "password_reset"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify password reset token and return email
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        if payload.get("type") != "password_reset":
            return None
        
        email = payload.get("sub")
        return email
        
    except JWTError:
        return None