import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from .config import Settings

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "packages" / "shared-python" / "src"))

from creator_shared import get_connection, init_db, replace_audience_rows, upsert_video_metric

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeApiError(RuntimeError):
    pass


def _get_json(path: str, params: dict[str, object]) -> dict[str, Any]:
    url = f"{YOUTUBE_API_BASE}/{path}?{urlencode(params)}"
    try:
        with urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise YouTubeApiError(str(exc)) from exc


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _uploads_playlist_id(settings: Settings) -> str:
    payload = _get_json(
        "channels",
        {
            "part": "contentDetails",
            "id": settings.channel_id,
            "key": settings.api_key,
        },
    )
    items = payload.get("items") or []
    if not items:
        raise YouTubeApiError("No YouTube channel found for YOUTUBE_CHANNEL_ID.")
    return str(items[0]["contentDetails"]["relatedPlaylists"]["uploads"])


def _list_video_ids(settings: Settings, playlist_id: str) -> list[str]:
    ids: list[str] = []
    page_token = ""
    for _ in range(settings.page_limit):
        params = {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": settings.page_size,
            "key": settings.api_key,
        }
        if page_token:
            params["pageToken"] = page_token
        payload = _get_json("playlistItems", params)
        for item in payload.get("items") or []:
            video_id = item.get("contentDetails", {}).get("videoId")
            if video_id:
                ids.append(str(video_id))
        page_token = str(payload.get("nextPageToken") or "")
        if not page_token:
            break
    return ids


def _video_details(settings: Settings, ids: list[str]) -> list[dict[str, Any]]:
    videos: list[dict[str, Any]] = []
    for part in _chunks(ids, 50):
        payload = _get_json(
            "videos",
            {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(part),
                "key": settings.api_key,
            },
        )
        videos.extend([item for item in payload.get("items") or [] if isinstance(item, dict)])
    return videos


def _iso_date(value: str) -> str | None:
    if not value:
        return None
    return value.split("T", 1)[0]


def run_pipeline(settings: Settings) -> dict[str, object]:
    conn = get_connection(settings.db_path)
    init_db(conn)
    metric_date = datetime.now(timezone.utc).date().isoformat()
    try:
        playlist_id = _uploads_playlist_id(settings)
        ids = _list_video_ids(settings, playlist_id)
        videos = _video_details(settings, ids)
        for item in videos:
            snippet = item.get("snippet") or {}
            stats = item.get("statistics") or {}
            raw_id = str(item.get("id", ""))
            video_id = f"youtube:{raw_id}"
            upsert_video_metric(
                conn,
                video_id=video_id,
                platform="youtube",
                title=str(snippet.get("title") or "Untitled YouTube video"),
                publish_date=_iso_date(str(snippet.get("publishedAt") or "")),
                source_url=f"https://www.youtube.com/watch?v={raw_id}",
                thumbnail_url=str((snippet.get("thumbnails") or {}).get("high", {}).get("url", "")),
                views=int(stats.get("viewCount") or 0),
                likes=int(stats.get("likeCount") or 0),
                comments=int(stats.get("commentCount") or 0),
                shares=0,
                watch_time=0,
                metric_date=metric_date,
            )
            replace_audience_rows(
                conn,
                video_id,
                [{"region": "unknown", "age": "unknown", "gender": "all", "viewers": int(stats.get("viewCount") or 0)}],
            )
        conn.commit()
        return {"status": "success", "platform": "youtube", "videos_count": len(videos), "metric_date": metric_date}
    finally:
        conn.close()
