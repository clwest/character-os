---
title: "Trust Calibration Log"
status: active
---

# Trust Calibration Log

Append-only ledger of AI ↔ human calibration events. See
[`docs-pattern/08_collaboration_roles.md`](docs-pattern/08_collaboration_roles.md)
for why this exists.

Three event types:

- **AI confidently wrong** — AI asserted something with confidence; turned out false.
- **AI right despite pushback** — AI raised a concern, human was skeptical, AI was right.
- **Near-miss** — human nearly approved something the AI later caught.

Keep both sides of the ledger. One-sided logs recalibrate trust in the wrong direction.

---

## Format

```markdown
## YYYY-MM-DD — <event type>: <one-line headline>

- **Context / claim:** <what the AI said or human was about to approve>
- **Reality / outcome:** <what turned out to be true>
- **Found by:** <verifier, test run, staging, reviewer>
- **Lesson:** <one-line calibration takeaway for future sessions>
```

---

## Log

## 2026-05-13 — AI right to flag, operator right to escalate: Celery pulled into Phase 2

- **Context / claim:** SESSION 109 started with the AI flagging a
  fire-then-poll design question for the video pipeline and
  recommending a **thread-helper middle path** (Django daemon
  thread polls the media-engine, writes back to the row). The
  AI's reasoning was "defers Celery to Phase 4 as originally
  planned." The AI also surfaced the real tradeoff: the thread
  approach is not crash-safe — a Django restart loses the polling
  thread.
- **Reality / outcome:** Operator said *"bring it in now, so we
  already have it as the project is merging and growing."*
  Celery + Redis landed in SESSION 109 as the foundation. Cost
  was ~80 lines of config + a docker-compose service + 2 new
  Python deps. SESSION 110's voice clone slice didn't need
  Celery, but the next async surface (video kinds 2-4,
  embeddings, scheduled tasks) will — landing it once costs less
  than retrofitting later.
- **Found by:** Operator judgement during the SESSION 109 design
  call.
- **Lesson:** When the AI proposes "smallest thing now" vs.
  "real foundation now," and the foundation is **clearly going
  to be needed within 1-3 sessions**, default to the real
  foundation rather than the smallest thing. The thread-helper
  middle path was technically correct as a Phase 2 minimum, but
  the operator's intuition that "this will become tech debt
  fast" was right. **For this operator specifically:** when
  scope expansion costs <1 session of work and saves a future
  retrofit, lean toward expanding.
