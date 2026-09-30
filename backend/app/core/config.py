from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CloudVault"
    database_url: str = "postgresql+psycopg://cloudvault:cloudvault@localhost:5432/cloudvault"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    storage_mode: str = "local"
    local_storage_path: str = "./storage"

    aws_region: str = "ap-south-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_s3_bucket: str | None = None

    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def sqlalchemy_database_url(self) -> str:
        # Render supplies PostgreSQL URLs with the legacy postgres:// scheme.
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
