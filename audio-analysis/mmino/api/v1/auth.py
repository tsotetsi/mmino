"""
Authentication endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from typing import Optional

from mmino.db.session import get_db
from mmino.db import crud
from mmino.schemas import (
    Token, RegisterRequest, UserResponse, 
    PasswordResetRequest, PasswordResetConfirm
)
from mmino.core.security import (
    get_password_hash, verify_password,
    create_access_token, create_refresh_token,
    verify_password_reset_token
)
from mmino.core.config import settings

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db = Depends(get_db)
):
    """
    OAuth2 compatible token login
    """
    print("form_data: ", form_data)

    # Try to find user by username or email
    user = crud.get_user_by_username(db, form_data.username)
    if not user:
        user = crud.get_user_by_email(db, form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=refresh_token_expires
    )
    
    # Update last login time
    user.last_login_at = datetime.utcnow()
    db.commit()

    print("form_data.username: ", form_data.username)
    print("user.username: ", user.username)
    print("user.email: ", user.email)
    print("user.is_active: ", user.is_active)
    print("user.last_login_at: ", user.last_login_at)
    print("access_token_expires: ", access_token_expires)
    print("refresh_token_expires: ", refresh_token_expires)
    
    print("access_token", access_token)
    print("refresh_token", refresh_token)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: RegisterRequest,
    db = Depends(get_db)
):
    """
    Register a new user
    """
    # Check if user already exists
    existing_user = crud.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(400, "Email already registered")
    
    existing_user = crud.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(400, "Username already taken")
    
    # Create user
    from mmino.schemas import UserCreate
    user_create = UserCreate(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        full_name=user_data.full_name
    )
    
    user = crud.create_user(db, user_create)
    
    return UserResponse.from_orm(user)

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    from mmino.core.security import verify_refresh_token
    
    try:
        payload = verify_refresh_token(refresh_token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(401, "Invalid refresh token")
        
        user = crud.get_user(db, user_id)
        if not user or not user.is_active:
            raise HTTPException(401, "User not found or inactive")
        
        # Create new tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        new_access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=access_token_expires
        )
        
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=refresh_token_expires
        )
        
        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    
    except Exception as e:
        raise HTTPException(401, "Invalid refresh token")

@router.post("/password-reset")
async def request_password_reset(
    request: PasswordResetRequest,
    db = Depends(get_db)
):
    """
    Request password reset email
    """
    user = crud.get_user_by_email(db, request.email)
    if not user or not user.is_active:
        # Don't reveal if user exists
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    from mmino.core.security import create_password_reset_token
    reset_token = create_password_reset_token(request.email)
    
    # In production, you would send an email here
    # For now, return the token (for testing only!)
    return {
        "message": "Password reset email sent",
        "reset_token": reset_token  # Remove this in production!
    }

@router.post("/password-reset/confirm")
async def confirm_password_reset(
    request: PasswordResetConfirm,
    db = Depends(get_db)
):
    """
    Confirm password reset with token
    """
    email = verify_password_reset_token(request.token)
    if not email:
        raise HTTPException(400, "Invalid or expired reset token")
    
    user = crud.get_user_by_email(db, email)
    if not user or not user.is_active:
        raise HTTPException(400, "User not found or inactive")
    
    # Update password
    hashed_password = get_password_hash(request.new_password)
    user.hashed_password = hashed_password
    db.commit()
    
    return {"message": "Password updated successfully"}

@router.post("/logout")
async def logout():
    """
    Logout endpoint (client should discard tokens)
    """
    return {"message": "Successfully logged out"}