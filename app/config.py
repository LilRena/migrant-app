from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    token_expire_minutes: int = 30

    @field_validator("database_url", "secret_key")
    @classmethod
    def must_not_be_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must be set in .env")
        return v

    model_config = {"env_file": ".env", "extra": "ignore"}


try:
    settings = Settings()
except Exception as exc:
    import sys
    print(f"ERROR: cannot start — check your .env file.\n{exc}", file=sys.stderr)
    sys.exit(1)