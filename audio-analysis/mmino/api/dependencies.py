"""
FastAPI dependencies for authentication and authorization
"""
import logging

from fastapi import Depends, HTTPException, status, Header, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any


from mmino.core.security import (
    get_current_user,
    get_current_active_user,
    get_current_superuser,
    get_api_key_user,
    require_auth as require_auth_func,
    verify_api_key,
    check_rate_limit
)
from mmino.core.config import settings
from mmino.db.session import get_db
from mmino.db import crud
from mmino.schemas import UserResponse

logger = logging.getLogger(__name__)

# Re-export require_auth for use in other modules
require_auth = require_auth_func

# HTTP Bearer authentication
security = HTTPBearer()

async def get_current_user_dep(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """
    Dependency to get current user from JWT token
    """
    return get_current_user(credentials)

async def get_current_active_user_dep(
    current_user: UserResponse = Depends(get_current_user_dep)
) -> UserResponse:
    """
    Dependency to get current active user
    """
    return get_current_active_user(current_user)

async def get_current_superuser_dep(
    current_user: UserResponse = Depends(get_current_active_user_dep)
) -> UserResponse:
    """
    Dependency to get current superuser
    """
    return get_current_superuser(current_user)

async def get_api_key_user_dep(
    x_api_key: Optional[str] = Header(None, description="API Key")
) -> Optional[Dict[str, Any]]:
    """
    Dependency to get user from API key
    """
    return get_api_key_user(x_api_key)

async def require_auth_dep(
    user_or_api_key: Optional[Dict[str, Any]] = Depends(get_api_key_user_dep),
    token: Optional[HTTPAuthorizationCredentials] = Depends(security, use_cache=False)
) -> Dict[str, Any]:
    """
    Dependency that requires either JWT or API key authentication
    """
    return require_auth_func(user_or_api_key, token)

async def optional_auth(
    x_api_key: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security, use_cache=False)
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - returns user info if authenticated, None otherwise
    """
    try:
        # Try API key first
        if x_api_key:
            user_info = verify_api_key(x_api_key)
            if user_info:
                user_info["auth_method"] = "api_key"
                return user_info
        
        # Try JWT token
        if credentials:
            user = get_current_user(credentials)
            return {
                "user_id": str(user.id),
                "username": user.username,
                "email": user.email,
                "is_superuser": user.is_superuser,
                "auth_method": "jwt"
            }
    
    except HTTPException:
        pass
    
    return None

async def rate_limiter(
    auth_info: Optional[Dict[str, Any]] = Depends(optional_auth),
    endpoint: str = Query(..., description="Endpoint name for rate limiting")
) -> None:
    """
    Rate limiting dependency
    """
    if auth_info:
        user_id = auth_info.get("user_id")
        if user_id:
            # Check rate limit
            db = next(get_db())
            try:
                if not check_rate_limit(user_id, endpoint):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded",
                        headers={"Retry-After": "60"}
                    )
            finally:
                db.close()

async def get_user_from_path(
    user_id: str,
    current_user: UserResponse = Depends(get_current_active_user_dep)
) -> UserResponse:
    """
    Verify user has access to the requested user resource
    """
    if str(current_user.id) != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's resources"
        )
    return current_user

async def get_job_owner(
    job_id: str,
    auth_info: Dict[str, Any] = Depends(require_auth_dep),
    db = Depends(get_db)
) -> Dict[str, Any]:
    """
    Verify user owns the job or is superuser
    """
    job = crud.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    user_id = auth_info.get("user_id")
    is_superuser = auth_info.get("is_superuser", False)
    
    # Allow access if user owns the job or is superuser
    if (job.user_id and str(job.user_id) == user_id) or is_superuser:
        return auth_info
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this job"
    )

async def check_file_size_limit(
    content_length: int = Header(..., ge=0),
    auth_info: Optional[Dict[str, Any]] = Depends(optional_auth)
) -> None:
    """
    Check if file size is within limits
    """
    if auth_info:
        user_id = auth_info.get("user_id")
        db = next(get_db())
        try:
            user = crud.get_user_by_id(db, user_id) if user_id else None
            max_size = user.max_file_size if user else settings.MAX_UPLOAD_SIZE
        finally:
            db.close()
    else:
        max_size = settings.MAX_UPLOAD_SIZE
    
    if content_length > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {max_size / (1024*1024)}MB"
        )

async def get_pagination_params(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return")
) -> Dict[str, int]:
    """
    Get pagination parameters
    """
    return {"skip": skip, "limit": limit}

async def get_sorting_params(
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order")
) -> Dict[str, str]:
    """
    Get sorting parameters
    """
    return {"sort_by": sort_by, "sort_order": sort_order}

async def get_filter_params(
    status: Optional[str] = Query(None, description="Filter by job status"),
    operation: Optional[str] = Query(None, description="Filter by operation type"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
) -> Dict[str, Any]:
    """
    Get filter parameters
    """
    filters = {}
    if status:
        filters["status"] = status
    if operation:
        filters["operation"] = operation
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date
    
    return filters

# Export dependencies
__all__ = [
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
    "get_api_key_user",
    "require_auth",
    "optional_auth",
    "rate_limiter",
    "get_user_from_path",
    "get_job_owner",
    "check_file_size_limit",
    "get_pagination_params",
    "get_sorting_params",
    "get_filter_params"
]