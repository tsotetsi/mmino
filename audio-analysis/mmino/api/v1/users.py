"""
User management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional

from mmino.api.dependencies import (
    get_current_active_user_dep, get_current_superuser_dep,
    get_user_from_path, require_auth_dep, get_pagination_params
)
from mmino.db.session import get_db
from mmino.db import crud
from mmino.schemas import UserResponse, UserUpdate, UserStats
from mmino.core.security import get_password_hash

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: UserResponse = Depends(get_current_active_user_dep)
):
    """
    Get current user info
    """
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: UserResponse = Depends(get_current_active_user_dep),
    db = Depends(get_db)
):
    """
    Update current user
    """
    updated_user = crud.update_user(db, str(current_user.id), user_update)
    if not updated_user:
        raise HTTPException(404, "User not found")
    
    return UserResponse.from_orm(updated_user)

@router.get("/me/stats")
async def get_current_user_stats(
    current_user: UserResponse = Depends(get_current_active_user_dep),
    db = Depends(get_db)
):
    """
    Get current user statistics
    """
    stats = crud.get_user_stats(db, str(current_user.id))
    
    # Add daily jobs remaining
    user = crud.get_user_by_id(db, str(current_user.id))
    if user:
        stats["daily_jobs_remaining"] = max(0, user.max_daily_jobs - user.daily_job_count)
    
    return stats

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: UserResponse = Depends(get_user_from_path),
    db = Depends(get_db)
):
    """
    Get user by ID (admin or self)
    """
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    return UserResponse.from_orm(user)

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    current_user: UserResponse = Depends(get_current_superuser_dep),
    db = Depends(get_db)
):
    """
    List users (admin only)
    """
    users = crud.get_users(db, skip=skip, limit=limit, active_only=active_only)
    return [UserResponse.from_orm(user) for user in users]

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: UserResponse = Depends(get_current_superuser_dep),
    db = Depends(get_db)
):
    """
    Update user (admin only)
    """
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    updated_user = crud.update_user(db, user_id, user_update)
    if not updated_user:
        raise HTTPException(500, "Failed to update user")
    
    return UserResponse.from_orm(updated_user)

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserResponse = Depends(get_current_superuser_dep),
    db = Depends(get_db)
):
    """
    Delete user (admin only)
    """
    # Cannot delete yourself
    if str(current_user.id) == user_id:
        raise HTTPException(400, "Cannot delete your own account")
    
    success = crud.delete_user(db, user_id)
    if not success:
        raise HTTPException(404, "User not found")
    
    return {"message": "User deleted successfully"}

@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    new_password: str,
    current_user: UserResponse = Depends(get_current_superuser_dep),
    db = Depends(get_db)
):
    """
    Reset user password (admin only)
    """
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # Hash new password
    hashed_password = get_password_hash(new_password)
    
    # Update user
    user.hashed_password = hashed_password
    db.commit()
    
    return {"message": "Password reset successfully"}