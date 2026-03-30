import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tiktok_analytics.config import load_settings
from tiktok_analytics.scheduler import run_daily_scheduler


def main() -> int:
    settings = load_settings()
    run_daily_scheduler(settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
