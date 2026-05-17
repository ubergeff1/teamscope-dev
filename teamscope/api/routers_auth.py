"""
Auth router — API prefix: /auth

Handles authentication for the application. Operates in single-user mode where
credentials are stored in environment variables:
  - ADMIN_USERNAME: the expected username
  - ADMIN_PASSWORD_HASH: a bcrypt hash of the password

To generate a password hash, run:
  python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('yourpassword'))"

Endpoints:
  POST /auth/token — Authenticate and receive a JWT access token
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import settings
from app.schemas.auth import TokenOut
from app.utils.auth import verify_password, create_access_token

# Router setup: all endpoints prefixed with /auth, grouped under "auth" tag
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenOut)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """POST /auth/token — Authenticate and obtain a JWT access token.

    Accepts OAuth2 password grant form data (username + password).
    Validates the username against the configured admin username, then
    verifies the password against the stored bcrypt hash.

    Returns a TokenOut containing the JWT access_token on success.
    Raises 401 Unauthorized if credentials are incorrect.
    """
    # Verify username matches the configured admin username
    if form_data.username != settings.admin_username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    # Verify password against the stored bcrypt hash
    if not verify_password(form_data.password, settings.admin_password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    # Generate a JWT with the username as the subject claim
    token = create_access_token({"sub": form_data.username})
    return TokenOut(access_token=token)
