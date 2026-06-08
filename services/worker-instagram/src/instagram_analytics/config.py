import os
from dataclasses import dataclass
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "packages" / "shared-python" / "src"))

from creator_shared.settings import analytics_db_path, load_dotenv


@dataclass
class Settings:
    access_token: str
    business_account_id: str
    db_path: Path
    page_size: int
    page_limit: int
    graph_version: str


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        access_token=_required("INSTAGRAM_ACCESS_TOKEN"),
        business_account_id=_required("INSTAGRAM_BUSINESS_ACCOUNT_ID"),
        db_path=analytics_db_path(),
        page_size=int(os.getenv("INSTAGRAM_MEDIA_PAGE_SIZE", "50")),
        page_limit=int(os.getenv("INSTAGRAM_MEDIA_PAGE_LIMIT", "10")),
        graph_version=os.getenv("META_GRAPH_VERSION", "v20.0"),
    )
