"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
)
from backend.config import JWT_EXPIRATION_MINUTES
from backend.schemas import LoginRequest, TokenResponse, UserProfile

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    """Authenticate administrator and return signed JWT bearer token."""
    if not authenticate_user(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject=request.username)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=JWT_EXPIRATION_MINUTES,
        username=request.username,
    )


@router.get("/me", response_model=UserProfile)
def get_user_profile(current_user: str = Depends(get_current_user)):
    """Return profile for the currently authenticated user session."""
    return UserProfile(
        username=current_user,
        role="Administrator",
        authenticated=True,
    )

