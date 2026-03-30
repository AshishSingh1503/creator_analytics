import time
from datetime import datetime, timedelta

from .config import Settings
from .pipeline import run_pipeline


def _seconds_until(schedule_time: str) -> float:
    now = datetime.now()
    hour, minute = [int(x) for x in schedule_time.split(":", 1)]
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    return (target - now).total_seconds()


def run_daily_scheduler(settings: Settings) -> None:
    print(f"Scheduler started. Daily run at {settings.schedule_time} local time.")
    while True:
        wait_seconds = _seconds_until(settings.schedule_time)
        print(f"Sleeping {int(wait_seconds)}s until next run...")
        time.sleep(max(wait_seconds, 1))

        print("Running daily pipeline...")
        try:
            result = run_pipeline(settings)
            print(f"Pipeline success: {result}")
        except Exception as exc:  # broad on purpose for scheduler resilience
            print(f"Pipeline failed: {exc}")
