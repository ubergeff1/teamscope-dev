"""
Pydantic schemas for authentication and authorization.

These schemas handle the JWT-based authentication flow for the API.
Unlike other schema modules, there is no corresponding SQLAlchemy model --
authentication state is managed via JWT tokens rather than a dedicated
database table (user credentials may be stored externally or in a
separate user management system).

Schema usage:
    - LoginRequest  -- POST /auth/login  request body
    - TokenOut      -- POST /auth/login  response body (JWT token)
    - TokenData     -- Internal schema for decoded JWT payload (not exposed via API)
"""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Schema for login credentials (POST /auth/login request body).

    Accepts a username and password which are validated against the
    configured authentication backend.
    """
    # The user's login username.
    username: str
    # The user's plaintext password (transmitted over HTTPS; never stored in plaintext).
    password: str


class TokenOut(BaseModel):
    """Response schema for successful authentication (POST /auth/login response).

    Returns a JWT access token that the client includes in the Authorization
    header for subsequent requests (``Authorization: Bearer <token>``).
    """
    # The JWT access token string.
    access_token: str
    # Token type; always "bearer" per OAuth2 convention.
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Internal schema for decoded JWT token payload.

    Used by the authentication middleware to extract user identity from
    the JWT claims.  This schema is not exposed via any API endpoint --
    it is used internally when validating the ``Authorization`` header
    on protected routes.
    """
    # Username extracted from the JWT "sub" (subject) claim.
    # None if the token is missing or the claim is absent.
    username: str | None = None
