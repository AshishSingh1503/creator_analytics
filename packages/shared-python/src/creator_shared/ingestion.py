from datetime import datetime, timezone
from typing import Iterable


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_video_metric(
    conn,
    *,
    video_id: str,
    platform: str,
    title: str,
    publish_date: str | None,
    source_url: str = "",
    thumbnail_url: str = "",
    views: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    watch_time: int = 0,
    metric_date: str | None = None,
    last_seen_at: str | None = None,
) -> None:
    last_seen = last_seen_at or utc_now_iso()
    date_value = metric_date or datetime.now(timezone.utc).date().isoformat()
    engagement_rate = ((likes + comments + shares) / views) if views else 0.0

    conn.execute(
        """
        INSERT INTO videos (id, platform, title, publish_date, source_url, thumbnail_url, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            platform=excluded.platform,
            title=excluded.title,
            publish_date=excluded.publish_date,
            source_url=excluded.source_url,
            thumbnail_url=excluded.thumbnail_url,
            last_seen_at=excluded.last_seen_at
        """,
        (video_id, platform, title, publish_date, source_url, thumbnail_url, last_seen),
    )
    conn.execute(
        """
        INSERT INTO metrics_daily (
            video_id, date, views, likes, comments, shares, watch_time, engagement_rate, growth_rate
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(video_id, date) DO UPDATE SET
            views=excluded.views,
            likes=excluded.likes,
            comments=excluded.comments,
            shares=excluded.shares,
            watch_time=excluded.watch_time,
            engagement_rate=excluded.engagement_rate
        """,
        (video_id, date_value, views, likes, comments, shares, watch_time, engagement_rate, None),
    )


def replace_audience_rows(conn, video_id: str, rows: Iterable[dict[str, object]]) -> None:
    conn.execute("DELETE FROM audience_data WHERE video_id=?", (video_id,))
    for row in rows:
        conn.execute(
            """
            INSERT INTO audience_data (video_id, region, age, gender, viewers)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                video_id,
                str(row.get("region", "unknown")),
                str(row.get("age", "unknown")),
                str(row.get("gender", "all")),
                int(row.get("viewers") or 0),
            ),
        )
