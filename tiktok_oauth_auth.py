import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Optional, Tuple

AUTH_BASE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def get_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def build_auth_url(
    client_key: str,
    redirect_uri: str,
    scope: str,
    state: str,
    disable_auto_auth: Optional[str],
) -> str:
    params = {
        "client_key": client_key,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    if disable_auto_auth is not None and disable_auto_auth.strip() in {"0", "1"}:
        params["disable_auto_auth"] = disable_auto_auth.strip()

    return AUTH_BASE_URL + "?" + urllib.parse.urlencode(params)


def parse_callback_url(callback_url: str) -> Tuple[str, Optional[str], Optional[str]]:
    parsed = urllib.parse.urlparse(callback_url)
    query = urllib.parse.parse_qs(parsed.query)

    code = (query.get("code") or [None])[0]
    state = (query.get("state") or [None])[0]
    error = (query.get("error") or [None])[0]
    return code or "", state, error


def exchange_code_for_token(
    client_key: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> Dict[str, object]:
    payload = {
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }

    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        TOKEN_URL,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"TikTok token request failed ({exc.code}): {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error while requesting token: {exc.reason}") from exc


def persist_tokens(token_data: Dict[str, object], token_path: Path) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")


def is_local_redirect_uri(redirect_uri: str) -> bool:
    parsed = urllib.parse.urlparse(redirect_uri)
    return parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}


def capture_code_via_local_callback(redirect_uri: str, auth_url: str, timeout_seconds: int) -> str:
    parsed = urllib.parse.urlparse(redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 80
    expected_path = parsed.path or "/"

    result: Dict[str, str] = {}
    done = threading.Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            request_path = urllib.parse.urlparse(self.path).path or "/"
            if request_path != expected_path:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Not Found")
                return

            full_url = f"http://{host}:{port}{self.path}"
            result["callback_url"] = full_url
            done.set()

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Authentication complete.</h2><p>You can close this tab and return to the terminal.</p></body></html>"
            )

        def log_message(self, format: str, *args: object) -> None:
            return

    try:
        server = HTTPServer((host, port), CallbackHandler)
    except OSError as exc:
        raise RuntimeError(
            f"Could not start local callback server on {host}:{port}. "
            "Make sure your TIKTOK_REDIRECT_URI points to a free local port."
        ) from exc

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print(f"\nListening for TikTok callback at {redirect_uri}")
    print("Open and authorize with this URL:\n")
    print(auth_url)

    if get_bool_env("TIKTOK_OPEN_BROWSER", default=True):
        webbrowser.open(auth_url)

    started = time.time()
    while not done.is_set():
        if time.time() - started > timeout_seconds:
            server.shutdown()
            raise RuntimeError("Timed out waiting for TikTok callback.")
        time.sleep(0.2)

    server.shutdown()
    return result["callback_url"]


def capture_code_manually(auth_url: str) -> str:
    print("\nOpen and authorize with this URL:\n")
    print(auth_url)

    if get_bool_env("TIKTOK_OPEN_BROWSER", default=True):
        webbrowser.open(auth_url)

    print("\nAfter login, paste the FULL callback URL:")
    callback_url = input("> ").strip()
    if not callback_url:
        raise RuntimeError("No callback URL provided.")
    return callback_url


def main() -> int:
    load_dotenv(Path(".env"))

    try:
        client_key = require_env("TIKTOK_CLIENT_KEY")
        client_secret = require_env("TIKTOK_CLIENT_SECRET")
        redirect_uri = require_env("TIKTOK_REDIRECT_URI")
    except ValueError as exc:
        print(exc)
        print("Create a .env file (or set env vars) before running this script.")
        return 1

    scope = os.getenv("TIKTOK_SCOPES", "user.info.basic").strip() or "user.info.basic"
    disable_auto_auth = os.getenv("TIKTOK_DISABLE_AUTO_AUTH")
    token_path = Path(os.getenv("TIKTOK_TOKEN_PATH", "tiktok_tokens.json"))
    callback_timeout = int(os.getenv("TIKTOK_CALLBACK_TIMEOUT_SECONDS", "180"))

    state = secrets.token_urlsafe(24)
    auth_url = build_auth_url(
        client_key=client_key,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        disable_auto_auth=disable_auto_auth,
    )

    try:
        if is_local_redirect_uri(redirect_uri):
            callback_url = capture_code_via_local_callback(redirect_uri, auth_url, callback_timeout)
        else:
            callback_url = capture_code_manually(auth_url)
    except RuntimeError as exc:
        print(exc)
        return 1

    code, returned_state, auth_error = parse_callback_url(callback_url)

    if auth_error:
        print(f"TikTok returned an authorization error: {auth_error}")
        return 1

    if returned_state != state:
        print("State mismatch. Possible CSRF risk. Aborting token exchange.")
        return 1

    if not code:
        print("Could not find authorization code in callback URL.")
        return 1

    try:
        token_data = exchange_code_for_token(
            client_key=client_key,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )
    except RuntimeError as exc:
        print(exc)
        return 1

    if "access_token" not in token_data or "refresh_token" not in token_data:
        print("Token response did not include expected tokens.")
        print(json.dumps(token_data, indent=2))
        return 1

    persist_tokens(token_data, token_path)

    print("\nWorkflow complete:")
    print("User -> TikTok Login -> Authorization Code -> Access Token + Refresh Token")
    print("Tokens saved to:", token_path.resolve())
    print("Access token expires in:", token_data.get("expires_in", "(unknown)"), "seconds")
    print("Refresh token expires in:", token_data.get("refresh_expires_in", "(unknown)"), "seconds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
