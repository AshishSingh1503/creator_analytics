import json
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from .config import Settings
from .db import get_connection, init_db
from .tiktok_api import TikTokApiError, chunked, list_videos, query_videos, refresh_access_token
from .token_store import get_tokens, read_token_file, token_needs_refresh, upsert_tokens, write_token_file


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _extract_video_items(payload: Dict[str, object]) -> List[Dict[str, object]]:
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return []

    videos = data.get("videos") or data.get("video_list") or []
    if isinstance(videos, list):
        return [v for v in videos if isinstance(v, dict)]
    return []


def _next_cursor(payload: Dict[str, object], current_cursor: int) -> Tuple[int, bool]:
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return current_cursor, False

    has_more = bool(data.get("has_more", False))
    cursor = data.get("cursor", current_cursor)
    try:
        return int(cursor), has_more
    except (TypeError, ValueError):
        return current_cursor, has_more


def _import_tokens_if_needed(conn, settings: Settings) -> Dict[str, object]:
    db_tokens = get_tokens(conn)
    if db_tokens:
        return db_tokens

    file_tokens = read_token_file(settings.token_json_path)
    if not file_tokens:
        raise RuntimeError(
            "No token found. Run authentication first to generate token JSON, then re-run pipeline."
        )

    upsert_tokens(conn, file_tokens)
    return get_tokens(conn) or {}


def _refresh_if_needed(tokens: Dict[str, object], settings: Settings) -> Dict[str, object]:
    if not token_needs_refresh(tokens, settings.refresh_buffer_seconds):
        return tokens

    refresh_token = str(tokens.get("refresh_token", ""))
    if not refresh_token:
        raise RuntimeError("Missing refresh_token. Re-run OAuth authentication.")

    refreshed = refresh_access_token(
        client_key=settings.client_key,
        client_secret=settings.client_secret,
        refresh_token=refresh_token,
    )

    if "access_token" not in refreshed or "refresh_token" not in refreshed:
        raise RuntimeError(f"Unexpected refresh response: {json.dumps(refreshed)}")

    return refreshed


def _upsert_videos(conn, videos: List[Dict[str, object]], fetched_at: str) -> None:
    for video in videos:
        conn.execute(
            """
            INSERT INTO videos (
                video_id, title, create_time, duration, share_url, cover_image_url, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                title=excluded.title,
                create_time=excluded.create_time,
                duration=excluded.duration,
                share_url=excluded.share_url,
                cover_image_url=excluded.cover_image_url,
                last_seen_at=excluded.last_seen_at
            """,
            (
                str(video.get("id", "")),
                str(video.get("title", "")),
                int(video.get("create_time") or 0),
                int(video.get("duration") or 0),
                str(video.get("share_url", "")),
                str(video.get("cover_image_url", "")),
                fetched_at,
            ),
        )


def _insert_analytics_snapshot(conn, videos: List[Dict[str, object]], fetched_at: str) -> None:
    for video in videos:
        conn.execute(
            """
            INSERT OR REPLACE INTO video_analytics (
                video_id, fetched_at, like_count, comment_count, share_count, view_count
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(video.get("id", "")),
                fetched_at,
                int(video.get("like_count") or 0),
                int(video.get("comment_count") or 0),
                int(video.get("share_count") or 0),
                int(video.get("view_count") or 0),
            ),
        )


def _store_daily_metrics(conn, metric_date: str, videos: List[Dict[str, object]], created_at: str) -> Dict[str, float]:
    total_videos = len(videos)
    total_views = sum(int(v.get("view_count") or 0) for v in videos)
    total_likes = sum(int(v.get("like_count") or 0) for v in videos)
    total_comments = sum(int(v.get("comment_count") or 0) for v in videos)
    total_shares = sum(int(v.get("share_count") or 0) for v in videos)
    avg_views = (total_views / total_videos) if total_videos else 0.0

    prev = conn.execute(
        """
        SELECT total_views FROM daily_metrics
        WHERE metric_date < ?
        ORDER BY metric_date DESC
        LIMIT 1
        """,
        (metric_date,),
    ).fetchone()

    views_growth_pct = None
    if prev and int(prev["total_views"]) > 0:
        views_growth_pct = ((total_views - int(prev["total_views"])) / int(prev["total_views"])) * 100.0

    conn.execute(
        """
        INSERT INTO daily_metrics (
            metric_date, total_videos, total_views, total_likes, total_comments,
            total_shares, avg_views_per_video, views_growth_pct, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(metric_date) DO UPDATE SET
            total_videos=excluded.total_videos,
            total_views=excluded.total_views,
            total_likes=excluded.total_likes,
            total_comments=excluded.total_comments,
            total_shares=excluded.total_shares,
            avg_views_per_video=excluded.avg_views_per_video,
            views_growth_pct=excluded.views_growth_pct,
            created_at=excluded.created_at
        """,
        (
            metric_date,
            total_videos,
            total_views,
            total_likes,
            total_comments,
            total_shares,
            avg_views,
            views_growth_pct,
            created_at,
        ),
    )

    return {
        "total_videos": float(total_videos),
        "total_views": float(total_views),
        "views_growth_pct": float(views_growth_pct) if views_growth_pct is not None else 0.0,
    }


def _insert_alert(conn, metric_date: str, level: str, message: str) -> None:
    conn.execute(
        "INSERT INTO alerts (created_at, level, message, metric_date) VALUES (?, ?, ?, ?)",
        (_utc_now_iso(), level, message, metric_date),
    )


def _evaluate_alerts(conn, settings: Settings, metric_date: str, metrics: Dict[str, float]) -> List[str]:
    created: List[str] = []

    if int(metrics["total_views"]) < settings.alert_min_views:
        msg = f"Total views ({int(metrics['total_views'])}) below threshold ({settings.alert_min_views})."
        _insert_alert(conn, metric_date, "warning", msg)
        created.append(msg)

    growth = metrics["views_growth_pct"]
    if growth < 0 and abs(growth) >= settings.alert_growth_drop_pct:
        msg = f"Views dropped {abs(growth):.2f}% vs previous day."
        _insert_alert(conn, metric_date, "critical", msg)
        created.append(msg)

    return created


def run_pipeline(settings: Settings) -> Dict[str, object]:
    conn = get_connection(settings.db_path)
    init_db(conn)

    started_at = _utc_now_iso()
    run_id = conn.execute(
        "INSERT INTO pipeline_runs (started_at, status, details) VALUES (?, ?, ?)",
        (started_at, "running", ""),
    ).lastrowid
    conn.commit()

    try:
        tokens = _import_tokens_if_needed(conn, settings)

        refreshed_tokens = _refresh_if_needed(tokens, settings)
        if refreshed_tokens is not tokens:
            upsert_tokens(conn, refreshed_tokens)
            write_token_file(settings.token_json_path, refreshed_tokens)
            tokens = get_tokens(conn) or refreshed_tokens

        access_token = str(tokens.get("access_token", ""))
        if not access_token:
            raise RuntimeError("Missing access token.")

        all_videos: List[Dict[str, object]] = []
        cursor = 0
        for _ in range(settings.page_limit):
            page = list_videos(access_token=access_token, page_size=settings.page_size, cursor=cursor)
            items = _extract_video_items(page)
            all_videos.extend(items)
            cursor, has_more = _next_cursor(page, cursor)
            if not has_more:
                break

        unique_ids = sorted({str(v.get("id", "")) for v in all_videos if v.get("id")})

        detailed: List[Dict[str, object]] = []
        for part in chunked(unique_ids, 20):
            resp = query_videos(access_token=access_token, video_ids=part)
            detailed.extend(_extract_video_items(resp))

        # Fallback: if query endpoint returns nothing, use list endpoint payload directly.
        videos_for_storage = detailed if detailed else all_videos

        fetched_at = _utc_now_iso()
        _upsert_videos(conn, videos_for_storage, fetched_at)
        _insert_analytics_snapshot(conn, videos_for_storage, fetched_at)

        metric_date = _today_utc()
        metrics = _store_daily_metrics(conn, metric_date, videos_for_storage, fetched_at)
        alerts = _evaluate_alerts(conn, settings, metric_date, metrics)

        conn.execute(
            "UPDATE pipeline_runs SET finished_at=?, status=?, details=? WHERE id=?",
            (
                _utc_now_iso(),
                "success",
                json.dumps({"videos": len(videos_for_storage), "alerts": alerts}),
                run_id,
            ),
        )
        conn.commit()

        return {
            "status": "success",
            "videos_count": len(videos_for_storage),
            "alerts": alerts,
            "metric_date": metric_date,
        }

    except (RuntimeError, TikTokApiError) as exc:
        conn.execute(
            "UPDATE pipeline_runs SET finished_at=?, status=?, details=? WHERE id=?",
            (_utc_now_iso(), "failed", str(exc), run_id),
        )
        conn.commit()
        raise
    finally:
        conn.close()
