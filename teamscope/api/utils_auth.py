"""
JWT authentication helpers.

This module provides the authentication infrastructure for the TeamScope API.
It handles three concerns:

  1. Password hashing and verification using bcrypt (via passlib).
  2. JWT token creation and decoding using the HS256 algorithm (via python-jose).
  3. A FastAPI dependency (``get_current_user``) that extracts and validates the
     JWT from the Authorization header on protected endpoints.

Authentication flow:
  - The client sends credentials to POST /api/auth/token.
  - The auth router verifies the password with ``verify_password``, then calls
    ``create_access_token`` to issue a JWT containing ``{"sub": username}``.
  - On subsequent requests, the client sends the JWT as a Bearer token.
  - Protected endpoints declare a dependency on ``get_current_user``, which
    decodes the token, extracts the username, and raises HTTP 401 if invalid.

Security notes:
  - The JWT secret key and expiration are configured via ``settings.secret_key``
    and ``settings.jwt_expire_minutes`` (see config.py).
  - Tokens are signed with HS256 (symmetric). The same secret is used for both
    signing and verification.
  - bcrypt is used for password hashing with automatic salt generation.
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Password hashing context -- uses bcrypt as the sole scheme.
# "deprecated='auto'" means any non-bcrypt hashes would be flagged for rehashing.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme that tells FastAPI/Swagger to look for a Bearer token and
# to direct users to the /api/auth/token endpoint for login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a bcrypt hash.

    Parameters:
        plain:  The plaintext password provided by the user at login.
        hashed: The bcrypt hash stored in the database or config.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt.

    A random salt is generated automatically by passlib. The returned string
    includes the salt, cost factor, and hash in the standard bcrypt format
    (e.g., ``$2b$12$...``).

    Parameters:
        plain: The plaintext password to hash.

    Returns:
        A bcrypt hash string suitable for storage.
    """
    return pwd_context.hash(plain)


def create_access_token(data: dict) -> str:
    """Create a signed JWT access token.

    The token payload is a copy of ``data`` with an ``exp`` (expiration) claim
    added. The expiration is set to ``jwt_expire_minutes`` minutes from now
    (defaults to 480 minutes / 8 hours -- see config.py).

    Parameters:
        data: The claims to include in the token. Typically ``{"sub": username}``.

    Returns:
        A URL-safe JWT string signed with HS256.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token.

    Validates the signature using the application's secret key and checks the
    ``exp`` claim. Raises ``jose.JWTError`` if the token is invalid, expired,
    or tampered with.

    Parameters:
        token: The raw JWT string (without the "Bearer " prefix).

    Returns:
        The decoded payload as a dictionary.

    Raises:
        jose.JWTError: If the token cannot be decoded or has expired.
    """
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """FastAPI dependency -- extracts and validates the current user from a JWT.

    This is injected into route handlers via ``Depends(get_current_user)``. It:
      1. Extracts the Bearer token from the Authorization header (handled by
         ``oauth2_scheme``).
      2. Decodes the JWT and retrieves the ``sub`` (subject) claim, which
         contains the username.
      3. Returns the username string if valid.
      4. Raises HTTP 401 with a ``WWW-Authenticate: Bearer`` header if the
         token is missing, expired, malformed, or lacks a ``sub`` claim.

    Parameters:
        token: The JWT string, automatically extracted by FastAPI's OAuth2
               dependency injection.

    Returns:
        The username (``sub`` claim) from the validated JWT.

    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exc
        return username
    except JWTError:
        raise credentials_exc
