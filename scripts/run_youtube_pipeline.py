import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "worker-youtube" / "src"))

from youtube_analytics.config import load_settings
from youtube_analytics.pipeline import run_pipeline


def main() -> int:
    print(json.dumps(run_pipeline(load_settings()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
