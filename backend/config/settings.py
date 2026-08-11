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
    mongo_db: str = "globtrade_dw"
    mongo_ops_db: str | None = None
    mongo_replica_uri: str | None = None
    mongo_replica_set: str | None = None

    api_host: str = "0.0.0.0"
    api_port: int = 8001
    web_port: int = 5001

    flask_secret_key: str = "globtrade-dev-change-in-production"
    session_days: int = 7

    product_uploads_dir: Path = ROOT / "frontend" / "static" / "uploads" / "products"
    max_product_image_mb: int = 2


settings = Settings()
