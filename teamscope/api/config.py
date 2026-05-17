"""
Application configuration -- reads all values from environment variables.

This module uses Pydantic Settings to define a strongly-typed configuration
class that automatically reads values from environment variables (and
optionally from a ``.env`` file at the project root).

Configuration values:
  - ``DATABASE_URL`` (required): SQLAlchemy-compatible database connection string.
    Example: ``postgresql://user:pass@localhost:5432/teamscope``
  - ``SECRET_KEY`` (required): Used to sign JWT tokens. Must be a long, random
    string. Keep this secret in production.
  - ``CORS_ORIGINS`` (default: "http://localhost:5000"): Comma-separated list of
    allowed frontend origins for CORS. In production, set this to the actual
    frontend domain(s).
  - ``ADMIN_USERNAME`` (default: "admin"): The username for the built-in admin
    account. This is the only user account (no user registration).
  - ``ADMIN_PASSWORD_HASH`` (default: placeholder): A bcrypt hash of the admin
    password. Generate a real hash with:
      ``python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('yourpassword'))"``
    The default placeholder value will not match any password.
  - ``JWT_EXPIRE_MINUTES`` (default: 480): How long JWT tokens remain valid,
    in minutes. 480 minutes = 8 hours (one work day). After expiration, the
    user must re-authenticate.

Usage:
  Import the singleton ``settings`` object anywhere in the application::

      from app.config import settings
      print(settings.database_url)

Set these in the ``.env`` file at the project root for local development.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Typed application settings, automatically populated from environment variables.

    Pydantic Settings handles type coercion (e.g., str -> int for jwt_expire_minutes)
    and raises validation errors at startup if required values are missing.
    """

    # -- Required settings (no defaults -- must be provided) --

    # SQLAlchemy database connection URL.
    # Supports PostgreSQL, SQLite, MySQL, etc.
    # Example: "postgresql://user:password@localhost:5432/teamscope"
    database_url: str

    # Secret key for signing JWT tokens (HS256).
    # Should be a cryptographically random string of at least 32 characters.
    secret_key: str

    # -- Optional settings (have sensible defaults) --

    # Comma-separated list of allowed CORS origins.
    # The frontend origin must be listed here for cross-origin API calls to work.
    # Multiple origins example: "http://localhost:5000,https://app.example.com"
    cors_origins: str = "http://localhost:5000"

    # Username for the single admin account.
    admin_username: str = "admin"

    # Bcrypt hash of the admin password. Generate with:
    #   python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('yourpassword'))"
    # The default placeholder will not match any password, forcing the operator
    # to set a real hash before the admin can log in.
    admin_password_hash: str = "$2b$12$placeholder_replace_this_value_in_dotenv_file"

    # JWT token lifetime in minutes. Default is 480 (8 hours / one work day).
    # Shorter values improve security; longer values improve convenience.
    jwt_expire_minutes: int = 480

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS_ORIGINS string into a list of origins.

        Strips whitespace around each origin so that
        ``"http://localhost:5000, https://example.com"`` works correctly.

        Returns:
            A list of origin URL strings.
        """
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        """Pydantic Settings configuration.

        - ``env_file = ".env"``: Tells Pydantic to look for a .env file in the
          working directory and load variables from it. Environment variables
          take precedence over .env values if both are set.
        """
        env_file = ".env"


# Singleton settings instance -- created once at import time.
# If required environment variables are missing, this line will raise a
# ValidationError with details about which variables need to be set.
settings = Settings()
