"""Authentication utilities for ZanderEtAlFishing Dashboard Backend.

Implements PBKDF2-HMAC-SHA256 password hashing with salt and PyJWT tokens.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from backend.config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    JWT_ALGORITHM,
    JWT_EXPIRATION_MINUTES,
    JWT_SECRET_KEY,
)

security = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if salt is None:
        salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    )
    return f"{salt}${dk.hex()}"


def verify_password(plain_password: str, hashed: str) -> bool:
    """Verify password against hashed string in format salt$hash."""
    try:
        salt, expected_hash = hashed.split("$", 1)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        )
        return hmac.compare_digest(dk.hex(), expected_hash)
    except Exception:
        return False


# Generate administrator password hash at startup
STORED_ADMIN_HASH = hash_password(ADMIN_PASSWORD)


def authenticate_user(username: str, password: str) -> bool:
    """Check username and password against configured admin credentials."""
    if username != ADMIN_USERNAME:
        return False
    return verify_password(password, STORED_ADMIN_HASH)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create signed JWT token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=JWT_EXPIRATION_MINUTES)
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "ZanderEtAlFishing",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            issuer="ZanderEtAlFishing",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """FastAPI dependency to extract and authenticate current user from Bearer header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    username: str = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username

