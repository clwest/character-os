# Knowledge Snapshots — SESSION 271 read-only export

Captured 2026-08-20 for upload to ChatGPT in the SESSION 271 knowledge-shape design conversation.

## Files

| File | Character | Documents included | Chars |
|---|---|---|---|
| `patch_knowledge.md` | Patch (`7fad8172`) | Personal (`fd0ba2ca`) + Shared canon (`f309469c`) | ~14040 |
| `rivet_knowledge.md` | Rivet (`f18b75cc`) | Personal (`218eb0d8`) + Shared canon (`f309469c`) | ~8567 |

## Purpose

Support the design conversation about candidate **Q-270-19** — knowledge-document rewrite to include audience-accessible translations alongside the raw technical vocabulary. The SESSION 271 knowledge audit (`docs/design/SESSION_271_CORRECTIVE_PASS_AUDIENCE_INVARIANCE_AUDIT.md` §81) found that the retrieved knowledge chunks provide the model with only raw technical vocabulary (`call APIs`, `maintain state`, `language model`, `databases`) and zero accessible alternatives — framed as *"WHAT PATCH KNOWS ABOUT AI."*

## Scope

- Only `KnowledgeDocument.raw_content` is included — NOT Teammate persona fields (business_brief / personality / character_point_of_view / who_you_help / what_you_sell / voice_* / never_say / always_emphasize / opener). Those live on `apps.spokespeople.Teammate` and feed into §2 Character Voice + §3 Brand Voice of the assembled prompt (SESSION 253 architecture).
- NarrativeMemory content is NOT included (pool state remains 14 remembered + 1 archived).
- Universe-canon retrieval pathway is available but currently empty for Patch's Workshop per SESSION 263 §6.8 corpus census.

## Provenance

Extracted from live `local-real` Postgres via `manage.py shell`, exported to markdown by Claude. Source-of-truth reference points to the specific `KnowledgeDocument.id` UUIDs.
