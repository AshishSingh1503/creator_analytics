import sqlite3
from pathlib import Path


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            scope TEXT,
            token_type TEXT,
            expires_in INTEGER,
            refresh_expires_in INTEGER,
            access_expires_at INTEGER,
            refresh_expires_at INTEGER,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            create_time INTEGER,
            duration INTEGER,
            share_url TEXT,
            cover_image_url TEXT,
            last_seen_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS video_analytics (
            video_id TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            like_count INTEGER,
            comment_count INTEGER,
            share_count INTEGER,
            view_count INTEGER,
            PRIMARY KEY (video_id, fetched_at)
        );

        CREATE TABLE IF NOT EXISTS daily_metrics (
            metric_date TEXT PRIMARY KEY,
            total_videos INTEGER NOT NULL,
            total_views INTEGER NOT NULL,
            total_likes INTEGER NOT NULL,
            total_comments INTEGER NOT NULL,
            total_shares INTEGER NOT NULL,
            avg_views_per_video REAL NOT NULL,
            views_growth_pct REAL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            metric_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            details TEXT
        );
        """
    )
    conn.commit()
