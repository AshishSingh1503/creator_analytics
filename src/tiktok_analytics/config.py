import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip().lstrip("\ufeff")
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass
class Settings:
    client_key: str
    client_secret: str
    db_path: Path
    token_json_path: Path
    scopes: str
    page_limit: int
    page_size: int
    callback_timeout: int
    refresh_buffer_seconds: int
    alert_min_views: int
    alert_growth_drop_pct: float
    dashboard_host: str
    dashboard_port: int
    schedule_time: str


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    load_dotenv(Path(".env"))
    return Settings(
        client_key=_required("TIKTOK_CLIENT_KEY"),
        client_secret=_required("TIKTOK_CLIENT_SECRET"),
        db_path=Path(os.getenv("TIKTOK_DB_PATH", "data/tiktok_analytics.db")),
        token_json_path=Path(os.getenv("TIKTOK_TOKEN_PATH", "tiktok_tokens.json")),
        scopes=os.getenv("TIKTOK_SCOPES", "user.info.basic,video.list").strip() or "user.info.basic,video.list",
        page_limit=int(os.getenv("TIKTOK_VIDEO_PAGE_LIMIT", "5")),
        page_size=int(os.getenv("TIKTOK_VIDEO_PAGE_SIZE", "20")),
        callback_timeout=int(os.getenv("TIKTOK_CALLBACK_TIMEOUT_SECONDS", "180")),
        refresh_buffer_seconds=int(os.getenv("TIKTOK_REFRESH_BUFFER_SECONDS", "300")),
        alert_min_views=int(os.getenv("ALERT_MIN_TOTAL_VIEWS", "100")),
        alert_growth_drop_pct=float(os.getenv("ALERT_GROWTH_DROP_PERCENT", "30")),
        dashboard_host=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
        dashboard_port=int(os.getenv("DASHBOARD_PORT", "8050")),
        schedule_time=os.getenv("TIKTOK_SCHEDULE_TIME", "03:30"),
    )
