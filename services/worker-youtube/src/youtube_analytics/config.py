import os
from dataclasses import dataclass
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "packages" / "shared-python" / "src"))

from creator_shared.settings import analytics_db_path, load_dotenv


@dataclass
class Settings:
    api_key: str
    channel_id: str
    db_path: Path
    page_size: int
    page_limit: int


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        api_key=_required("YOUTUBE_API_KEY"),
        channel_id=_required("YOUTUBE_CHANNEL_ID"),
        db_path=analytics_db_path(),
        page_size=int(os.getenv("YOUTUBE_VIDEO_PAGE_SIZE", "50")),
        page_limit=int(os.getenv("YOUTUBE_VIDEO_PAGE_LIMIT", "10")),
    )
