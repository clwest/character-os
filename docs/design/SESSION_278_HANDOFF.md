# SESSION 278 — Handoff (from SESSION 277)

## Status at the top

- SESSION 277 is **CLOSED**.
  - Closeout ref: `docs/design/SESSION_277_OPERATOR_KNOWLEDGE_DOGFOOD.md` §283 (closeout marker).
  - Full evidence: same document, ~6,700 lines across 13 primary slices + hot-fix + verification passes.
- Real-DB state at closeout (verified read-only): 3 KnowledgeDocuments in Chris's workspace (all in Fox & Flour Bakery); 2 Universes (Fox & Flour Bakery, Patch's Workshop); 9 teammates (4 Universe-bound, 5 legacy `universe=NULL`).
- Slice 13.1 verification remains intact; nothing has been mutated during closeout.

**Purpose of this document:** compact self-contained orientation for a fresh SESSION 278 Claude + ChatGPT so neither has to re-read all of SESSION 277 to resume work.

---

## §1 Current product model (as of 2026-08-22)

```
Workspace                                       [tenant / ownership / security]
  ├── World A (Universe)                        [semantic/creative container]
  │     ├── shared World brief (Universe.brief) [compact identity — always in synthesis]
  │     ├── shared World Knowledge (KDs)        [detailed facts; retrieval-ranked]
  │     ├── Characters (Teammates)
  │     │    ├── character identity (name / personality / voice)
  │     │    ├── legacy business_brief          [historical; overlap with World]
  │     │    └── character-specific Knowledge   [scoped by CHARACTER audience + M2M]
  │     ├── Episodes                            [Universe-scoped stories]
  │     └── Narrative memory                    [Universe-scoped continuity]
  ├── World B (Universe)
  │     ...
  └── legacy pool                               [universe=NULL teammates + legacy KDs]
```

### Workspace
- **Load-bearing role:** tenant / ownership / security boundary. Every content model FKs Workspace with NOT NULL + CASCADE. Every viewset filters by `workspace__memberships__user`.
- **NOT** the ordinary business/world concept in the current product model.
- One operator Workspace can contain multiple unrelated Worlds.
- **Workspace-wide character Knowledge** (`audience_scope=WORKSPACE`) is not an ordinary default audience. It is preserved for compatibility but is not exposed in any contextual character-origin or World-origin flow. It exists behind the generic `/workspace/knowledge` `UniverseScopePicker`'s "None (legacy)" gesture for the dashboard/nav-rail path. Do not resurrect it as the normal business-sharing mechanism.

### World / Universe
- **Backend name:** `Universe` (app: `shell/apps/universe/`). **Operator-facing name:** "World".
- A World is the persistent semantic/business/creative context containing its characters, shared Knowledge, Episodes, and memory.
- **Ordinary new characters require explicit World membership** (SESSION 261 substrate + Slice 5 wizard invariant). The SPA wizard has a mandatory World picker with inline "+ Create new World".
- **Legacy `universe=NULL` teammates still exist** (5 in Chris's workspace) and were intentionally not migrated during SESSION 277. They remain functional under compatibility branches but are structurally excluded from Universe-aware features (Episodes, NarrativeMemory, UNIVERSE-audience Knowledge, canon lane).
- Do not casually weaken the World-required-at-create boundary in future work.

### Character
- Character identity/personality belongs to the character (`Teammate.personality`, `Teammate.tone_archetype`, `Teammate.voice_*`, `Teammate.character_point_of_view`).
- Shared business/world truth should NOT need to be duplicated into every character.
- `Teammate.business_brief` historically carried both character AND business/world meaning because it predates Universe by ~3 months (SESSION 107 vs SESSION 261).
- SESSION 277 began separating those responsibilities by introducing `Universe.brief` and by validating multi-character Worlds (Ruby + Tyson) end-to-end.
- Do not assume existing legacy briefs represent the desired future authoring model. They are compatibility substrate.

### World identity
- **`Universe.brief`** is the compact shared identity every character in the World inherits during synthesis. Deterministically injected into every synthesis path (script / dialogue / claim verifier / teammate ask / conversation) as a `WORLD SHAPE:` block. 2000-char cap; blank remains valid.
- **`Universe.description`** (DB column name unchanged) is now operator-visible as "Operator notes (optional)". Private operator reference. **Not consumed by synthesis.** Preserve the distinction.
- **World brief ≠ Knowledge.** Critical architectural distinction — see §3.

### Knowledge
- Knowledge has an explicit audience model. Three DB values: CHARACTER, UNIVERSE, WORKSPACE, plus NONE (fail-closed for orphans).
- **The two ordinary useful audiences established in SESSION 277:**
  - **Character-specific** — one or more spokespeople scoped by CHARACTER audience + M2M.
  - **Shared with a World** — UNIVERSE audience, all characters in that World.
- **Workspace-wide Knowledge is exceptional / advanced**, not the normal business-sharing mechanism.
- **The Knowledge UI now asks "Who should know this?"** (in contextual character-origin mode) rather than exposing internal scope semantics. In World-origin mode the audience is implied by the origin and no question is asked.
- Contextual character AND World origins should preserve what is already known and ask only for what remains unknown.

---

## §2 Contextual navigation product rule (supported, not universal)

> **"Carry forward what the operator has already told us; ask only for what remains unknown."**

**Evidence boundary — tested at three substrates:**
- **Character-origin handoff** (`/spokespeople/:id/welcome`, character-detail KnowledgePanel) → World preserved + character preserved + audience genuinely unknown → operator asked "Who should know this? (Everyone in {World} / Just {Character})". Neither preselected.
- **World-origin handoff** (`/workspace/universes/:id` "Add shared knowledge" button) → World preserved + audience implied by origin (UNIVERSE) → no audience question. CHARACTER option not exposed at all.
- **Generic / no-context** (dashboard / nav rail → `/workspace/knowledge`) → nothing preserved → operator explicitly picks a scope via the pre-Slice-12 `UniverseScopePicker`.

**Status:** SUPPORTED as a product-navigation rule within these three substrates. **NOT** declared a universal invariant for every future origin. Any future Knowledge-adjacent origin (Episode origin, Transcript origin, Composition origin, etc.) should independently test its own known/unknown split before adopting this rule blindly.

---

## §3 The architectural distinction that must not be lost

**World brief** vs **Knowledge** vs **Character brief** — one of the major product-model discoveries of SESSION 277.

| Layer | Storage | Consumed by | Character owns? | World owns? | Purpose |
|---|---|---|---|---|---|
| **World brief** | `Universe.brief` (TextField, 2000 chars) | Every synthesis path as a deterministic `WORLD SHAPE:` block | no | **yes** | Compact shared identity every character in the World inherits |
| **World Knowledge** | KDs with `audience_scope=UNIVERSE` + `universe_id=<uuid>` + empty M2M | Retrieved by cosine when relevant to the query | no | **yes** | Detailed facts / menus / pricing / policies / procedures / expertise — shared across all characters in the World |
| **Character-specific Knowledge** | KDs with `audience_scope=CHARACTER` + `universe_id=<uuid>` + M2M `[<sp>]` | Retrieved by cosine — only for the M2M spokesperson | **yes** | no | Character-private facts / expertise / preferences |
| **Character identity** | `Teammate.personality`, `Teammate.tone_archetype`, `Teammate.voice_*`, `Teammate.character_point_of_view` | Every synthesis path as a deterministic `CHARACTER VOICE` block | **yes** | no | Character-specific role, voice, mannerisms, POV |
| **Legacy character `business_brief`** | `Teammate.business_brief` (TextField) | Every synthesis path as a deterministic `BUSINESS SHAPE:` block | historically mixed | historically mixed | Historical residue — carries both character AND World meaning because it predates Universe; treat as compatibility substrate |
| **Operator notes** | `Universe.description` (DB column; operator label "Operator notes (optional)") | **Nothing.** Not consumed by synthesis. | no | no (private) | Operator reference — audit notes, reminders, private context |

**Do not conflate these layers.** World brief is compact + deterministic; Knowledge is detailed + retrievable; character brief is (mostly) character-personal. Universe.description is a private operator note that has no effect on synthesis.

---

## §4 Current operator flows

### A. Fresh character creation
1. Dashboard → **New spokesperson**.
2. Wizard Step 1: fill Name + Brief; **required World picker** (existing World select OR inline "+ Create new World" with a compact create form asking only for name).
3. Wizard Steps 2-4: portrait, voice, confirm. Submit creates the character bound to the chosen World.
4. Welcome page: "Meet {name}." Primary CTA **"Teach {name} about your business"** routes to `/workspace/knowledge?universe=<uuid>&spokesperson=<uuid>&origin=character_welcome`.
5. Contextual destination renders: "Teach {name} in {World}. Pick who should know this before adding content." Two audience options — **Everyone in {World}** or **Just {name}** — neither preselected. Ingest tabs appear after audience is picked.
6. Submit produces the expected payload (§7 hot-fix note).

### B. World detail
1. Dashboard → Worlds → **{World name}** (e.g. Fox & Flour Bakery).
2. Page defaults to a readable **Overview** — World name as heading, `Universe.brief` as prose ("What is this World?"), Operator notes shown only when populated.
3. Explicit **Edit** button reveals a form: Name + "What is this World?" + "Operator notes (optional)". Save / Cancel return to Overview.
4. Overview also carries an **"Add shared knowledge"** button. Clicking routes to `/workspace/knowledge?universe=<uuid>&origin=world_detail_add_knowledge`.
5. Contextual destination renders: "Add shared knowledge to *{World}*. Every character in this World inherits what you add here." **No audience question — no CHARACTER option.** Ingest tabs immediately available.
6. Sections below Overview: **Episodes** (link to sibling route), **Teammates** (member list), **NarrativeMemoryList** (Universe-scoped memories), **Docs** (client-filtered on `d.universe === id`).
7. **Lifecycle region** at page bottom (destructive-tinted card): Archive / Delete permanently. Delete-blocked when members exist.

### C. Generic Knowledge entry
1. Dashboard / nav rail → **Knowledge**.
2. Bare `/workspace/knowledge` — pre-Slice-12 `UploadPanel` renders with the generic `UniverseScopePicker` on every ingest tab. Operator explicitly picks scope via "— Pick a scope —" (existing Universe row OR the "None (legacy)" WORKSPACE sentinel).
3. Ingest by Paste / Upload PDF / URL / Search.
4. Submit uses the picked scope. This path is the only place the WORKSPACE-via-legacy-sentinel gesture is still available.

---

## §5 Real dogfood evidence recorded

**OPERATOR OBSERVATION — Chris via ChatGPT, three real dogfood cycles:**

1. **Slice 10 (World-detail view/edit):** "Both pages look good. The default Overview state feels correct. The operator-visible distinction between World brief and Operator notes is understandable."
2. **Slice 12 (character-origin contextual handoff):** ran Sequence W (welcome-page handoff) with Tyson in Fox & Flour. Created two KDs — "Fox & Flour Hours" via **Everyone in Fox & Flour** (UNIVERSE), and "Tyson's Pastry Pairing Specialty" via **Just Tyson** (CHARACTER). Both persisted successfully.
3. **Slice 13 (World-origin contextual handoff):** ran Sequence WD (Worlds → Fox & Flour → Add shared knowledge). Created "Fox & Flour holiday policy" (UNIVERSE). "The World-detail flow worked exactly as predicted and did not require Chris to reconfirm an audience the originating World had already established."

**Runtime verification recorded (Slice 12.2 §247, Slice 13.1 §274):**

| KD title | audience | universe | M2M | Tyson | Ruby | Patch (control) | Penny (legacy control) |
|---|---|---|---|---|---|---|---|
| Fox & Flour Hours | UNIVERSE | Fox & Flour | [] | YES | YES | NO | NO |
| Tyson's Pastry Pairing Specialty | CHARACTER | Fox & Flour | [Tyson] | YES | **NO** | NO | NO |
| Fox & Flour holiday policy | UNIVERSE | Fox & Flour | [] | YES | YES | NO | NO |

**Matrix matches every prediction across the arc.** Cross-World isolation (Patch = NO) and legacy-pool isolation (Penny = NO) both confirmed via the production `retrieve_for_teammate` path.

Zero WORKSPACE-audience KDs exist in Chris's workspace. Zero cross-Universe leakage.

---

## §6 SESSION 277 hot-fix lesson — DO NOT REGRESS

Slice 12 initially shipped with a **wrong Character-audience payload builder**. The SPA sent only `{workspace, spokesperson_ids: [<uuid>]}` (no `universe`), which forced the KD to `universe=NULL` (legacy). The backend correctly rejected because Tyson has `universe=Fox&Flour` — the SESSION 261 M2M invariant requires `sp.universe_id == doc.universe_id`.

**Correct Universe-bound CHARACTER payload:**
```
POST /api/knowledge/
{
  workspace:         <workspace-uuid>,
  universe:          <character.universe.id>,   <-- REQUIRED
  spokesperson_ids:  [ <character.id> ],
  title:             ...,
  text_content OR pdf_data_uri OR source_url_input,
}
```

**Both `universe` AND `spokesperson_ids` are REQUIRED.** This is not "mixed audience". Precedence at `_persist` (`apps/embeddings/ingestion.py:276`) makes `spokespeople` win → `audience_scope=CHARACTER`, with the KD carrying the character's Universe FK to satisfy the M2M cross-check.

The SESSION 276 contradictory-payload guard (`serializers.py:265-281`) only fires for `audience_scope="workspace" + (spokespeople OR universe)`, **NOT** for `spokespeople + universe`.

**Backend regression:** `shell/apps/embeddings/tests/test_knowledge_universe_api.py::test_post_knowledge_universe_bound_character_shape_lands_as_character` locks this contract at the API boundary. Do not remove or weaken it.

---

## §7 Known legacy state (do not clean up in SESSION 278)

- **Penny** is outdated dogfood from a pre-current-flow era (58 compositions, all `episode=NULL`). Chris's stated position (SESSION 277 §63 / §79): Penny should NOT constrain forward architecture. She is preserved as legacy substrate — do not migrate her, do not archive her, do not use her as a design constraint.
- **5 legacy `universe=NULL` teammates** in Chris's workspace: Mason, Penny, Mike, Repo Red, Riggs. Structurally excluded from Universe-aware features (Episodes, NarrativeMemory, UNIVERSE-audience Knowledge, canon lane). Preserved deliberately — SESSION 261 chose opt-in prospective adoption rather than forced backfill.
- **Existing `business_brief` content on Universe-bound characters (Ruby, Patch, Rivet, Tyson) still carries World-identity overlap** because it predates `Universe.brief`. Do not run a decomposition migration merely because this is documented. Let the overlap resolve organically as operators re-author briefs.
- **`Universe.description` DB column name is unchanged** despite the operator label becoming "Operator notes (optional)". A future rename is a small housekeeping question, not urgent.

---

## §8 Deferred items (carried into SESSION 278)

Two items remain genuinely open. Both are low-priority.

### Q-277-13-B — Copy micro-slice (LOW PRIORITY)
Reword welcome-page CTA and/or character-detail KnowledgePanel empty-state now that all three handoff origins are settled. Chris reported no meaningful friction with current copy across all three dogfood cycles. Land only if a fresh friction observation surfaces.

### Q-277-13-D — Character-brief decomposition observation (OBSERVATION-ONLY)
Watch during normal dogfood whether operators naturally trim World-identity content from character `business_brief` fields now that `Universe.brief` and shared-World Knowledge are both live. **Observation only — do NOT force a decomposition migration.** If natural organic decomposition happens, no work required. If overlap persists indefinitely and causes synthesis drift, revisit as a separate slice.

### Genuinely open questions from earlier slices (still relevant, not urgent)
- `Universe.description` internal rename (Q-277-11-B alternate; low priority).
- Should the Docs section on `/workspace/universes/:id` also surface CHARACTER-audience KDs attached to that World's members? Deferred; no operator friction reported.
- Should the character-detail KnowledgePanel empty-state grow context-preserving CTA copy now that its Link already preserves context? Deferred; low priority.

**Aggressively excluded** from carry-forward: any implementation idea already superseded by later evidence (all Slice 1-9 hypothesis lists; all pre-Slice-8 Universe.brief representation options; all pre-Slice-13 handoff sketch variants; all wording candidates explored during audits).

---

## §9 Do not re-litigate without new runtime evidence

These findings are **settled** by dogfood. Future sessions should NOT reopen them merely because a new session began. Only revisit if new runtime evidence contradicts the finding.

- **Workspace = tenant/security boundary** (not the ordinary business/world concept). Established in SESSION 261 audit; re-verified in SESSION 277 Slices 2 and 6.
- **Ordinary new characters belong to a World.** Slice 5 invariant. Backend serializer enforces via `universe_required_on_create` code.
- **World brief ≠ detailed Knowledge.** Slice 7-8 finding; Slice 9 §170 label correction; Slice 10 view-mode correction.
- **Character-specific vs World-shared Knowledge is a first-class operator decision** when context leaves it genuinely ambiguous. Slice 12 contextual UI. Slice 12.2 + Slice 13.1 real-DB confirmation.
- **Contextual handoffs preserve known scope + ask only what's unknown.** Slice 13 §256 product rule; validated across three substrates.
- **Legacy `universe=NULL` state is historical residue** — not the ordinary new-character path. Slice 3 classification C.
- **The Universe-bound CHARACTER payload requires both `universe` AND `spokesperson_ids`.** Slice 12.1 hot-fix + backend regression.

---

## §10 Starting posture for SESSION 278

**Return to normal evidence-driven development:**

```
orient
  → identify one operator-visible friction / question
  → make a falsifiable prediction
  → smallest change or observation
  → dogfood
  → inspect runtime evidence
  → compare prediction vs reality
  → document
  → decide next
```

**Do not assume implementation is automatically next.** SESSION 277 closed on strong ground; there is no single obvious next friction that demands an immediate slice.

**Recommended first posture for SESSION 278 Claude:**
1. Read this handoff first (`docs/design/SESSION_278_HANDOFF.md`).
2. Only read `SESSION_277_OPERATOR_KNOWLEDGE_DOGFOOD.md` if a specific §-number in this handoff points there.
3. Verify baseline: git status + HEAD + origin/main + a short read-only DB probe of `chriss-workspace` (should be 3 KDs, 2 Universes, 9 teammates, `Universe.brief` on Fox & Flour still 331 chars).
4. Ask Chris what he wants to look at. **Do not invent work.** If Chris does not have a specific friction to bring, SESSION 278 should begin with a fresh operator dogfood pass across the flows in §4 to surface any residual friction — not with implementation.
5. If Chris raises a question that isn't visibly settled in this handoff, do a small audit slice (like SESSION 277's Slice 2 / 6 / 9 / 11) before implementing anything.

**Do NOT begin SESSION 278 with:**
- Any of the deferred items in §8 unless Chris explicitly asks.
- A "wrap up SESSION 277 loose ends" mindset — there are no undocumented loose ends; §8 exhausts them.
- Reopening any finding in §9 without runtime evidence.
- Assuming the SESSION 277 velocity (~14 slices) should continue. Slower is fine if there is no clear friction.

---

## §11 References

- **Full SESSION 277 audit:** `docs/design/SESSION_277_OPERATOR_KNOWLEDGE_DOGFOOD.md` (~6,700 lines, ~14 primary slices + hot-fix + verifications). Closed at SHA `88c255a` (Slice 13.1 SHA-record).
- **Load-bearing backend files:**
  - `shell/apps/universe/models.py` (Universe model + brief field).
  - `shell/apps/spokespeople/serializers.py` (`universe_required_on_create` guard).
  - `shell/apps/embeddings/serializers.py` (audience-scope positive-value validation).
  - `shell/apps/embeddings/ingestion.py` (audience_scope precedence).
  - `shell/apps/embeddings/retrieval.py` (`retrieve_for_teammate` predicate).
  - `shell/character_os/script_synthesis.py`, `dialogue_synthesis.py`, `teammate_ask.py`, `conversation_synthesis.py`, `claim_verifier.py` (five synthesis sites reading `Universe.brief`).
- **Load-bearing SPA files:**
  - `web/src/lib/knowledge/handoff.ts` (handoff contract).
  - `web/src/routes/spokespeople/welcome.tsx` (character-welcome origin).
  - `web/src/components/knowledge-panel.tsx` (character-detail origin).
  - `web/src/routes/workspace/universes.$id.tsx` (World detail + Add shared knowledge action).
  - `web/src/routes/workspace/knowledge.tsx` (contextual destination + `CharacterOriginUploadPanel` + `WorldOriginUploadPanel`).
  - `web/src/components/spokesperson-wizard.tsx` (Slice-5 World picker + inline create).
- **Migrations added in SESSION 277:**
  - `shell/apps/universe/migrations/0004_session277_universe_brief.py` (AddField `brief`).
- **Backend regression tests (do not weaken):**
  - `shell/apps/spokespeople/tests/test_universe_required_on_create.py`
  - `shell/apps/universe/tests/test_universe_brief.py`
  - `shell/apps/embeddings/tests/test_knowledge_universe_api.py::test_post_knowledge_universe_bound_character_shape_lands_as_character`

---

_This handoff supersedes all SESSION 277 "smallest next question" recommendations. Start SESSION 278 fresh from Chris's next question or dogfood observation._
