# SESSION 274 — Universe-Shared + Character-Specific Knowledge Dogfood (Slice 2)

**Status:** Slice 2 OPEN. Slice 1 CLOSED at commit `e7ff4a4` (`docs(session-274): §1-§11 Slice 1 — shared/global knowledge characterization (read-only)`).

**Slice 2 stop condition — FIRST STOP (right now):** propose Class C content, present overlap analysis and probe plan, **WAIT for Chris's content approval** before any DB mutation.

**Author window:** SESSION 274 Slice 2 open → this doc.

---

## §1. HYPOTHESIS

The product model Character OS already appears to be approximating is:

> **Universe-shared knowledge** (facts every character in a Universe should be allowed to know) **+ character-specific knowledge** (expertise for one particular character in that Universe).

Slice 1 proved that the eligibility layer can express this exactly — Class C (`universe=U, spokespeople=∅`) and Class D (`universe=U, spokespeople={A}`) are both eligible for character A when A is in U. What is NOT known is whether **cosine-only `top_k=5` ranking** allows them to coexist reliably or whether one systematically starves the other.

Slice 2 question:

> Can a character reliably use shared facts from its Universe together with its own character-specific expertise?

Slice 2 is a **characterization / dogfood** slice. It does NOT redesign retrieval. It measures whether the existing system supports the product model well enough that a smaller product-decision could stand on it.

---

## §2. SUBSTRATE

| Item | Value |
| --- | --- |
| Universe | Fox & Flour Bakery (`1a0af807-dd6a-47cd-bfaa-3d088f1c105f`) |
| Character | Ruby (`5875a7b4-cf39-433d-89b3-4e34a89a5208`) |
| Existing Class D KD | Fox & Flour Bakery — Working Knowledge (`74e7f18f-5b77-459c-bc36-b4ab617d8aca`) — 10 chunks, 6,598 chars |
| NarrativeMemory | none for Ruby |
| Persona | wizard-default (only `business_brief` + `personality` + `tone_archetype` populated) |
| Prior renders | 2 successful videos (SESSION 273 §27 and §29–§32) grounded 100% on Class D KD alone |
| Class C KDs in Fox & Flour today | **0** (Slice 1 §4.7) |

**Substrate rules for Slice 2 (per Chris):**
- Do NOT modify Ruby's persona.
- Do NOT modify Ruby's existing Class D KD.
- Do NOT create any NarrativeMemory.
- Do NOT create additional Fox & Flour teammates just for the test.
- Do NOT use Patch / Rivet as the primary substrate.
- Cross-Universe / cross-workspace exclusion is proven mechanically by Slice 1 rows 5 and 9; Slice 2 verifies it read-only, does not need new characters.

---

## §3. OVERLAP AUDIT — RUBY'S EXISTING CLASS D KD

The full processed content of `74e7f18f` (`Fox & Flour Bakery — Working Knowledge`) is 6,598 chars organized into 8 markdown sections. Read-only inspection performed via `manage.py shell`; no changes.

| # | Section | Content type | Predominantly Ruby-specific? | Predominantly business/world? |
| --- | --- | --- | --- | --- |
| 1 | Breads & sourdough | product/craft (recipes, breads, pricing rule, discount policy, food-shelf donation) | mixed — craft + policy | mixed |
| 2 | Pastries | product line (bake schedule, daily case, half-price/donation policy) | mixed | mixed |
| 3 | Celebration cakes | product line + policy (styles, fillings, aesthetic, **5-day / 10-day lead time**, **50% deposit non-refundable inside 72 hrs**, **pickup-only no delivery**) | Ruby's aesthetic bias (rustic-elegant, steers away from fondant) is Ruby-specific | policy facts (lead time / deposit / pickup) are business |
| 4 | Ingredients & sourcing | supplier categories (Colorado mill, family creamery 2 hrs north, pastured egg farm, Wednesday+Saturday farmers markets w/ 3 growers, California citrus, single-origin West Coast chocolate, Maine flaky sea salt) + Ruby's "no artisan buzzword" stance and "we can tell you where it came from" rule | Ruby's marketing stance is Ruby-specific | supplier categories are business |
| 5 | Bakery routines | **Wed–Sun 7 AM–3 PM**, Mon+Tue closed for production/deep-clean/menu dev, bake rhythm (mixed doughs afternoon before → bench-proof overnight → shape+bake AM), pastry lamination Sundays, custom-cake work Mon+Tue+Thu, staffing (Ruby bakes Wed/Fri/Sun, lead baker Thu+Sat, 2 counter, 1 part-time decorator) | staffing rotation names Ruby | hours + closed-days + prep rhythm are business |
| 6 | Seasonal offerings | Spring/Summer/Autumn/Winter menu rotations + preorder holiday cutoff "two weeks ahead / no walk-in same-day" | menu specifics are product | preorder cutoff is business |
| 7 | Customer experience | **6 counter seats + few two-tops**, regulars-by-name policy, **private paper notebook** for allergy notes + kids' bday history, "no question too basic" staff rule, celebration-cake waitlist during peak, refers to two other trusted independent bakers when full, coffee bought (not roasted) from small nearby roaster + used in case-walkthrough conversation | Ruby-knows-regulars is personal | seating/waitlist/referral/coffee-partner are business |
| 8 | Ruby's reason for operating Fox & Flour | biography (8 years in others' kitchens, fine-dining pastry → bakery-café sold-to-chain, opened Fox & Flour as neighborhood pushback), **name origin (grandmother's "little fox" + "flour")**, **twice declined to expand**, "quality ceiling drops when I stop being in the kitchen" | **Ruby-only autobiographical** | not business |

### §3.1. What is genuinely Ruby-only in the current KD

- Ruby's biographical arc (§8)
- Ruby's design/aesthetic stance on cakes (buttercream over fondant, rustic-elegant)
- Ruby's marketing stance on "artisan"
- Ruby's decision to not expand
- Ruby's baker rotation (naming her personally as Wed/Fri/Sun baker)
- Ruby's individual craft technique + starter maintenance

### §3.2. What is business/Universe fact currently living inside Ruby's Class D KD

These facts are legitimate Fox & Flour Bakery business facts. They live inside a Ruby-scoped Class D KD today only because Ruby was the first (and only) Fox & Flour teammate, and there was no Class C KD when her KD was authored:

- **Open days + hours:** Wed–Sun, 7 AM – 3 PM; Mon + Tue closed to public
- **Purpose of closed days:** custom-order production, deep cleaning, menu development
- **Celebration-cake ordering policy:** minimum 5-day lead for standard tiered cakes / 10-day for sculpted or heavily decorated
- **Deposit policy:** 50% at booking; non-refundable inside 72 hours of pickup
- **Pickup-only:** Fox & Flour does not deliver cakes
- **Preorder-holiday cutoff:** two weeks ahead for Thanksgiving / Christmas Eve / Easter, with no walk-in same-day availability for specialty items
- **Day-old bread policy:** discounted next morning; unsold goes to local food shelf on Sunday evening
- **Pastry unsold policy:** half-price in the last hour of the day, or donated same evening
- **Physical footprint:** small storefront with 6 counter seats + a handful of two-tops by the window
- **Customer-record habit:** paper notebook behind the register for allergy notes + kids'-birthday histories
- **Celebration-cake waitlist practice:** small waitlist during peak weeks; when they can't book, counter recommends two named other independent bakers Ruby trusts
- **Coffee policy:** beans sourced from a small nearby roaster; not roasted in-house; part of case-walkthrough for newer customers
- **Sourcing categories:** Colorado regional mill / family creamery ~2 hrs north / pastured local egg farm / Wednesday + Saturday farmers markets w/ 3 long-term growers / California citrus cooperative in winter / single-origin West Coast chocolate / Maine flaky sea salt

### §3.3. Duplication policy

Chris's rule (Slice 2 §3):

> The new Class C document should contain as little duplication as practical.
> If existing approved Fox & Flour material already provides enough shared facts, reuse only those supported facts and cite their source.

Ruby's existing KD **already contains sufficient approved business facts** to build a small non-inventive Class C. **All content proposed below is drawn from `74e7f18f` — no new Fox & Flour facts are being invented for Slice 2.** Overlap with the Class D KD is therefore intentional and irreducible: Chris told us not to modify Ruby's KD, so if we extract the business facts into a Class C KD, both KDs will contain those same facts. This overlap is a **feature of the experiment** — it directly stresses the Slice 2 question about coexistence and starvation.

Optionally, Chris may authorize a small number of NEW Fox & Flour business facts to sharpen the semantic separation. Those are enumerated in §4.2 as a distinct **Option B** and require explicit approval before ingestion.

---

## §4. PROPOSED CLASS C CONTENT

Two content options are presented. Chris chooses ONE (or a hybrid) before any ingestion. No KD has been created.

### §4.1. Option A — EXTRACT-ONLY (no new facts, all quotable from Ruby's KD)

**Title:** `Fox & Flour Bakery — House Policies & Hours`

**Universe:** `1a0af807-dd6a-47cd-bfaa-3d088f1c105f` (Fox & Flour Bakery)

**Spokespeople:** *(EMPTY — true Class C)*

**Ingest mode:** paste (markdown)

**Content (draft):**

```markdown
## Hours and closed days

Fox & Flour Bakery is open to the public Wednesday through Sunday,
7 AM to 3 PM. Monday and Tuesday the shop is closed to the public
and used for large custom-order production, deep cleaning, and menu
development.

## Storefront and seating

The bakery is a small neighborhood storefront with six seats at the
counter and a handful of two-tops by the window. Regulars are
recognized by name and by their usual order. A private paper
notebook is kept behind the register for allergy notes and
children's-birthday histories.

## Celebration cake orders

Custom celebration cakes are a special-order item, not a walk-in
item. Standard tiered cakes require a minimum five-day lead time.
Sculpted or heavily decorated cakes require a minimum ten-day lead
time. Peak seasons (spring weddings and December holidays) push
those lead times out further.

A 50% deposit is taken at booking. Deposits are non-refundable
inside 72 hours before pickup. Fox & Flour does not deliver cakes;
all orders are pickup only.

During peak weeks the shop keeps a small waitlist for celebration
cakes. When the shop cannot take a booking, the counter staff
recommend one of two other independent bakers in town that Ruby
personally knows and trusts.

## Preorder holidays

Fox & Flour publishes a two-week cutoff ahead of Thanksgiving,
Christmas Eve, and Easter for holiday-specialty items. There is no
walk-in same-day availability for those specialty items after the
cutoff.

## Day-of leftovers policy

Whole loaves are priced by weight and cut on request. Half loaves
are available. Day-old bread is discounted the following morning;
unsold bread goes to the local food shelf on Sunday evening.

Morning pastries are not held over. Whatever does not sell by close
is either marked half price in the last hour or donated the same
evening.

## Sourcing categories

Flour comes from a Colorado regional mill. Butter and dairy are
sourced from a family creamery about two hours north of town. Eggs
come from a pastured local farm at similar distance. Fruit shifts
with the season: through summer and fall most fruit comes from the
Wednesday and Saturday farmers markets from three growers the
bakery has worked with for years; in winter the shop supplements
with citrus from a California cooperative. Chocolate is
single-origin from a small West Coast chocolate maker. Salt is
flaky sea salt from Maine.

When a customer asks where something came from, staff are trained
to name the actual farm, mill, or maker rather than use generic
"artisan" language.

## Coffee

Coffee is served but not roasted in-house. Beans are bought from a
small roaster nearby. The pairing between coffee and a given
pastry is part of the case-walkthrough conversation for newer
customers.
```

**Character count (draft):** ~2,050 chars (well below the current Ruby KD's 6,598 chars — deliberately small so any starvation effect is visible instead of masked by sheer volume).

**Expected chunk count after ingest:** 3–5 chunks (based on prior Fox & Flour ingest producing 10 chunks from 6,598 chars; scale-adjusted).

**Source citation:** Every fact in this draft appears verbatim or as a straightforward business-voice paraphrase of a fact already present in Ruby's approved `74e7f18f` KD (§3.2 above enumerates the source lines). **Zero invented facts.**

**Deliberate style shift:** Ruby's KD is written in a mixed first-person-narrator / Ruby-referential voice (e.g., "Ruby knows most regulars," "Ruby steers most customers toward buttercream"). Option A is written in third-person business voice (e.g., "regulars are recognized by name," "the shop cannot take a booking"). This keeps the SAME facts in both KDs but attributes them to the BUSINESS rather than to Ruby specifically. Whether cosine ranking finds the two encodings semantically similar enough to compete for the same slot is exactly what we want to measure.

### §4.2. Option B — EXTRACT + a small set of new business facts (REQUIRES CHRIS'S APPROVAL)

Option B is Option A **plus** a small number of NEW Fox & Flour facts that do not exist in Ruby's KD. These would sharpen the semantic separation (some queries could only be answered from Class C, some only from Class D) and reduce cosine-overlap-induced competition. They are **invented** and Chris must approve each one individually or overwrite them with facts he already knows about Fox & Flour.

Candidate new facts (flagged **[INVENTED — needs Chris approval]** for each):

- **[INVENTED]** Address / neighborhood: no physical address is currently in Ruby's KD. A neighborhood label (e.g., "in the West End of a small mountain-adjacent town") is likely fine as flavor, but even a fictional street name should be Chris's call.
- **[INVENTED]** Contact hours for custom orders: e.g., "Custom-order inquiries are taken by phone or in person during open hours; email requests are answered the next open day."
- **[INVENTED]** Allergen accommodation policy beyond the notebook: e.g., "The shop can flag gluten-containing surfaces on request but is not a certified gluten-free environment."
- **[INVENTED]** Kids-birthday-party protocol: e.g., "Fox & Flour hosts small in-shop kids'-birthday cake pickups on Sunday afternoons only, by prior arrangement."
- **[INVENTED]** Gift cards: e.g., "Gift cards are sold in fixed denominations at the counter; no online purchase."
- **[INVENTED]** Mailing list / preorder notifications: e.g., "The bakery keeps a low-volume opt-in email list for holiday preorder announcements only."
- **[INVENTED]** Catering minimum: e.g., "Whole-loaf standing orders for cafés or restaurants require a two-week trial and a 12-loaf weekly minimum."

**Chris:** please tell me which (if any) of these are correct-adjacent to Fox & Flour as you already conceive of it, or provide the right versions. Any un-approved item will NOT be ingested. If none of these are approved, Option A stands as-is.

### §4.3. Overlap risk & why it is scientifically useful

- Option A duplicates business facts across Class C and Class D. Cosine ranking is likely to place both encodings near the same query embedding. Slice 2 will directly observe whether the two encodings compete for the same `top_k` slot, whether one dominates, and whether the character-specific chunks (Ruby's aesthetic / biography / sourcing stance) survive alongside them.
- Option B reduces overlap for the added facts, giving us a cleaner "shared knowledge that Class D cannot supply" test.
- Combined Option A + Option B would give us BOTH signals in the same experiment: the extract-only overlap section characterizes duplication behavior, and the invented section characterizes clean-separation behavior.

---

## §5. EXPECTED ELIGIBILITY (before ingestion)

Per Slice 1 truth table (rows 5–9) plus `retrieval.py:194–226`:

| Teammate | Universe | Expected eligibility for the new Class C KD |
| --- | --- | --- |
| Ruby | Fox & Flour Bakery | **ELIGIBLE** — row 6 (empty M2M within same Universe). Class D KD also eligible. |
| Patch | Patch's Workshop | **NOT ELIGIBLE** — row 9 (different Universe). |
| Rivet | Patch's Workshop | **NOT ELIGIBLE** — row 9. |
| Mason | *legacy* (universe=None) | **NOT ELIGIBLE** — row 4 (legacy teammate cannot see Universe-scoped docs). |
| Penny | legacy | **NOT ELIGIBLE** — row 4. |
| Mike | legacy | **NOT ELIGIBLE** — row 4. |
| Repo Red | legacy | **NOT ELIGIBLE** — row 4. |
| Riggs | legacy | **NOT ELIGIBLE** — row 4. |

Verification of these expectations is a required Slice 2 checkbox (§9).

---

## §6. BASELINE RETRIEVAL PROBE PLAN (READ-ONLY)

**Runs before Class C ingestion.** Same probes will be re-run after ingestion (§7) for a before/after matrix.

**Method:** direct call to `retrieve_for_teammate(ruby, query, top_k=5)` via `manage.py shell`. Zero provider cost — the retrieval function itself calls `_embed_query` (OpenAI `text-embedding-3-small` — ~$0.00002 per query at 8k tokens max; four baseline queries + four post-ingest = 8 embeds total ~ $0.0002 aggregate cost). No LLM completion call. No Composition row. No render.

**Per-chunk record for each returned chunk:**

- rank (0-indexed)
- cosine distance (from the `.annotate(distance=CosineDistance(...))` result)
- document title + UUID
- chunk index within document
- chunk class (A / B / C / D / D-fullcast)
- 1–2 sentence excerpt or summary

**Queries (4 total, mapped to §5 of Chris's Slice 2 spec):**

| ID | Category | Query text | Why |
| --- | --- | --- | --- |
| **Q-A** | clearly Ruby-specific | "Why did you decide not to open a second location?" | Answer lives only in §8 of Ruby's KD (autobiographical). Class C cannot help. |
| **Q-B** | clearly candidate shared / business | "How far in advance do I need to order a custom birthday cake and what deposit is required?" | Answer is a business policy fact — currently in Ruby's KD §3 (5-day / 10-day / 50%). After Class C creation, both KDs will contain it. |
| **Q-C** | ambiguous — both plausible | "What kinds of bread do you sell and how do you source your flour?" | Draws from Ruby's craft (§1 Breads) and business sourcing (§4). Both KDs will contribute after Class C. |
| **Q-D** | unrelated control | "Do you offer catering for corporate events?" | Neither KD currently addresses this. Expect noise-level cosine matches only. Useful as a baseline for what "no real match" looks like. |

**Additional cross-Universe / cross-scope verification probes (post-ingest only, mechanical rather than semantic):**

- Call `retrieve_for_teammate(patch, "birthday cake lead time", top_k=5)` → expect no Fox & Flour Class C chunk in result.
- Call `retrieve_for_teammate(rivet, "birthday cake lead time", top_k=5)` → same.
- Call `retrieve_for_teammate(mason, "birthday cake lead time", top_k=5)` → same (row 4).

**Explicit contract:**
- No `save()`, no `create()`, no `update()` calls.
- No mocks, no experiment env vars.
- All output captured into this doc as append-only sections §11 (baseline) and §12 (post-ingest matrix).

---

## §7. POST-CLASS-C RETRIEVAL MATRIX PLAN

After ingestion of the approved Class C KD (only if Chris authorizes), re-run all four queries with the same method. Produce a before/after comparison in §12. Explicitly answer the eight Slice-2 §8 questions:

1. Do Class C and Class D actually coexist in Ruby's top_k?
2. On a Ruby-specific query (Q-A), does her Class D expertise survive?
3. On a business-wide query (Q-B), does Class C appropriately dominate?
4. On an ambiguous query (Q-C), what mixture appears?
5. Can Class C occupy all five slots?
6. Can Class D occupy all five slots?
7. Does the observed ranking align with the intended semantic distinction?
8. Is starvation merely theoretically possible or readily observable?

**Non-negotiable:** if results are ugly, they are preserved. No quotas, weights, two-lane retrieval, per-document diversity, scope priority, prompt changes, larger top_k, reranking, or K6 scope labels are added to make the test pass (per §9 of Chris's spec).

---

## §8. OPTIONAL K6 / COMPOSITION DOGFOOD (contingent on retrieval outcome)

Do NOT render automatically.

If the §7 retrieval matrix shows a useful Class C + Class D coexistence case, propose ONE Ruby talking-head Episode topic that would naturally require BOTH — a simple operator-authored topic, not a jailbreak topic that stuffs "cite both docs" into the prompt.

Before the render, this doc will record: proposed Episode title, proposed simple topic, expected Class C contribution, expected Class D contribution, and expected retrieved chunks. **Then WAIT for Chris's authorization.**

If retrieval already demonstrates a serious failure mode, skip the render — no reason to burn a provider call to prove the downstream consequence.

---

## §9. UI OBSERVATION LOG — CLASS C CREATION PATH

Because Slice 1 found Class C effectively unused in production, the actual operator flow used to create the Class C KD will be observed and recorded here as product evidence. Slice 2 will NOT patch the SPA opportunistically.

Recorded fields (populated during KD creation, only if Chris authorizes):

- How Chris/Claude selects Fox & Flour Bakery Universe on the create form.
- Whether leaving the spokesperson selection empty is intentional/obvious given current UI.
- Whether the create UI explains that empty spokespeople = "shared with everyone in Fox & Flour."
- What the document looks like after save (list view, detail view).
- Whether Universe scope remains visible post-save.
- Whether Ruby's detail-page Knowledge panel labels the KD accurately (predicted from Slice 1: it will use the "workspace" label, which will be demonstrably wrong for Class C).
- Whether current "workspace" copy is provably wrong once we can point at a live Class C instance.

This section will be filled in only after ingestion, if authorized.

---

## §10. STOP CONDITIONS

**FIRST STOP (right now):**
Chris reviews §3 overlap audit, §4 proposed content (Option A / Option B / hybrid), §6 baseline probe plan, and either approves the content to be ingested or provides amended content. **NO KD IS CREATED until Chris explicitly approves.**

**Second stop (after ingestion + retrieval matrix):**
Slice 2 verdict is one of GREEN / YELLOW / RED (per §12 of Chris's spec). Chris reviews the verdict and decides whether a Slice 3 render is warranted, whether to revisit product options P1/P2/P3/P4/P2-lite, or whether SESSION 274 should close here.

**Slice 2 does NOT decide the product model.** It supplies additional evidence to the product-decision brief already scaffolded in Slice 1 §8.

---

## §11. BASELINE RETRIEVAL RESULTS (pre–Class C)

**Method.** Direct call to the same ORM query as `retrieve_for_teammate(ruby, query, top_k=5)` (workspace filter + `universe_id=Fox&Flour` + `Q(spokespeople__isnull=True) | Q(spokespeople=Ruby)` + CosineDistance sort). Read-only. Executed at Slice 2 open, `OPENAI_API_KEY` sourced from the running Django process env (real embeddings, `text-embedding-3-small`). No Composition, no LLM call, no DB writes.

At baseline Ruby had exactly one eligible KD (her Class D `74e7f18f`, 10 chunks). All 4 queries × top_k=5 = 20 slots came from that single doc.

### §11.1. Q-A [Ruby-specific] — `"Why did you decide not to open a second location?"`

| Rank | Cosine dist | Class | Doc | Chunk idx | Chunk UUID | Excerpt (first ~180 chars) |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.6231 | D | Fox & Flour Bakery — Working Knowledge | 9 | `74c810f9-…` | `than to a distant owner who never smelled the ovens. The name comes from an old family nickname (Ruby's grandmother called her "little fox") and from the literal thing the shop…` |
| 1 | 0.6815 | D | Fox & Flour Bakery — Working Knowledge | 8 | `15ca8597-…` | `a small waitlist for celebration cakes during peak weeks. When the shop can't take a booking, the counter staff recommend one of two other independent bakers in town who Ruby knows…` |
| 2 | 0.7589 | D | Fox & Flour Bakery — Working Knowledge | 4 | `1754ac81-…` | `50% deposit is taken at booking. Deposits are non-refundable inside of 72 hours before pickup. Fox & Flour does not deliver cakes; all orders are pickup only. ## Ingredients…` |
| 3 | 0.7718 | D | Fox & Flour Bakery — Working Knowledge | 7 | `5f169561-…` | `in January. Preorder holidays (Thanksgiving, Christmas Eve, Easter) have a published cutoff two weeks ahead and no walk-in same-day availability for the specialty items. ## Cus…` |
| 4 | 0.7859 | D | Fox & Flour Bakery — Working Knowledge | 6 | `659524ac-…` | `Friday, and Sunday. Her lead baker covers Thursday and Saturday. There are two counter staff and one part-time decorator. ## Seasonal offerings ## Menu rotations follow the calendar…` |

Semantic reading: rank 0 is exactly the answer (grandmother nickname → autobiography section that discusses the no-expansion stance). Ranks 1–4 are adjacent Ruby-context chunks. Mix: D=5, C=0.

### §11.2. Q-B [business/shared] — `"How far in advance do I need to order a custom birthday cake and what deposit is required?"`

| Rank | Cosine dist | Class | Doc | Chunk idx | Chunk UUID | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.3761 | D | Fox & Flour Bakery — Working Knowledge | 3 | `cc0c4259-…` | `lead time is a minimum of five days for standard tiered cakes and ten days for sculpted or heavily decorated cakes; peak seasons (spring weddings, December holidays) push those win…` |
| 1 | 0.5188 | D | Fox & Flour Bakery — Working Knowledge | 7 | `5f169561-…` | Preorder holidays chunk |
| 2 | 0.5284 | D | Fox & Flour Bakery — Working Knowledge | 4 | `1754ac81-…` | 50% deposit chunk |
| 3 | 0.5609 | D | Fox & Flour Bakery — Working Knowledge | 2 | `18f9eb09-…` | Scones + pastries-not-held-over chunk |
| 4 | 0.6242 | D | Fox & Flour Bakery — Working Knowledge | 6 | `659524ac-…` | Bake-rotation chunk |

Semantic reading: rank 0 has both facts (lead time AND deposit). Mix: D=5, C=0.

### §11.3. Q-C [ambiguous] — `"What kinds of bread do you sell and how do you source your flour?"`

| Rank | Cosine dist | Class | Doc | Chunk idx | Excerpt |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.4275 | D | Fox & Flour Bakery — Working Knowledge | 0 | Breads & sourdough intro |
| 1 | 0.4912 | D | Fox & Flour Bakery — Working Knowledge | 4 | 50% deposit + Ingredients & sourcing chunk |
| 2 | 0.5034 | D | Fox & Flour Bakery — Working Knowledge | 1 | Rotating breads + brioche chunk |
| 3 | 0.5517 | D | Fox & Flour Bakery — Working Knowledge | 5 | `"artisan"`-avoidance + bakery routines chunk |
| 4 | 0.5704 | D | Fox & Flour Bakery — Working Knowledge | 6 | Bake-rotation chunk |

Semantic reading: bread-and-flour question naturally pulls the breads section + sourcing-adjacent chunks. Mix: D=5, C=0.

### §11.4. Q-D [unrelated control] — `"Do you offer catering for corporate events?"`

| Rank | Cosine dist | Class | Doc | Chunk idx | Excerpt |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.6579 | D | Fox & Flour Bakery — Working Knowledge | 6 | Bake-rotation chunk |
| 1 | 0.6611 | D | Fox & Flour Bakery — Working Knowledge | 3 | Cake lead-time chunk |
| 2 | 0.6651 | D | Fox & Flour Bakery — Working Knowledge | 2 | Pastries-not-held-over chunk |
| 3 | 0.6877 | D | Fox & Flour Bakery — Working Knowledge | 1 | Rotating breads + brioche chunk |
| 4 | 0.7000 | D | Fox & Flour Bakery — Working Knowledge | 4 | 50% deposit + sourcing chunk |

Semantic reading: no strong match; ranking is noise-level cosine floor (0.66–0.70) — Fox & Flour has nothing about catering. Mix: D=5, C=0.

### §11.5. Baseline summary

Every one of the 20 top_k slots is Class D (only eligible KD pre-ingest). Distance floor `0.66` on Q-D is a useful "no-real-match" watermark. Ruby's authoritative autobiographical chunk (idx 9) ranked 0 on Q-A. Semantic ranking behaves as expected within a single-doc corpus.

---

## §11.6. CLASS C KD CREATION EVIDENCE

Executed via `apps.embeddings.ingestion.ingest_text(...)` then `embed_document.apply([doc.id])` synchronously (celery task in-process rather than via broker; same code path, deterministic completion for measurement).

| Field | Value |
| --- | --- |
| Doc UUID | `8f825c98-f420-4867-8700-6d4db6832d9d` |
| Title | `Fox & Flour Bakery — House Policies & Hours` |
| Workspace | `4ce5486d-…` (chriss-workspace) |
| Universe | `1a0af807-…` (Fox & Flour Bakery) |
| Spokespeople M2M | **empty (0)** — true Class C ✓ |
| document_type | markdown |
| ingested_via | paste |
| Raw content length | 2,769 chars |
| Content hash | `d205f813b24ad8647d6df18a99c5299fc9ea4e1db4275cdffff22d95c0a8cbad` |
| Status | processed |
| is_active | True |
| Chunk count | **5** (within predicted 3–5 range) |
| All chunks embedded | True (embedding_vector non-null on all 5) |
| Chunk sizes | 869, 833, 558, 895, 397 chars |
| Deduped on ingest | False (new content_hash) |
| Class | **C** ✓ |
| Ruby's `74e7f18f` post-ingest | content_hash unchanged (`7a0e4bd2…`), chunks=10 unchanged, spokespeople=1 unchanged |
| Ruby persona post-ingest | untouched (no persona field modified) |
| NarrativeMemory | zero rows in Ruby's Universe, unchanged |

### §11.6.1. Ingestion invariants verified

- KD created with `universe=Fox & Flour, spokespeople=∅` in a single transaction (per `ingestion.py:_persist` at lines 132–170).
- Chunking + embedding driven by `embed_document` celery task, run synchronously in-process to make measurement deterministic; identical code path to production celery worker.
- Ruby's Class D KD is byte-identical before and after (content_hash unchanged). No modification, no re-ingest, no re-embedding.
- No new teammates, no persona changes, no NarrativeMemory rows.

---

## §12. POST–CLASS C RETRIEVAL MATRIX

### §12.1. Eligibility verification (mechanical)

| Teammate | Universe | Eligible KDs (post-ingest) | New Class C visible? |
| --- | --- | --- | --- |
| Ruby | Fox & Flour Bakery | Class C `Fox & Flour Bakery — House Policies & Hours`; Class D `Fox & Flour Bakery — Working Knowledge` | **YES** ✓ (expected) |
| Patch | Patch's Workshop | Class D `PATCH — AI BUILDING…`; Class D `PATCH'S WORKSHOP — SHARED CANON` | **NO** ✓ (row 9, cross-Universe) |
| Rivet | Patch's Workshop | Class D `RIVET — EXPERIMENTATION…`; Class D `PATCH'S WORKSHOP — SHARED CANON` | **NO** ✓ (row 9) |
| Mason | *legacy* (universe=None) | 9 Class A (Riggs, TANK, Tulsi, 6× Hearth & Hollow) | **NO** ✓ (row 4, legacy cannot see Universe-scoped) |

**All four eligibility expectations verified.**

### §12.2. Cross-scope exclusion probe

Query: `"birthday cake lead time and deposit policy"` — deliberately business-flavored so Class C should be the closest match if the exclusion were faulty.

| Teammate | Fox & Flour Class C hits (of top 5) | Notes |
| --- | --- | --- |
| Patch | **0** ✓ | All 5 slots are `PATCH — AI BUILDING…` chunks (dist 0.87–0.92; noise floor for an off-topic corpus). |
| Rivet | **0** ✓ | All 5 slots are `RIVET — EXPERIMENTATION…` chunks (dist 0.89–0.93). |
| Mason | **0** ✓ | All 5 slots are `TANK — AUTOMOTIVE FINANCING…` chunks (dist 0.80–0.82). |

**Cross-Universe (rows 9) and legacy-vs-Universe (row 4) exclusion mechanically verified.** No Class C leak across scope boundaries.

### §12.3. Ruby post-ingest retrieval (same 4 queries)

#### §12.3.1. Q-A [Ruby-specific] — post-ingest

| Rank | Cosine dist | Class | Doc | Chunk idx | Chunk UUID | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.6231 | D | Working Knowledge | 9 | `74c810f9-…` | Autobiography / no-expansion stance |
| 1 | 0.6815 | D | Working Knowledge | 8 | `15ca8597-…` | Waitlist + trusted-baker referral |
| 2 | **0.7435** | **C** | **House Policies & Hours** | 0 | `63a05d1a-…` | `Hours and closed days` |
| 3 | 0.7589 | D | Working Knowledge | 4 | `1754ac81-…` | 50% deposit + sourcing |
| 4 | **0.7646** | **C** | **House Policies & Hours** | 4 | `d0829555-…` | Sourcing/`artisan` chunk |

Mix: **C=2, D=3.** Ruby's autobiography chunk (the correct answer) **retained rank 0**. Two Class C chunks displaced Ruby's D chunks at ranks 5–7 of the baseline (which would have been idx 6, 3, 2 of her doc). Neither Class C chunk actually answers the Ruby-specific question — they're context / off-topic bakery facts.

#### §12.3.2. Q-B [business/shared] — post-ingest

| Rank | Cosine dist | Class | Doc | Chunk idx | Chunk UUID | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | **0.3758** | **C** | **House Policies & Hours** | 1 | `c62b3988-…` | `require a minimum five-day lead time…` (business-voice restatement) |
| 1 | 0.3761 | D | Working Knowledge | 3 | `cc0c4259-…` | `lead time is a minimum of five days…` (Ruby-voice original) |
| 2 | 0.5188 | D | Working Knowledge | 7 | `5f169561-…` | Preorder-holiday cutoffs |
| 3 | **0.5223** | **C** | **House Policies & Hours** | 0 | `63a05d1a-…` | `Hours and closed days` |
| 4 | 0.5284 | D | Working Knowledge | 4 | `1754ac81-…` | 50% deposit + sourcing |

Mix: **C=2, D=3.** Class C landed rank 0. **The duplicated lead-time chunks (Class C rank 0 vs Class D rank 1) are separated by 0.0003 in cosine distance — essentially a tie.** Both surfaced. Rank 4 is the 50%-deposit fact (Class D), so the operator would see the deposit answer as well.

**Observation:** the duplicated chunks did NOT collapse to one; both were surfaced, back to back. The tiebreaker between two encodings of the same fact is essentially random within measurement noise (0.0003).

#### §12.3.3. Q-C [ambiguous] — post-ingest

| Rank | Cosine dist | Class | Doc | Chunk idx | Excerpt |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.4275 | D | Working Knowledge | 0 | Breads & sourdough intro |
| 1 | **0.4454** | **C** | **House Policies & Hours** | 3 | Day-of leftovers + Sourcing intro |
| 2 | 0.4912 | D | Working Knowledge | 4 | 50% deposit + Ingredients & sourcing |
| 3 | 0.5034 | D | Working Knowledge | 1 | Rotating breads + brioche |
| 4 | 0.5517 | D | Working Knowledge | 5 | `"artisan"`-avoidance + bakery routines |

Mix: **C=1, D=4.** Class D dominant. Class C sourcing chunk broke into rank 1 (dist 0.4454 vs prior baseline rank-1 of 0.4912 which was Class D). Ruby's authoritative breads chunk held rank 0.

#### §12.3.4. Q-D [unrelated control] — post-ingest

| Rank | Cosine dist | Class | Doc | Chunk idx | Excerpt |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.6579 | D | Working Knowledge | 6 | Bake-rotation |
| 1 | 0.6611 | D | Working Knowledge | 3 | Cake lead-time |
| 2 | 0.6651 | D | Working Knowledge | 2 | Pastries |
| 3 | **0.6773** | **C** | **House Policies & Hours** | 0 | Hours & closed days |
| 4 | **0.6848** | **C** | **House Policies & Hours** | 1 | Celebration cake orders |

Mix: **C=2, D=3.** All chunks at noise-floor distance (0.66–0.68 — same as baseline). Class C's small size means each of its chunks has enough generic bakery text to match noise-level queries; two slots leaked in.

### §12.4. Answers to the 8 Slice-2 questions

**1. Do Class C and Class D actually coexist in Ruby's top_k?**
**Yes.** In 3 of 4 queries (Q-A, Q-B, Q-D) both classes appeared. Q-C had only 1 Class C but 4 Class D, still a mix.

**2. On a Ruby-specific query (Q-A), does her Class D expertise survive?**
**Yes at rank 0.** Ruby's autobiographical chunk (dist 0.6231) held rank 0 by a margin of 0.058 over the closest Class C intruder (rank 2 at 0.7435). Ranks 3 remained Class D. But **2 of 5 slots (rank 2 and rank 4) were consumed by Class C chunks that do not answer the question**. Those slots displaced Ruby's D chunks that would have been rank 5–7 in the baseline (idx 6 bake-rotation, idx 3 cake lead-time, idx 2 pastries). Whether that displacement matters depends on whether the K6 factual basis needed those 2 additional D chunks; for Q-A specifically it did not, since rank 0 already contained the answer.

**3. On a business-wide query (Q-B), does Class C appropriately dominate?**
**Yes but by a hair.** Class C landed rank 0 (dist 0.3758) but its Class D duplicate landed rank 1 (dist 0.3761) — a 0.0003 gap. Sub-percent embedding noise could invert this ranking. Rank 3 was also Class C. In production this is a functional GREEN but structurally FRAGILE — the same fact is being surfaced twice at nearly-identical distances, competing for the same K6 slot budget.

**4. On an ambiguous query (Q-C), what mixture appears?**
**C=1, D=4.** Class D dominated because Ruby's Class D KD is 2× the size of the Class C KD (10 vs 5 chunks) and her breads section is a strong direct match. Class C sourcing chunk sneaked into rank 1 (dist 0.4454) beating the baseline rank-1 Class D by 0.046. Mix looks natural.

**5. Can Class C occupy all five slots?**
**Not observed under these conditions.** Maximum Class C occupation was 2/5 (Q-A, Q-B, Q-D). Given that Class C has 5 chunks total and Class D has 10, and cosine ranking chooses whichever chunks are closer in embedding space, Class D's larger surface area dominated. **Theoretical yes** (if a query embedding were perfectly aligned to Class C content and misaligned to Class D content), but not observed here.

**6. Can Class D occupy all five slots?**
**Not observed post-ingest.** Baseline had D=5 on all queries (only eligible KD). Post-ingest, max D was 4/5 on Q-C. **Theoretical yes** if a query perfectly aligns to Ruby-specific content and misaligns to shared business language; not observed with these four queries.

**7. Does the observed ranking align with the intended semantic distinction?**
**Mostly yes, with caveats.**
- Q-A (Ruby-specific): Class D rank 0 with the correct answer ✓. Class C intrusions at ranks 2 and 4 do not answer the question but do not displace the correct answer.
- Q-B (business/shared): Class C rank 0 ✓ — but with the Class D duplicate literally 0.0003 away in cosine distance. Semantic alignment survived; margin is fragile.
- Q-C (ambiguous): Class D rank 0 with the on-topic breads chunk ✓. Class C sneaks in at rank 1 with a related sourcing chunk. Natural mixture.
- Q-D (control): noise-floor ranking, mixture is not semantically meaningful.

**8. Is starvation merely theoretically possible or readily observable?**
**Observable and mild.** On Q-A, 2 of 5 slots were consumed by Class C chunks that do not answer the Ruby-specific question — those slots displaced Ruby's alternative D chunks. On Q-D (control), 2 slots were noise-level Class C hits. **No catastrophic starvation** was observed (Class D never lost rank 0 on a Ruby-specific query, Class C never occupied all 5 slots). But operator intent leaks: on Q-A, if K6 uses all 5 chunks, 40% of its factual basis for a Ruby-specific question is business-context boilerplate rather than more Ruby-specific detail.

### §12.5. Duplicate-chunk competition — direct observation

Q-B rank 0 vs rank 1 is the clearest measurement of the duplication effect:

| Position | Class | Chunk (paraphrased) | Cosine dist |
| --- | --- | --- | --- |
| Rank 0 | C | "Custom celebration cakes are a special-order item... require a minimum five-day lead time. Sculpted or heavily decorated cakes require a minimum ten-day lead time. Peak seasons push those lead times out further. A 50% deposit is taken at booking. Deposits are non-refundable inside 72 hours before pickup." | **0.3758** |
| Rank 1 | D | "lead time is a minimum of five days for standard tiered cakes and ten days for sculpted or heavily decorated cakes; peak seasons (spring weddings, December holidays) push those windows out further." (Ruby-voice) | **0.3761** |

**The same business fact is now stored twice with a 0.0003 cosine-distance gap.** The system surfaces both to K6, giving K6 the same fact twice in the top-2 factual-basis slots — reducing the diversity of the returned set. If Chris were to author 2 or 3 more Class C business facts that also live in Ruby's KD, the top-5 could plausibly become 3–4 duplicates plus 1–2 additional facts. **This is real starvation-adjacent behavior**, not a theoretical concern.

---

## §13. GREEN / YELLOW / RED VERDICT

**Verdict: YELLOW.**

Justification (definitions from Chris's Slice 2 §12):

- **Not GREEN** because ranking DOES produce surprising / fragile competition: Q-A had 2 Class C slots that don't answer the Ruby-specific question, and Q-B's rank 0/1 near-tie between duplicated facts is inherently fragile (any embedding drift could invert them, or worse, cause them to both fall out of top_k).
- **Not RED** because operator intent was NEVER inverted in a meaningful way: Ruby's authoritative Q-A chunk held rank 0; the business-wide Q-B correctly surfaced Class C at rank 0 (even if by a hair); the on-topic Q-C breads chunk held rank 0. Nothing in the results makes the model "unreliable enough that operator intent cannot be trusted."
- **YELLOW** because "the model works but ranking occasionally produces surprising/fragile competition" is exactly what §12 documents: duplicate chunks compete for the same slots at essentially tied cosine distance, and small-KD chunks like Class C's 5-chunk footprint leak into unrelated queries (Q-D). None of these break the product yet; they characterize a system that will get more fragile as more Class C material overlaps Class D.

**Scaling projection (unverified in Slice 2):** if Chris were to author 3–4 more Class C business KDs of similar size, or migrate more of Ruby's business facts into Class C without pruning Class D, the duplicate-tie behavior observed at Q-B would multiply. At 3× duplication, top-5 could plausibly become 3–5 duplicates of the same fact, starving unique Ruby content. This is a scaling risk, not a current failure.

---

## §14. PRODUCT-OPTIONS REVISIT (Slice 2 evidence integrated)

Recap of Slice 1 §8.5 options:
- **P1** — Preserve current model; fix UI accuracy only.
- **P2** — Formalize two-lane retrieval (shared/canon + character-specific with independent budgets, persisted separately, K6-labeled).
- **P2-lite** — preserve schema; expose Class C/D in the SPA with correct copy; retrieve each with independent small budgets; merge/dedupe before K6; persist provenance metadata later.
- **P3** — Workspace → Universe → character inheritance.
- **P4** — Explicit `KnowledgeAudience` first-class construct.

**Slice 2 evidence bearing on each option:**

| Option | Bearing from Slice 2 |
| --- | --- |
| **P1** | *Preserve current model + fix UI copy only.* Slice 2 confirmed the mechanical eligibility works exactly as designed. But P1 does NOTHING about duplicate-chunk competition (Q-B rank-0-vs-rank-1 tie); the fragility observed at YELLOW would remain. P1 accepts that operator intent gets nudged toward whichever duplicate happens to be embedding-closer to a query. **Cheap; leaves the observed YELLOW behavior intact.** |
| **P2 / P2-lite** | *Independent budgets per scope, merge/dedupe before K6.* Directly targets both YELLOW findings — independent budgets fix the "2 Class C slots on a Ruby-specific query" leak, and dedupe-before-K6 collapses the duplicate business fact into one chunk. Persisting per-scope provenance lets downstream panels distinguish "canon vs expertise." **Best structural match to Slice 2 evidence; also the largest immediate lift.** P2-lite avoids schema churn but requires new retrieval + persistence surface. |
| **P3** | *Workspace → Universe → character inheritance rings.* Slice 2 did NOT test inheritance behavior. But per §15 below, the workspace-global concept may not correspond to a legitimate product need — which would undermine P3's premise. Also: P3 would compound the YELLOW behavior by adding a third tier of chunks competing in the same ranked pool, making the fragility worse without independent per-tier budgets. If P3 is pursued, it must be paired with per-tier budgets (essentially P2 + inheritance). |
| **P4** | *Explicit `KnowledgeAudience` first-class construct.* Not tested in Slice 2. Would require the biggest schema migration and SPA rework. Reasonable long-term north-star but massive move to make from a YELLOW verdict; overkill relative to the current characterization. |

**Emergent read (not a decision):** the Slice 2 evidence points most naturally at **P2-lite** — the current schema is fine (eligibility works), but the ranking layer is thin. Adding independent per-scope small budgets + dedup-before-K6 targets the two YELLOW findings directly. Chris's decision.

---

## §15. IS "WORKSPACE-GLOBAL" EVEN A THING THE PRODUCT NEEDS?

**Updated with Slice 2 evidence + Chris's clarification.**

Chris reports that the current Class A workspace-shared KDs in `chriss-workspace` (TANK, Hearth & Hollow set, Tulsi, Riggs) are **knowledge left behind by DELETED characters**, and that the current UI does **not allow him to delete those orphaned KDs**. This reframes the Class A footprint from "operator-intentional shared knowledge" to **"unintentional operator debt / orphan artifacts."**

This is an **operator report**, not yet a mechanically-proven root cause. Slice 2 does NOT investigate deletion lifecycle behavior. Recorded here for later, per Chris's Slice 2 §11 instruction.

### §15.1. Potential lifecycle hazard (carried, unresolved)

**Hazard statement (unverified — needs a dedicated lifecycle audit slice):**
> Deleting a character (teammate) may leave formerly-associated `KnowledgeDocument` rows with empty `spokespeople` M2M, potentially making them eligible as legacy workspace-shared (Class A) knowledge for every remaining legacy teammate — regardless of the operator's original intent.

**What is known / not known:**
- **Known (Slice 1 §2):** empty `spokespeople` M2M is the mechanical signal for "broadcast-eligible to all teammates in scope." An orphan KD (formerly attached to a since-deleted character) that ends up with `spokespeople=∅` would inherit that broadcast eligibility.
- **Not known:** whether teammate deletion in fact leaves KDs with empty M2M (vs. cascading, vs. preserving inert M2M rows). This depends on `KnowledgeDocumentSpokesperson.on_delete` semantics + any signal handlers.
- **Not known:** whether the current SPA offers any KD-deletion affordance for these orphans, or whether the only available lifecycle actions are attach/detach on Spokesperson pages (which are unreachable if no target character exists).

**Follow-up question (deferred):** dedicated read-only audit slice — inspect `on_delete` on `KnowledgeDocumentSpokesperson`, inspect any `post_delete` signal handlers on Teammate, inspect SPA delete affordances on `/workspace/knowledge/{id}`, and construct a synthetic teammate-delete probe in a scratch workspace to confirm what happens to the M2M row. **Not undertaken in Slice 2.**

### §15.2. Product implication if the orphan hypothesis holds

If Chris's operator report is mechanically correct, then Class A's current population isn't a product intent at all — it's a lifecycle artifact. That reframes §15's answer sharply:

- The **product question** is no longer "should workspace-global exist?" but "should orphan KDs quietly become workspace-global?"
- The **retrieval implication** is real: Mason (legacy) currently retrieves 9 orphan-derived Class A KDs (TANK, Tulsi, all 6 Hearth & Hollow docs, Riggs). If Mason's synthesis mixes automotive-financing and bookstore facts on any query, that's the orphan hazard actively contaminating output.
- The **decision options** shrink:
  - **A** Cleanup + policy: add a KD-delete affordance for orphans; policy that character deletion cascades or explicitly re-scopes attached KDs.
  - **B** Rename: "workspace-global" is renamed to "unassigned" (which is what it IS today for orphans) with an explicit "do you actually want this shared, or is this stale?" flow.
  - **C** Remove: workspace-global scope is deprecated entirely; all KDs must belong to a Universe.

None of these are Slice-2 decisions.

### §15.3. Updated read of §15

Prior read (Slice 2 pre-approval): "workspace-global may not correspond to a legitimate product need."

**Updated read:** if the deleted-character-orphan hypothesis holds mechanically, then the current workspace-global slot doesn't just lack a clean product need — it's actively **broken lifecycle debt**. This strengthens the case that P3 (workspace inheritance) is a poor product direction, and increases the case for either P2-lite (which keeps workspace-global as a rarely-used explicit scope with correct UI copy) or an explicit deprecation of Class A.

**Chris's product-model decision still awaits.**

---

## §9. UI OBSERVATION LOG — CLASS C CREATION PATH

*Populated with Slice 2 evidence. The Class C KD in §11.6 was created via the ingestion API (`apps.embeddings.ingestion.ingest_text` + `embed_document`) rather than the SPA form. The following observations characterize what the SPA WOULD show if Chris performed the identical creation via the browser, grounded in the Slice 1 §5 SPA forensic audit of `web/src/routes/workspace/knowledge.tsx`.*

**Step-by-step operator flow to create the exact Slice 2 KD via the current SPA:**

1. Navigate to `/workspace/knowledge`. Empty-state or list view. No affordance yet.
2. Click "Paste" tab (default) in the "Add knowledge" section.
3. **World / Universe dropdown (required):** operator sees the label `"World / Universe"` and three option groups — placeholder (`"— Pick a scope —"`, disabled), `"None (legacy — visible to workspace-wide legacy teammates only)"`, and the workspace's Universes. To create Class C, the operator picks `"Fox & Flour Bakery"`. Help text: `"Pick a world to scope this doc to that world's characters, or pick "None (legacy)" to make it visible to legacy (pre-Universe) characters."`
4. Enter title: `Fox & Flour Bakery — House Policies & Hours`.
5. Paste content: the exact Option A markdown.
6. No spokesperson-assignment field exists on the create form. The operator does not see a "share with everyone in Fox & Flour" option, an "Ruby-only" option, or any indication of what the M2M defaults to.
7. Click `"Add to knowledge"`. Loading state: `"Ingesting…"`.
8. On success: form clears, list refreshes.

### §9.1. Does the UI make "Share this knowledge with everyone in Fox & Flour" legible?

**No.** Evidence:

- **The Universe dropdown itself is legible** for "which world does this belong to" — the required selection + the help text communicate this clearly.
- **The empty-spokespeople-means-broadcast mechanic is NOT communicated at any point in the create flow.** The operator does not see any field labeled "share with everyone in Fox & Flour," "restrict to specific characters," "audience," or equivalent. The M2M defaults to empty because there is no field to populate, not because the operator explicitly chose "share."
- **The post-save state does not confirm the semantics.** The Knowledge list page (`/workspace/knowledge`) shows no per-row Universe badge and no scope indicator. From the list, the newly-created Class C KD is visually indistinguishable from any Class A KD.
- **The Knowledge detail page (`/workspace/knowledge/{id}`) does not display `universe` or `spokespeople`** in its metadata grid (per Slice 1 §5.4). Operator cannot confirm the scope of the doc they just created.
- **The Spokesperson-detail Knowledge panel WILL surface this KD** under Ruby (as expected — she's the only teammate in Fox & Flour). The row label will read `"Visible to every spokesperson in the workspace · 5 chunk(s)"`. That label is **factually wrong**: this Class C KD is visible only to Ruby (and any future Fox & Flour teammate), not to every spokesperson in the workspace. Mason, Penny, Mike, Repo Red, Patch, Rivet, Riggs cannot retrieve it.

### §9.2. Concrete Slice 1 gap now demonstrated with a live specimen

Prior to Slice 2 there were zero live Class C KDs in production. Slice 2 created one (`8f825c98-…`). The Slice 1 UI gaps §5.7 predicted are now concretely observable:

- **Class C is visually indistinguishable from Class A in list + detail views.** Slice 2 KD is the counter-example needed to make this concrete.
- **The "Visible to every spokesperson in the workspace" label is now provably wrong** for a live doc. Anyone reading it about `8f825c98-…` would conclude Mason can retrieve it. He cannot (verified in §12.1).
- **The operator cannot answer "who will retrieve this?" from the SPA.** They would have to visit every Spokesperson detail page one-by-one.

### §9.3. Legibility verdict

**No.** The SPA does not make "Share this knowledge with everyone in Fox & Flour" a legible operator action. Class C creation succeeds only because the operator's Universe selection is required and the M2M-empty default happens to produce the correct behavior — not because the SPA explains that shape. The empty-M2M mechanic is entirely implicit in the current UI.

---



---

## §16. CHECKBOX STATUS

**Evidence-backed only. `[x]` = done and verifiable from either this doc, the source, the DB, or the commit trail.**

- [x] Slice 1 committed and pushed (commit `e7ff4a4`, main == origin/main verified)
- [x] Slice 2 durable doc created (`docs/design/SESSION_274_UNIVERSE_SHARED_KNOWLEDGE_DOGFOOD.md`)
- [x] Existing Ruby KD inspected for overlap (§3 — full content read, 8-section overlap table with Ruby-specific vs business/world split; also §3.2 enumerates the 13 business-fact classes)
- [x] Proposed Class C content documented (§4 — Option A extract-only draft + Option B invented-facts candidate list)
- [x] Chris approved Class C content (Option A EXTRACT-ONLY exactly as drafted; explicit duplication with Ruby's Class D KD preserved as intended stress-test material; no Option B invented facts approved)
- [x] Baseline retrieval probes complete (§11 — Q-A/B/C/D captured with rank/dist/class/doc/chunk_uuid/excerpt; all 20 slots Class D as expected pre-ingest)
- [x] Class C KD created (§11.6 — Doc UUID `8f825c98-f420-4867-8700-6d4db6832d9d`, Option A content exactly)
- [x] Class C ingestion verified (§11.6 — universe=Fox & Flour, status=processed, 5 chunks all embedded, hash=`d205f813…`)
- [x] Empty M2M verified post-ingest (§11.6 — spokespeople count=0)
- [x] Ruby eligibility verified (§12.1 — Class C `8f825c98-…` + Class D `74e7f18f-…` both eligible)
- [x] Cross-Universe exclusion verified (§12.1, §12.2 — Patch + Rivet see zero Fox & Flour Class C hits on business-flavored probe)
- [x] Legacy exclusion verified (§12.1, §12.2 — Mason sees zero Fox & Flour Class C hits; his eligible pool is 9 Class A only)
- [x] Post–Class-C retrieval probes complete (§12.3 — Q-A/B/C/D re-run with full rank/dist/class/doc/chunk_uuid capture)
- [x] Before/after matrix complete (§11 baseline + §12.3 post-ingest; §12.5 direct duplicate-chunk competition observation)
- [x] Starvation / coexistence verdict recorded (§12.4 — all 8 questions answered from evidence; §12.5 direct-observation table)
- [x] UI Class C operator-path observations recorded (§9 — full walkthrough grounded in Slice 1 §5 SPA source audit; §9.1 legibility answered "no"; §9.2 lists Slice-1 gaps now concretely demonstrated with live specimen `8f825c98-…`)
- [x] GREEN / YELLOW / RED verdict recorded (§13 — YELLOW, with justification against all three definitions)
- [ ] Render decision made (§8) — deferred; Slice 2 stop condition is "STOP and wait for Chris" before any render
- [x] Product options revisited with Slice 2 evidence (§14 — Slice 2 evidence integrated into P1/P2/P2-lite/P3/P4 assessment; emergent read points at P2-lite; no decision made)
- [x] Workspace-global-necessity assessment finalized for Slice 2 (§15 — updated with Chris's deleted-character-orphan clarification; hazard statement recorded as carried follow-up, not investigated in this slice)
- [x] Deleted-character / orphan-KD lifecycle hazard recorded as product finding (§15.1 — hazard statement + follow-up scope; no fix attempted in Slice 2)

---

## §17. CURRENT REPOSITORY / RUNTIME STATE (Slice 2 open)

| Check | Value |
| --- | --- |
| Git HEAD | `e7ff4a471f03f91be12e6e35a245ab1c7aedfb7c` |
| `origin/main` | `e7ff4a471f03f91be12e6e35a245ab1c7aedfb7c` — matched |
| Working tree | clean at Slice 2 open (this doc will show as `??` next commit boundary) |
| Django `:8010/admin/` | 302 (verified Slice 1 §1) |
| Media-engine `:8001/health` | all mocks false; llm_model=gpt-4o-mini (verified Slice 1 §1) |
| Vite `:5174/` | 200 (verified Slice 1 §1) |
| Celery | 1 node online (verified Slice 1 §1) |
| Environment | no MOCK / EXPERIMENT drift on Django/media/celery PIDs (verified Slice 1 §1) |
| DB port | 5434 (from running Django env; all Slice 2 shell probes will use this) |

---

**Slice 2 pre-approval scaffolding populated with post-ingest evidence. Second stop reached — waiting on Chris's decision on the optional Slice 3 render.**

---

## §18. SLICE 2 SECOND-STOP SUMMARY (for handoff)

- Baseline (§11) captured before any DB mutation. All 20 slots Class D (only KD eligible pre-ingest).
- Class C KD `8f825c98-f420-4867-8700-6d4db6832d9d` created in `chriss-workspace` under Fox & Flour Bakery Universe, spokespeople=∅, 5 processed+embedded chunks. Ruby's Class D KD, persona, and NarrativeMemory unchanged.
- Post-ingest eligibility (§12.1) exactly matches the Slice 1 truth table: Ruby YES, Patch NO, Rivet NO, Mason NO.
- Post-ingest retrieval (§12.3) shows Class C + Class D coexist in Ruby's top_k with mild starvation on Q-A (2 unused Class C slots) and a fragile 0.0003 near-tie between duplicated business facts on Q-B. Ranking generally aligns with intended semantic distinction. No catastrophic starvation. Class C never occupied all 5 slots.
- **Verdict: YELLOW.** Model works, but ranking produces surprising / fragile competition when Class C duplicates Class D content.
- UI observation (§9): the SPA does not make "Share this knowledge with everyone in Fox & Flour" a legible operator action; the empty-M2M mechanic is entirely implicit; post-save Class C is visually indistinguishable from Class A; the "Visible to every spokesperson in the workspace" label is now provably wrong for a live specimen.
- Slice 1 §8 product-decision brief updated with §14: Slice 2 evidence points most naturally at **P2-lite** (independent per-scope budgets + dedup-before-K6 + persist provenance). Not a decision — Chris chooses.
- Chris's deleted-character-orphan clarification recorded in §15.1 as a follow-up hazard requiring a dedicated read-only lifecycle audit slice; not investigated in Slice 2.

**Slice 2 does NOT render Ruby.** That decision awaits Chris.

