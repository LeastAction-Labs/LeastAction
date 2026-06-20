# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
#
# Lifecycle stage: 09_platform_integration  |  Flavor: KB (how-to-use, multi-service flow)
# How to USE YouTube + Gemini together: fetch new comments -> Gemini drafts a reply -> post the reply.
# Authored originally. Operators generated from the Google YouTube + Gemini skill.
payloads = {}

skills = {
    "00_youtube_gemini_responder.md": """\
# How to build a YouTube comment auto-responder with Gemini

A flow that fetches new comments from the **YouTube Data API**, drafts a context-aware reply with
**Gemini**, and posts it back — each step a LeastAction task chained with `LeastActionCheckIfParentsAreDone`.

> No operators ship in core for this. The agent **generates** them from the
> **`Google_youtube_gemini_comment_responder.md`** skill (YouTube auth/endpoints + Gemini call) via Operator
> Dev, then wires the flow. Knowledge lives in the skill; the flow lives here.

## Prerequisites
- A Google `connection` with YouTube Data API credentials (OAuth 2.0 with comment write scope) and a Gemini
  API key.
- Generated operators (from the skill): "list new comments", "Gemini generate reply", "post comment reply".
  `LeastActionCheckIfParentsAreDone` for ordering.

## The flow
| Step | Generated operator | Does |
|---|---|---|
| 0 `fetch_new_comments` | YouTube list comment threads | Pull comments newer than the last watermark for the channel/video |
| 1 `draft_replies` | Gemini generate | For each comment, draft a reply using the video + comment as context |
| 2 `post_replies` | YouTube insert comment reply | Post the approved/auto replies back to YouTube |

Step 0 has no pre-action; steps 1-2 chain via `LeastActionCheckIfParentsAreDone`. Track a per-channel
comment watermark so each run only handles new comments (idempotent — never double-reply).

## Guardrails (important)
- **Human-in-the-loop option:** land drafted replies for review (a `pending-approval` folder + the
  `leastaction-reporting-approval` pattern) before posting, for sensitive channels.
- **Rate/quota:** respect YouTube write quota; back off on errors (see `leastaction-pipelines-retry`).
- **Idempotency:** the watermark + a "replied" flag prevents duplicate replies on re-run.

## Deploy
> "use the google-youtube-gemini-responder usecase to auto-draft Gemini replies to new comments (review before posting)"
"""
,
}

prompt = (
    "How to use YouTube + Gemini together in LeastAction: fetch new comments from the YouTube Data API (newer "
    "than a watermark), draft context-aware replies with Gemini, and post them back via the YouTube API. "
    "Steps chain via LeastActionCheckIfParentsAreDone; a per-channel watermark + replied flag makes it "
    "idempotent (no double-replies). Supports a human-in-the-loop review step (leastaction-reporting-approval) "
    "and quota back-off (leastaction-pipelines-retry). No operators ship in core, so the agent generates them "
    "from the Google_youtube_gemini_comment_responder skill."
)

description = (
    "Platform Integration (how-to-use): a YouTube comment auto-responder — fetch new comments -> Gemini drafts "
    "a reply -> post back — as chained LeastAction tasks, idempotent via a watermark, with an optional "
    "human-review gate. Operators generated from the Google YouTube + Gemini skill."
)

guide_docs = """\
# YouTube + Gemini Comment Responder (how-to-use)

**Lifecycle stage:** Platform Integration. **Flavor:** knowledge bundle — the agent reads the flow,
generates the YouTube + Gemini operators from the skill, and implements it.

## The flow
YouTube (new comments since watermark) -> Gemini (draft reply) -> YouTube (post reply), chained via
`LeastActionCheckIfParentsAreDone`, idempotent via a watermark + replied flag.

## Prerequisites
- A Google `connection` (YouTube OAuth with write scope + Gemini key); reference skill
  `Google_youtube_gemini_comment_responder.md` (operators generated from it — none ship in core).

## Using
> "use the google-youtube-gemini-responder usecase to auto-reply to new comments, with review before posting"

Add a human-review gate via `leastaction-reporting-approval`; add quota back-off via
`leastaction-pipelines-retry`.
"""

publisher = "LeastAction"

metadata = {
    "service": "YouTube, Gemini",
    "category": "Platform Integration",
    "tags": ["flavor:KB", "lifecycle:platform-integration", "how-to-use", "google", "youtube", "gemini", "automation", "ai"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
