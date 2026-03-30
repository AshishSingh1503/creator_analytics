import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Iterable, List

API_HOST = "https://open.tiktokapis.com"
TOKEN_URL = f"{API_HOST}/v2/oauth/token/"
LIST_VIDEOS_URL = f"{API_HOST}/v2/video/list/"
QUERY_VIDEOS_URL = f"{API_HOST}/v2/video/query/"

VIDEO_FIELDS = [
    "id",
    "title",
    "create_time",
    "duration",
    "share_url",
    "cover_image_url",
    "like_count",
    "comment_count",
    "share_count",
    "view_count",
]


class TikTokApiError(RuntimeError):
    pass


def _parse_json_response(resp_bytes: bytes) -> Dict[str, object]:
    try:
        return json.loads(resp_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise TikTokApiError("Failed to parse TikTok JSON response") from exc


def _request_json(url: str, method: str, headers: Dict[str, str], payload: Dict[str, object]) -> Dict[str, object]:
    data = None
    if payload:
        data = json.dumps(payload).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}

    req = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return _parse_json_response(response.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise TikTokApiError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise TikTokApiError(f"Network error: {exc.reason}") from exc


def refresh_access_token(client_key: str, client_secret: str, refresh_token: str) -> Dict[str, object]:
    body = urllib.parse.urlencode(
        {
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url=TOKEN_URL,
        method="POST",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return _parse_json_response(response.read())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise TikTokApiError(f"Refresh failed HTTP {exc.code}: {body_text}") from exc
    except urllib.error.URLError as exc:
        raise TikTokApiError(f"Network error during token refresh: {exc.reason}") from exc


def list_videos(access_token: str, page_size: int, cursor: int = 0) -> Dict[str, object]:
    fields = ",".join(VIDEO_FIELDS)
    url = f"{LIST_VIDEOS_URL}?fields={urllib.parse.quote(fields)}"

    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"max_count": page_size, "cursor": cursor}
    return _request_json(url=url, method="POST", headers=headers, payload=payload)


def query_videos(access_token: str, video_ids: Iterable[str]) -> Dict[str, object]:
    ids = [video_id for video_id in video_ids if video_id]
    fields = ",".join(VIDEO_FIELDS)
    url = f"{QUERY_VIDEOS_URL}?fields={urllib.parse.quote(fields)}"

    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"filters": {"video_ids": ids}}
    return _request_json(url=url, method="POST", headers=headers, payload=payload)


def chunked(items: List[str], chunk_size: int) -> List[List[str]]:
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]
