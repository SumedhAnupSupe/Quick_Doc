"""Application settings, loaded from environment variables (see .env.example)."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "APAAR NEXUS"
    environment: str = "development"  # development | test | production
    api_prefix: str = "/api/v1"

    # Operational DB. Central / State vault catalogues can use their own connection
    # (and DB role) so access boundaries are separate from the operational database.
    database_url: str = "sqlite:///./apaar_nexus.db"
    central_vault_database_url: str | None = None
    state_vault_database_url: str | None = None

    # Auth
    secret_key: str = "change-me-in-production-min-32-chars!!"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    cors_origins: str = "http://localhost:5173"

    # Files
    storage_root: str = "./private_storage"
    max_request_bytes: int = 12 * 1024 * 1024

    # OTP simulation (no real SMS provider is integrated)
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 3
    expose_demo_otp: bool = True  # refused in production by assert_safe()

    demo_mode: bool = True  # demo seed + login hints; refused in production

    @field_validator("environment")
    @classmethod
    def _env(cls, v: str) -> str:
        if v not in {"development", "test", "production"}:
            raise ValueError("environment must be development, test or production")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def assert_safe(self) -> None:
        """Refuse to boot in production with insecure defaults."""
        if self.is_production:
            if self.secret_key.startswith("change-me") or len(self.secret_key) < 32:
                raise RuntimeError("SECRET_KEY must be set to a strong value in production")
            if self.demo_mode or self.expose_demo_otp:
                raise RuntimeError("DEMO_MODE and EXPOSE_DEMO_OTP must be false in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
