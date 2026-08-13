# Case Study 06 — Allauth `RATE_LIMITS = False` (AI miscalibration)

**Date:** SESSION 131.
**Systems:** Django settings, `django-allauth`, Playwright e2e.

## Problem

The Playwright e2e suite was hitting `django-allauth`'s default
signup rate limit (20/minute) during test runs. Multiple test
files created accounts within the same minute, and after the
20th account the suite began failing with 429s.

The fix should be one line in Django settings.

## Evidence

- Playwright suite intermittent failures on signup step.
- Manual inspection of allauth response showed 429 rate-limit
  errors.
- Same tests passed one-at-a-time; failed when run together.

## The AI's proposal

Claude Code proposed:

```python
ACCOUNT_RATE_LIMITS = {}
```

Rationale (paraphrased): "The dict of rate limits is empty, so
allauth has nothing to enforce."

Confidence in the proposal: high — the shape is natural, the
naming matches allauth's convention.

## What actually happened

Applied the setting. Tests still failed.

## Root cause

`django-allauth`'s `app_settings.RATE_LIMITS` merges user
overrides with library defaults. An empty dict override merges
with the defaults (`{login: "5/m", ...}`) to produce the
default set unchanged. The setting had zero effect.

The correct disable value is `ACCOUNT_RATE_LIMITS = False` —
which allauth interprets as "disable rate limiting entirely",
not as a dict shape at all.

## Decision

- Fix the setting.
- Log the miscalibration in `TRUST_CALIBRATION.md` — the AI's
  proposal was structurally reasonable but empirically wrong.
- Codify a pattern: when a library's override shape is not
  clearly documented, verify the actual behavior in a REPL
  before trusting the natural shape.

## Implementation change

```python
# shell/character_os/settings.py
ACCOUNT_RATE_LIMITS = False
```

Verified via:

```bash
python -c "from allauth.account import app_settings; print(app_settings.RATE_LIMITS)"
```

which now returns the empty / disabled state instead of the
merged defaults.

## Verification

Playwright suite ran cleanly through 40+ signups.
`TRUST_CALIBRATION.md` picked up the entry as an "AI-assumed
shape ≠ library-actual shape" example.

## Lasting rule

**When AI-proposed configuration matches the "natural" shape
but the library isn't documented on that behavior, verify in a
REPL before shipping.** The natural shape is often wrong for
libraries that predate current API conventions. `False` vs `{}`
vs `None` for disable-toggle settings is a common trap.

This is a small case study, but it's the shape of many
AI-assisted development corrections: the AI's answer looked
right, ran without error, and did nothing useful. Only a
runtime check caught it.
