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


class InstagramApiError(RuntimeError):
    pass


def _graph_base(settings: Settings) -> str:
    return f"https://graph.facebook.com/{settings.graph_version}"


def _get_json(url: str, params: dict[str, object]) -> dict[str, Any]:
    request_url = f"{url}?{urlencode(params)}"
    try:
        with urlopen(request_url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise InstagramApiError(str(exc)) from exc


def _metric_map(payload: dict[str, Any]) -> dict[str, int]:
    values: dict[str, int] = {}
    for item in payload.get("data") or []:
        name = str(item.get("name") or "")
        metric_values = item.get("values") or []
        if metric_values:
            values[name] = int(metric_values[0].get("value") or 0)
    return values


def _list_media(settings: Settings) -> list[dict[str, Any]]:
    media: list[dict[str, Any]] = []
    url = f"{_graph_base(settings)}/{settings.business_account_id}/media"
    params = {
        "access_token": settings.access_token,
        "fields": "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,like_count,comments_count",
        "limit": settings.page_size,
    }
    for _ in range(settings.page_limit):
        payload = _get_json(url, params)
        media.extend([item for item in payload.get("data") or [] if isinstance(item, dict)])
        next_url = (payload.get("paging") or {}).get("next")
        if not next_url:
            break
        url = str(next_url)
        params = {}
    return media


def _media_insights(settings: Settings, media_id: str) -> dict[str, int]:
    payload = _get_json(
        f"{_graph_base(settings)}/{media_id}/insights",
        {
            "access_token": settings.access_token,
            "metric": "views,reach,likes,comments,shares,total_interactions",
        },
    )
    return _metric_map(payload)


def _caption_title(caption: str) -> str:
    text = " ".join(caption.split())
    if not text:
        return "Instagram media"
    return text[:90]


def run_pipeline(settings: Settings) -> dict[str, object]:
    conn = get_connection(settings.db_path)
    init_db(conn)
    metric_date = datetime.now(timezone.utc).date().isoformat()
    try:
        media = _list_media(settings)
        for item in media:
            raw_id = str(item.get("id", ""))
            insights = _media_insights(settings, raw_id)
            views = insights.get("views") or insights.get("reach") or 0
            likes = insights.get("likes") or int(item.get("like_count") or 0)
            comments = insights.get("comments") or int(item.get("comments_count") or 0)
            shares = insights.get("shares") or 0
            upsert_video_metric(
                conn,
                video_id=f"instagram:{raw_id}",
                platform="instagram",
                title=_caption_title(str(item.get("caption") or "")),
                publish_date=str(item.get("timestamp") or "").split("T", 1)[0] or None,
                source_url=str(item.get("permalink") or ""),
                thumbnail_url=str(item.get("thumbnail_url") or item.get("media_url") or ""),
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                watch_time=0,
                metric_date=metric_date,
            )
            replace_audience_rows(
                conn,
                f"instagram:{raw_id}",
                [{"region": "unknown", "age": "unknown", "gender": "all", "viewers": views}],
            )
        conn.commit()
        return {"status": "success", "platform": "instagram", "videos_count": len(media), "metric_date": metric_date}
    finally:
        conn.close()
