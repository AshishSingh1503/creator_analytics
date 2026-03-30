import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "worker-tiktok" / "src"))

from tiktok_analytics.config import load_settings
from tiktok_analytics.pipeline import run_pipeline


def main() -> int:
    settings = load_settings()
    try:
        result = run_pipeline(settings)
    except Exception as exc:  # broad to provide clean CLI error output
        print(f"Pipeline failed: {exc}")
        traceback.print_exc()
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
