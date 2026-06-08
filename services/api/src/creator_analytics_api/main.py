import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "packages" / "shared-python" / "src"))

from creator_shared import analytics_db_path, get_connection, init_db, row_to_dict

app = FastAPI(title='Creator Analytics API')
SUPPORTED_PLATFORMS = ["youtube", "tiktok", "instagram"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


def _connection():
    conn = get_connection(analytics_db_path())
    init_db(conn)
    return conn


@app.get("/analytics/summary")
def analytics_summary() -> dict[str, object]:
    conn = _connection()
    try:
        latest_date = conn.execute("SELECT MAX(date) AS date FROM metrics_daily").fetchone()["date"]
        if not latest_date:
            return {
                "date": None,
                "totals": {"videos": 0, "views": 0, "likes": 0, "comments": 0, "shares": 0, "watch_time": 0},
                "engagement_rate": 0,
                "platforms": [],
            }

        totals = conn.execute(
            """
            SELECT COUNT(DISTINCT video_id) AS videos, SUM(views) AS views, SUM(likes) AS likes,
                   SUM(comments) AS comments, SUM(shares) AS shares, SUM(watch_time) AS watch_time
            FROM metrics_daily
            WHERE date=?
            """,
            (latest_date,),
        ).fetchone()
        views = int(totals["views"] or 0)
        engagement = int(totals["likes"] or 0) + int(totals["comments"] or 0) + int(totals["shares"] or 0)
        platform_rows = {
            row["platform"]: row_to_dict(row)
            for row in conn.execute(
                "SELECT * FROM platform_daily_summary WHERE date=?",
                (latest_date,),
            ).fetchall()
        }
        platforms = []
        for platform in SUPPORTED_PLATFORMS:
            platforms.append(
                platform_rows.get(
                    platform,
                    {
                        "platform": platform,
                        "date": latest_date,
                        "videos": 0,
                        "views": 0,
                        "likes": 0,
                        "comments": 0,
                        "shares": 0,
                        "watch_time": 0,
                        "engagement_rate": 0,
                    },
                )
            )
        return {
            "date": latest_date,
            "totals": {
                "videos": int(totals["videos"] or 0),
                "views": views,
                "likes": int(totals["likes"] or 0),
                "comments": int(totals["comments"] or 0),
                "shares": int(totals["shares"] or 0),
                "watch_time": int(totals["watch_time"] or 0),
            },
            "engagement_rate": (engagement / views) if views else 0,
            "platforms": platforms,
        }
    finally:
        conn.close()


@app.get("/platforms/status")
def platform_status() -> list[dict[str, object]]:
    conn = _connection()
    try:
        rows = {
            row["platform"]: row_to_dict(row)
            for row in conn.execute(
                """
                SELECT v.platform, COUNT(DISTINCT v.id) AS videos, MAX(v.last_seen_at) AS last_seen_at,
                       MAX(m.date) AS latest_metric_date
                FROM videos v
                LEFT JOIN metrics_daily m ON m.video_id = v.id
                GROUP BY v.platform
                """
            ).fetchall()
        }
        return [
            {
                "platform": platform,
                "configured": platform in rows,
                "videos": int((rows.get(platform) or {}).get("videos") or 0),
                "last_seen_at": (rows.get(platform) or {}).get("last_seen_at"),
                "latest_metric_date": (rows.get(platform) or {}).get("latest_metric_date"),
            }
            for platform in SUPPORTED_PLATFORMS
        ]
    finally:
        conn.close()


@app.get("/videos/top")
def top_videos(limit: int = 10) -> list[dict[str, object]]:
    conn = _connection()
    try:
        rows = conn.execute(
            """
            SELECT v.id, v.platform, v.title, v.publish_date, m.views, m.likes, m.comments, m.shares,
                   m.watch_time, m.engagement_rate, m.growth_rate, r.rank, r.score
            FROM metrics_daily m
            JOIN videos v ON v.id = m.video_id
            LEFT JOIN content_rankings r ON r.video_id = v.id
            WHERE m.date = (SELECT MAX(date) FROM metrics_daily)
            ORDER BY COALESCE(r.rank, 999999), m.views DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()


@app.get("/metrics/daily")
def daily_metrics(days: int = 30) -> list[dict[str, object]]:
    conn = _connection()
    try:
        rows = conn.execute(
            """
            SELECT m.date, v.platform, SUM(m.views) AS views, SUM(m.likes) AS likes,
                   SUM(m.comments) AS comments, SUM(m.shares) AS shares,
                   SUM(m.watch_time) AS watch_time,
                   AVG(m.engagement_rate) AS engagement_rate,
                   AVG(m.growth_rate) AS growth_rate
            FROM metrics_daily m
            JOIN videos v ON v.id = m.video_id
            GROUP BY m.date, v.platform
            ORDER BY m.date DESC, views DESC
            LIMIT ?
            """,
            (days * 3,),
        ).fetchall()
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()


@app.get("/audience")
def audience(limit: int = 50) -> list[dict[str, object]]:
    conn = _connection()
    try:
        rows = conn.execute(
            """
            SELECT v.platform, a.region, a.age, a.gender, SUM(a.viewers) AS viewers
            FROM audience_data a
            JOIN videos v ON v.id = a.video_id
            GROUP BY v.platform, a.region, a.age, a.gender
            ORDER BY viewers DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()


@app.post("/demo/seed")
def seed_demo_data() -> dict[str, object]:
    conn = _connection()
    today = date.today()
    now = datetime.now(timezone.utc).isoformat()
    platforms = ["youtube", "tiktok", "instagram"]
    try:
        for platform_index, platform in enumerate(platforms):
            for video_index in range(1, 5):
                video_id = f"{platform}-{video_index}"
                conn.execute(
                    """
                    INSERT INTO videos (id, platform, title, publish_date, source_url, thumbnail_url, last_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        title=excluded.title,
                        publish_date=excluded.publish_date,
                        last_seen_at=excluded.last_seen_at
                    """,
                    (
                        video_id,
                        platform,
                        f"{platform.title()} campaign video {video_index}",
                        (today - timedelta(days=video_index + platform_index)).isoformat(),
                        "",
                        "",
                        now,
                    ),
                )
                for day_offset in range(7):
                    metric_date = (today - timedelta(days=day_offset)).isoformat()
                    views = (platform_index + 2) * 1000 + video_index * 275 + (6 - day_offset) * 180
                    likes = int(views * (0.04 + platform_index * 0.01))
                    comments = int(views * 0.008)
                    shares = int(views * 0.012)
                    watch_time = views * (24 + video_index * 3)
                    engagement_rate = (likes + comments + shares) / views
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
                            engagement_rate=excluded.engagement_rate,
                            growth_rate=excluded.growth_rate
                        """,
                        (video_id, metric_date, views, likes, comments, shares, watch_time, engagement_rate, 0.08),
                    )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO audience_data (video_id, region, age, gender, viewers)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (video_id, "US", "25-34", "all", 1200 + platform_index * 250 + video_index * 80),
                )
        conn.commit()
        return {"status": "seeded", "videos": 12}
    finally:
        conn.close()

