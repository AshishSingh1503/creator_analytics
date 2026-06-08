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
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            title TEXT NOT NULL,
            publish_date TEXT,
            source_url TEXT,
            thumbnail_url TEXT,
            last_seen_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS metrics_daily (
            video_id TEXT NOT NULL,
            date TEXT NOT NULL,
            views INTEGER NOT NULL DEFAULT 0,
            likes INTEGER NOT NULL DEFAULT 0,
            comments INTEGER NOT NULL DEFAULT 0,
            shares INTEGER NOT NULL DEFAULT 0,
            watch_time INTEGER NOT NULL DEFAULT 0,
            engagement_rate REAL NOT NULL DEFAULT 0,
            growth_rate REAL,
            PRIMARY KEY (video_id, date),
            FOREIGN KEY (video_id) REFERENCES videos(id)
        );

        CREATE TABLE IF NOT EXISTS audience_data (
            video_id TEXT NOT NULL,
            region TEXT NOT NULL,
            age TEXT NOT NULL,
            gender TEXT NOT NULL,
            viewers INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (video_id, region, age, gender),
            FOREIGN KEY (video_id) REFERENCES videos(id)
        );

        CREATE TABLE IF NOT EXISTS content_rankings (
            video_id TEXT PRIMARY KEY,
            rank INTEGER NOT NULL,
            score REAL NOT NULL,
            computed_at TEXT NOT NULL,
            FOREIGN KEY (video_id) REFERENCES videos(id)
        );

        CREATE TABLE IF NOT EXISTS platform_daily_summary (
            platform TEXT NOT NULL,
            date TEXT NOT NULL,
            videos INTEGER NOT NULL,
            views INTEGER NOT NULL,
            likes INTEGER NOT NULL,
            comments INTEGER NOT NULL,
            shares INTEGER NOT NULL,
            watch_time INTEGER NOT NULL,
            engagement_rate REAL NOT NULL,
            PRIMARY KEY (platform, date)
        );
        """
    )
    conn.commit()


def row_to_dict(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in row.keys()}
