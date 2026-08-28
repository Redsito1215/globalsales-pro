from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    pocketbase_collection: str = "sales_records"
    csv_source: Path = ROOT / "data" / "sales.csv"
    data_raw_dir: Path = ROOT / "data" / "raw"
    data_parquet_dir: Path = ROOT / "data" / "parquet"

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_server_selection_timeout_ms: int = 5000
    mongo_connect_timeout_ms: int = 5000
    mongo_db: str = "globtrade_dw"
    mongo_ops_db: str | None = None
    mongo_replica_uri: str | None = None
    mongo_replica_set: str | None = None

    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_database: str = "globtrade_analytics"
    clickhouse_secure: bool = False

    api_host: str = "0.0.0.0"
    api_port: int = 8001
    web_port: int = 5001
    app_env: str = "development"
    cors_origins: str = "http://localhost:5001,http://127.0.0.1:5001"

    flask_secret_key: str = "globtrade-dev-change-in-production"
    session_days: int = 7  # compatibilidad con instalaciones anteriores
    session_idle_minutes: int = 120
    session_cookie_secure: bool = False

    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def assert_safe_production(self) -> None:
        if self.app_env.lower() != "production":
            return
        insecure = {"", "globtrade-dev-change-in-production", "globtrade-docker-change-me", "cambia-esto-en-produccion"}
        if self.flask_secret_key in insecure or len(self.flask_secret_key) < 32:
            raise RuntimeError("FLASK_SECRET_KEY debe ser aleatoria y tener al menos 32 caracteres en producción.")
        if not self.session_cookie_secure:
            raise RuntimeError("SESSION_COOKIE_SECURE debe estar habilitado en producción.")

    product_uploads_dir: Path = ROOT / "frontend" / "static" / "uploads" / "products"
    company_uploads_dir: Path = ROOT / "frontend" / "static" / "uploads" / "company"
    static_dir: Path = ROOT / "frontend" / "static"
    max_product_image_mb: int = 2

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-5-mini"
    ai_timeout_seconds: int = 60


settings = Settings()
