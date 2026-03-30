import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tiktok_analytics.config import load_settings
from tiktok_analytics.dashboard import run_dashboard


def main() -> int:
    settings = load_settings()
    run_dashboard(settings.db_path, settings.dashboard_host, settings.dashboard_port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
