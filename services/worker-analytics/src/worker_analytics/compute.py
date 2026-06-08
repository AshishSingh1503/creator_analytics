import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "packages" / "shared-python" / "src"))

from creator_shared import analytics_db_path, get_connection, init_db


def compute_metrics(db_path: Path | None = None) -> dict[str, object]:
    conn = get_connection(db_path or analytics_db_path())
    init_db(conn)
    computed_at = datetime.now(timezone.utc).isoformat()

    try:
        conn.execute("DELETE FROM platform_daily_summary")
        conn.execute(
            """
            INSERT INTO platform_daily_summary (
                platform, date, videos, views, likes, comments, shares, watch_time, engagement_rate
            )
            SELECT v.platform, m.date, COUNT(DISTINCT m.video_id), SUM(m.views), SUM(m.likes),
                   SUM(m.comments), SUM(m.shares), SUM(m.watch_time),
                   CASE
                       WHEN SUM(m.views) = 0 THEN 0
                       ELSE CAST(SUM(m.likes + m.comments + m.shares) AS REAL) / SUM(m.views)
                   END
            FROM metrics_daily m
            JOIN videos v ON v.id = m.video_id
            GROUP BY v.platform, m.date
            """
        )

        latest_date = conn.execute("SELECT MAX(date) AS date FROM metrics_daily").fetchone()["date"]
        conn.execute("DELETE FROM content_rankings")
        if latest_date:
            rows = conn.execute(
                """
                SELECT video_id,
                       (engagement_rate * 1000.0) + (watch_time / 1000.0) + (views / 10000.0) AS score
                FROM metrics_daily
                WHERE date=?
                ORDER BY score DESC
                """,
                (latest_date,),
            ).fetchall()
            for index, row in enumerate(rows, start=1):
                conn.execute(
                    """
                    INSERT INTO content_rankings (video_id, rank, score, computed_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (row["video_id"], index, float(row["score"] or 0), computed_at),
                )

        conn.commit()
        return {
            "status": "success",
            "computed_at": computed_at,
            "latest_metric_date": latest_date,
            "ranked_videos": conn.execute("SELECT COUNT(*) AS count FROM content_rankings").fetchone()["count"],
        }
    finally:
        conn.close()
