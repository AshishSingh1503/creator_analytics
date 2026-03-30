import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .db import get_connection, init_db


def _render_page(conn) -> str:
    latest_metrics = conn.execute(
        "SELECT * FROM daily_metrics ORDER BY metric_date DESC LIMIT 30"
    ).fetchall()
    latest_alerts = conn.execute(
        "SELECT * FROM alerts ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    top_videos = conn.execute(
        """
        SELECT v.video_id, v.title, a.view_count, a.like_count, a.comment_count, a.share_count, a.fetched_at
        FROM video_analytics a
        JOIN videos v ON v.video_id = a.video_id
        WHERE a.fetched_at = (SELECT MAX(fetched_at) FROM video_analytics)
        ORDER BY a.view_count DESC
        LIMIT 20
        """
    ).fetchall()

    metrics_parts = []
    for r in latest_metrics:
        growth_value = r["views_growth_pct"]
        growth_text = "" if growth_value is None else f"{float(growth_value):.2f}%"
        metrics_parts.append(
            "<tr>"
            f"<td>{html.escape(r['metric_date'])}</td>"
            f"<td>{r['total_videos']}</td>"
            f"<td>{r['total_views']}</td>"
            f"<td>{r['total_likes']}</td>"
            f"<td>{r['total_comments']}</td>"
            f"<td>{r['total_shares']}</td>"
            f"<td>{float(r['avg_views_per_video']):.2f}</td>"
            f"<td>{growth_text}</td>"
            "</tr>"
        )
    metrics_rows = "".join(metrics_parts)

    alert_rows = "".join(
        f"<tr><td>{html.escape(r['created_at'])}</td><td>{html.escape(r['level'])}</td><td>{html.escape(r['message'])}</td></tr>"
        for r in latest_alerts
    )

    video_rows = "".join(
        f"<tr><td>{html.escape(r['video_id'])}</td><td>{html.escape(r['title'] or '')}</td><td>{r['view_count']}</td><td>{r['like_count']}</td><td>{r['comment_count']}</td><td>{r['share_count']}</td></tr>"
        for r in top_videos
    )

    return f"""
    <html>
    <head>
      <title>TikTok Analytics Dashboard</title>
      <style>
        body {{ font-family: Segoe UI, sans-serif; margin: 24px; background: #f4f6f8; color: #222; }}
        h1, h2 {{ margin-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; background: #fff; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 13px; }}
        th {{ background: #f0f0f0; text-align: left; }}
      </style>
    </head>
    <body>
      <h1>TikTok Analytics Dashboard</h1>
      <h2>Daily Metrics</h2>
      <table>
        <tr><th>Date</th><th>Videos</th><th>Views</th><th>Likes</th><th>Comments</th><th>Shares</th><th>Avg Views/Video</th><th>Views Growth</th></tr>
        {metrics_rows}
      </table>

      <h2>Top Videos (Latest Snapshot)</h2>
      <table>
        <tr><th>Video ID</th><th>Title</th><th>Views</th><th>Likes</th><th>Comments</th><th>Shares</th></tr>
        {video_rows}
      </table>

      <h2>Alerts</h2>
      <table>
        <tr><th>Created At</th><th>Level</th><th>Message</th></tr>
        {alert_rows}
      </table>
    </body>
    </html>
    """


def run_dashboard(db_path: Path, host: str, port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/api/health":
                body = json.dumps({"ok": True}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
                return

            conn = get_connection(db_path)
            init_db(conn)
            try:
                page = _render_page(conn)
            finally:
                conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page.encode("utf-8"))

        def log_message(self, format: str, *args) -> None:
            return

    server = HTTPServer((host, port), Handler)
    print(f"Dashboard running at http://{host}:{port}")
    server.serve_forever()
