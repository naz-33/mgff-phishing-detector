"""Configuration settings for ZanderEtAlFishing Dashboard Backend."""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "zander_email_monitor.db"))

# Security & Authentication
# Secret key for JWT signing - in production can be overridden via environment variable
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "zander_phishing_thesis_jwt_secret_key_2026_secured")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = int(os.environ.get("JWT_EXPIRATION_MINUTES", "480"))  # 8 hours

# Default administrator credentials (can be overridden via environment variables)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
# Default password for thesis prototype demonstration
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ZanderAdmin2026!")

# Gmail OAuth paths
GMAIL_CREDENTIALS_PATH = os.environ.get("GMAIL_CREDENTIALS_PATH", str(BASE_DIR / "credentials" / "credentials.json"))
GMAIL_TOKEN_PATH = os.environ.get("GMAIL_TOKEN_PATH", str(BASE_DIR / "credentials" / "token.json"))

# Scanner configuration
POLLING_INTERVAL_SECONDS = int(os.environ.get("POLLING_INTERVAL_SECONDS", "60"))

