# Creator Analytics Platform

Multi-Platform Video Intelligence Dashboard for **YouTube + TikTok + Instagram**.

## Overview

Creator Analytics Platform is a scalable web-based analytics system for creators and agencies to track, analyze, and optimize content performance across short-form and long-form video platforms.

It aggregates platform data from:
- YouTube Data API v3
- YouTube Analytics API
- TikTok for Developers API
- Instagram Graph API

The platform provides a single dashboard for video performance, audience behavior, and growth trends.

## Problem Statement

Today, creators and teams often:
- Manually switch between multiple platform dashboards
- Lack unified cross-platform insights
- Struggle to identify which content performs best
- Spend significant time collecting and comparing analytics

This platform automates that workflow and surfaces actionable insights in one place.

## Key Features

### Unified Dashboard
- Cross-platform analytics (YouTube, TikTok, Instagram)
- Centralized performance view

### Video-Level Insights
- Views, likes, comments, shares
- Engagement rate calculation
- Watch time and retention

### Audience Analytics
- Region distribution
- Age and gender breakdowns
- Audience behavior trends

### Growth and Trend Intelligence
- Daily performance tracking
- Viral content detection
- Top-performing content discovery

### Scalable Data Pipeline
- Designed to handle 100K+ videos
- Automated data ingestion and metric updates

## High-Level Architecture

```text
Frontend (React)
        |
Backend API (FastAPI)
        |
Queue System (Amazon SQS)
        |
Worker Services
        |
Platform APIs (YouTube + TikTok + Instagram)
        |
PostgreSQL (RDS) + Redis (Cache)
```

## Authentication

OAuth 2.0 is used across all supported platforms:
- YouTube -> Google OAuth
- TikTok -> TikTok OAuth
- Instagram -> Meta OAuth

Tokens are stored securely and refreshed automatically for continuous data sync.

## Data Pipeline Workflow

```text
Scheduler (Cron / Lambda)
        |
Fetch Video List (Incremental)
        |
Queue Jobs (Per Video)
        |
Workers Fetch Analytics
        |
Store in Database
        |
Precompute Metrics
        |
Serve via API
        |
Render Dashboard
```

## Database Design (Core Entities)

### `videos`
- `id`
- `platform`
- `title`
- `publish_date`

### `metrics_daily`
- `video_id`
- `date`
- `views`
- `likes`
- `comments`
- `shares`
- `watch_time`

### `audience_data`
- `video_id`
- `region`
- `age`
- `gender`

## Analytics Computation

Key computed metrics:

- **Engagement Rate**: `(likes + comments + shares) / views`
- **Growth Rate**: Daily change in views
- **Top Content Ranking**: Weighted by engagement and watch time

## Tech Stack

### Backend
- FastAPI
- Python

### Frontend
- React

### Cloud and Infrastructure
- AWS Lambda
- Amazon SQS
- Amazon RDS (PostgreSQL)
- Redis

## Repository Structure

```text
creator_analytics/
├─ apps/
│  └─ frontend/                   # React dashboard app
├─ services/
│  ├─ api/                        # FastAPI backend (unified analytics API)
│  │  ├─ src/creator_analytics_api/
│  │  └─ tests/
│  ├─ worker-tiktok/              # TikTok ingestion worker (current implementation)
│  │  ├─ src/tiktok_analytics/
│  │  ├─ scripts/
│  │  └─ tests/
│  └─ worker-analytics/           # Cross-platform metric computation worker
│     ├─ src/worker_analytics/
│     └─ tests/
├─ packages/
│  └─ shared-python/
│     ├─ src/creator_shared/      # Shared models/utilities
│     └─ tests/
├─ infra/
│  ├─ terraform/
│  │  ├─ environments/dev/
│  │  ├─ environments/prod/
│  │  └─ modules/
│  └─ aws/
├─ docs/
│  ├─ architecture/
│  └─ api/
├─ tests/
│  └─ integration/
├─ scripts/                       # Root helper scripts for local runs
└─ configs/                       # Environment-specific app configs
```

## Deployment Architecture

```text
CloudFront (Frontend Hosting)
        |
API Gateway
        |
Backend (Lambda / ECS)
        |
SQS Queue
        |
Worker Services
        |
Amazon RDS (PostgreSQL) + Redis
```

## Project Goal

Build a reliable, scalable intelligence layer for creator businesses so teams can move from manual reporting to real-time, data-driven content decisions.
