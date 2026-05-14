"""
Application configuration — reads all values from environment variables.
Set these in the .env file at the project root.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    cors_origins: str = "http://localhost:5000"
    admin_username: str = "admin"
    # Store a bcrypt hash. Generate with:
    #   python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('yourpassword'))"
    admin_password_hash: str = "$2b$12$placeholder_replace_this_value_in_dotenv_file"
    jwt_expire_minutes: int = 480

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
