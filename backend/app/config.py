from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="YUKIT_", extra="ignore")

    environment: Literal["local", "test", "production"] = "local"
    app_name: str = "YuKit"
    public_base_url: str = "http://localhost:5173"
    api_base_url: str = "http://localhost:8000"
    database_url: str = ""
    redis_url: str = ""
    session_secret: str = Field(default="local-dev-session-secret-change-me", min_length=32)
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8000"]
    docs_enabled: bool = True
    dev_auth_enabled: bool = False
    github_client_id: str = ""
    github_client_secret: str = ""
    github_oauth_authorize_url: str = "https://github.com/login/oauth/authorize"
    github_oauth_token_url: str = "https://github.com/login/oauth/access_token"
    github_api_user_url: str = "https://api.github.com/user"
    github_api_emails_url: str = "https://api.github.com/user/emails"

    @property
    def effective_docs_enabled(self) -> bool:
        return self.environment != "production" and self.docs_enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()
