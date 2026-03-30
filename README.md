# TikTok Analytics

End-to-end TikTok analytics pipeline:

`[Auth Done] -> [Store Tokens] -> [Scheduler (Daily)] -> [Refresh Token] -> [Fetch Video List] -> [Fetch Analytics] -> [Store Data] -> [Process Metrics] -> [Dashboard + Alerts]`

## Full Workflow

1. **Auth Done**
   Run OAuth once to get `access_token` + `refresh_token`.

2. **Store Tokens**
   Tokens are stored in `tiktok_tokens.json` and synced into SQLite `tokens` table.

3. **Scheduler (Daily)**
   Scheduler runs pipeline every day at `TIKTOK_SCHEDULE_TIME`.

4. **Refresh Token**
   Before API calls, access token is refreshed automatically when near expiry.

5. **Fetch Video List**
   Pull videos using TikTok list endpoint with pagination.

6. **Fetch Analytics**
   Pull detailed stats (views/likes/comments/shares) using query endpoint.

7. **Store Data**
   Save normalized data into SQLite (`videos`, `video_analytics`, `pipeline_runs`).

8. **Process Metrics**
   Build daily aggregates in `daily_metrics` and compute day-over-day growth.

9. **Dashboard + Alerts**
   Serve dashboard and generate alerts from configured thresholds.

## Project Structure

- `tiktok_oauth_auth.py` - OAuth 2.0 login + authorization code exchange.
- `src/tiktok_analytics/config.py` - environment/config loader.
- `src/tiktok_analytics/db.py` - SQLite schema + init.
- `src/tiktok_analytics/token_store.py` - token persistence + refresh checks.
- `src/tiktok_analytics/tiktok_api.py` - TikTok API client.
- `src/tiktok_analytics/pipeline.py` - full pipeline orchestration.
- `src/tiktok_analytics/scheduler.py` - daily scheduler loop.
- `src/tiktok_analytics/dashboard.py` - dashboard HTTP server.
- `scripts/run_pipeline.py` - run one pipeline cycle.
- `scripts/run_scheduler.py` - run daily scheduler.
- `scripts/run_dashboard.py` - start dashboard.

## First-Time Setup

1. Create `.env` from `.env.example` and fill required values.
2. Run OAuth once:

```bash
python tiktok_oauth_auth.py
```

3. Run first pipeline manually:

```bash
python scripts/run_pipeline.py
```

4. Start dashboard:

```bash
python scripts/run_dashboard.py
```

Open: `http://127.0.0.1:8050` (or configured host/port).

## Daily Operation

Run scheduler process (keep it running in background/server):

```bash
python scripts/run_scheduler.py
```

Scheduler behavior:
- waits until `TIKTOK_SCHEDULE_TIME`
- runs full pipeline
- logs success/failure in `pipeline_runs`
- persists refreshed tokens and new analytics snapshots

## Environment Variables

Required:
- `TIKTOK_CLIENT_KEY`
- `TIKTOK_CLIENT_SECRET`
- `TIKTOK_REDIRECT_URI`

Auth-related:
- `TIKTOK_SCOPES` (default: `user.info.basic,video.list`)
- `TIKTOK_DISABLE_AUTO_AUTH` (`0` or `1`)
- `TIKTOK_OPEN_BROWSER` (`true`/`false`)
- `TIKTOK_CALLBACK_TIMEOUT_SECONDS` (default: `180`)
- `TIKTOK_TOKEN_PATH` (default: `tiktok_tokens.json`)

Pipeline:
- `TIKTOK_DB_PATH` (default: `data/tiktok_analytics.db`)
- `TIKTOK_VIDEO_PAGE_LIMIT` (default: `5`)
- `TIKTOK_VIDEO_PAGE_SIZE` (default: `20`)
- `TIKTOK_REFRESH_BUFFER_SECONDS` (default: `300`)

Scheduler + Dashboard:
- `TIKTOK_SCHEDULE_TIME` (default: `03:30`)
- `DASHBOARD_HOST` (default: `127.0.0.1`)
- `DASHBOARD_PORT` (default: `8050`)

Alerts:
- `ALERT_MIN_TOTAL_VIEWS` (default: `100`)
- `ALERT_GROWTH_DROP_PERCENT` (default: `30`)

## Data Storage

SQLite DB (default: `data/tiktok_analytics.db`) tables:
- `tokens`
- `videos`
- `video_analytics`
- `daily_metrics`
- `alerts`
- `pipeline_runs`

## Alerts

Implemented rules:
- Warning if daily total views `< ALERT_MIN_TOTAL_VIEWS`
- Critical if day-over-day views drop by `>= ALERT_GROWTH_DROP_PERCENT`

## Troubleshooting

- **No token found**
  Run `python tiktok_oauth_auth.py` first.

- **State mismatch during auth**
  Restart auth flow and ensure callback URL is from same login attempt.

- **Token refresh failure**
  Re-run OAuth to issue fresh tokens.

- **Empty analytics**
  Verify app scopes/permissions in TikTok Developer Portal and update `TIKTOK_SCOPES`.

## Security Notes

- Never commit `.env` or token files.
- Rotate client secret if exposed.
- Keep redirect URI exactly matched between `.env` and TikTok app settings.
