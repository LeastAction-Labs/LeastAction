# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 09_platform_integration  |  Flavor: KB (how-to-use, multi-service flow)
# How to USE the YouTube Data API in LeastAction: fetch channel videos + analytics + comments -> store ->
# report. Authored originally. Operators generated from the Google YouTube skill.
payloads = {}

skills = {
    "00_youtube_engagement.md": """\
# How to build a YouTube engagement reporting pipeline

A scheduled flow that pulls channel performance from the **YouTube Data API** (videos, view/like/comment
counts, recent comments), lands it, and renders an engagement report — each step a LeastAction task chained
with `LeastActionCheckIfParentsAreDone`.

> No YouTube operators ship in core. The agent **generates** them from the **`Google_youtube.md`** skill
> (auth, endpoints, quota) via Operator Dev, then wires this flow. Knowledge lives in the skill; the flow here.

## Prerequisites
- A Google `connection` with YouTube Data API credentials (OAuth 2.0 / API key as the skill describes).
- Generated operators (from `Google_youtube.md`): a "list channel videos + stats" op and a "list comments"
  op; a sink (DB/`html_report`). `LeastActionCheckIfParentsAreDone` for ordering.

## The flow
| Step | Generated operator | Does |
|---|---|---|
| 0 `fetch_videos` | YouTube list videos + statistics | Pull the channel's videos with view/like/comment counts for the window |
| 1 `fetch_comments` | YouTube list comment threads | Pull recent comments per video (respect API quota / pagination) |
| 2 `store` | PostgreSQL (or warehouse) insert | Land videos + comments into tables stamped `{{logical_date}}` (idempotent) |
| 3 `report` | `PostgresqlGenerateHtmlTableReport` (or AI report) | Render an engagement dashboard and publish it to the catalog |

Step 0 has no pre-action; steps 1-3 chain via `LeastActionCheckIfParentsAreDone`. Carry `{{logical_date}}`
so each run is a dated snapshot (and backfillable).

## Notes
- **Quota:** the YouTube Data API is quota-limited — page results and avoid refetching unchanged data
  (track a per-video watermark). See `Google_youtube.md`.
- Make step 2 idempotent (delete-the-day-slice then insert) so re-runs are safe.

## Verify
`inspect_data` on the comments/videos tables for `{{logical_date}}`; open the published report.

## Deploy
> "use the google-youtube-engagement usecase to pull my channel stats daily and publish an engagement report"
"""
,
}

prompt = (
    "How to use the YouTube Data API as a LeastAction pipeline: fetch channel videos + statistics and recent "
    "comment threads (paged, quota-aware), land them idempotently into tables stamped {{logical_date}}, and "
    "render an engagement report via PostgresqlGenerateHtmlTableReport (or an AI report). Steps chain via "
    "LeastActionCheckIfParentsAreDone. No YouTube operators ship in core, so the agent generates them from the "
    "Google_youtube skill (OAuth, endpoints, quota)."
)

description = (
    "Platform Integration (how-to-use): a YouTube engagement reporting pipeline — fetch videos/stats/comments "
    "from the YouTube Data API, store, and report — as chained LeastAction tasks. Operators generated from the "
    "Google YouTube skill."
)

guide_docs = """\
# YouTube Engagement Reporting (how-to-use)

**Lifecycle stage:** Platform Integration. **Flavor:** knowledge bundle — the agent reads the flow,
generates the YouTube operators from `Google_youtube.md`, and implements it.

## The flow
YouTube Data API (videos+stats, comments) -> store (idempotent, `{{logical_date}}`) -> report, chained via
`LeastActionCheckIfParentsAreDone`. Mind API quota (page + watermark).

## Prerequisites
- A Google `connection` with YouTube API creds; reference skill `Google_youtube.md` (operators generated
  from it — none ship in core); a report operator for the output.

## Using
> "use the google-youtube-engagement usecase to publish a daily engagement report for my channel"

For auto-responding to comments with Gemini, see `google-youtube-gemini-responder`.
"""

publisher = "LeastAction"

metadata = {
    "service": "YouTube",
    "category": "Platform Integration",
    "tags": ["flavor:KB", "lifecycle:platform-integration", "how-to-use", "google", "youtube", "engagement", "reporting"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
