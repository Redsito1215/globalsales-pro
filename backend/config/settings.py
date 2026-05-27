from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    pocketbase_url: str = "http://127.0.0.1:8090"
    pocketbase_admin_email: str = "admin@globtrade.local"
    pocketbase_admin_password: str = "changeme"
    pocketbase_collection: str = "sales_records"

    csv_source: Path = ROOT / "data" / "sales.csv"
    data_raw_dir: Path = ROOT / "data" / "raw"
    data_parquet_dir: Path = ROOT / "data" / "parquet"

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "globtrade_dw"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    web_port: int = 5000

    flask_secret_key: str = "globtrade-dev-change-in-production"
    session_days: int = 7

    def model_post_init(self, __context) -> None:
        def _clean(s: str) -> str:
            return s.strip().strip("\ufeff").strip("\r").strip("\n")

        self.pocketbase_admin_email = _clean(self.pocketbase_admin_email)
        self.pocketbase_admin_password = _clean(self.pocketbase_admin_password)
        self.pocketbase_url = self.pocketbase_url.rstrip("/")
        self.flask_secret_key = _clean(self.flask_secret_key)


settings = Settings()
