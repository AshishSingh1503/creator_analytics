import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "worker-analytics" / "src"))

from worker_analytics import compute_metrics


def main() -> int:
    print(json.dumps(compute_metrics(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
