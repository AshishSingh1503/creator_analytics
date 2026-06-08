import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "worker-tiktok" / "src"))
sys.path.insert(0, str(ROOT / "services" / "worker-youtube" / "src"))
sys.path.insert(0, str(ROOT / "services" / "worker-instagram" / "src"))
sys.path.insert(0, str(ROOT / "services" / "worker-analytics" / "src"))

from instagram_analytics.config import load_settings as load_instagram_settings
from instagram_analytics.pipeline import run_pipeline as run_instagram_pipeline
from tiktok_analytics.config import load_settings as load_tiktok_settings
from tiktok_analytics.pipeline import run_pipeline as run_tiktok_pipeline
from worker_analytics import compute_metrics
from youtube_analytics.config import load_settings as load_youtube_settings
from youtube_analytics.pipeline import run_pipeline as run_youtube_pipeline


def _run_platform(name: str, load_settings, run_pipeline) -> dict[str, object]:
    try:
        settings = load_settings()
        return run_pipeline(settings)
    except ValueError as exc:
        return {"status": "skipped", "platform": name, "reason": str(exc)}
    except Exception as exc:
        return {
            "status": "failed",
            "platform": name,
            "reason": str(exc),
            "traceback": traceback.format_exc(),
        }


def main() -> int:
    results = {
        "tiktok": _run_platform("tiktok", load_tiktok_settings, run_tiktok_pipeline),
        "youtube": _run_platform("youtube", load_youtube_settings, run_youtube_pipeline),
        "instagram": _run_platform("instagram", load_instagram_settings, run_instagram_pipeline),
    }
    results["analytics"] = compute_metrics()
    print(json.dumps(results, indent=2))

    failed = [name for name, result in results.items() if result.get("status") == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
