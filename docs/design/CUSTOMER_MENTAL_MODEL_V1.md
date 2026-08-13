# CHARACTER OS — CUSTOMER MENTAL MODEL RECONCILIATION V1

> **Later ontology (added 2026-08-08):** SESSION 250 later produced
> [`IDENTITY_MODEL_V1.md`](IDENTITY_MODEL_V1.md), an
> implementation-agnostic ontology of what an AI creator's identity
> IS (CORE / EXPRESSION / GOVERNANCE). The object-model discussion
> in §3 of this document is superseded conceptually by that ontology
> — but this document is preserved unchanged as design history from
> its point in time. The reading order for the full design-history
> arc lives in
> [`CUSTOMER_EXPERIENCE_REVIEW_INDEX.md`](CUSTOMER_EXPERIENCE_REVIEW_INDEX.md).

## Design lock for the customer-facing product model

**Status:** proposal (design lock candidate)
**Author:** synthesized from SESSION 250 persona review + shipped SPA copy survey
**Purpose:** define what the customer experiences as a product, so any subsequent UX work has a mental-model contract to build against
**Not-goals:** implementation, string substitution, code, redesign of components, changes to backend models, changes to Step 10 sequencing, changes to any contract
**Companions:** persona review (SESSION 250), `CLAUDE.md`, `docs/design/CUSTOMER_JOURNEY_V1.md`, `docs/CHARACTER_OS_WHAT_IT_IS.md`
**Do not treat this as final until:** (a) the operator ratifies the customer object model in §3; (b) the "spokesperson" noun question in §4 is resolved; (c) the IA in §5 is walked against the top three go-to-market personas.

---

## §1 — Evidence summary from the persona review

Ten personas were walked through the shipped SPA copy (SESSION 250 review). The specific reactions per persona are in that review; the aggregate signal that this document is built on is:

- **The wizard + welcome page + first video** is a genuinely delightful experience 8/10 personas can complete without help. Everything after that first-video completion feels like a different product built by a different team.
- **A single word — "spokesperson" — filters out 5-7 of 10 target personas.** The teacher does not have a spokesperson; the pastor does not have a spokesperson; the therapist does not have a spokesperson; the coach IS himself, not a spokesperson. Only the museum curator and (loosely) the consultant use the word naturally.
- **Engineering vocabulary is cumulative, not individually fatal.** No single word (render, composition, provision, bake, K6.4, mock, primitive, chunk, pipeline) sinks the product on its own. Together they establish that Character OS was built by engineers for a technical audience — which contradicts the audience the wizard and empty-state copy actually invite in.
- **The product's most differentiating capability (K6.4 grounded fact-checking) is unusable by the personas who need it most** because it is presented as a mode-selector on a form with an internal codename.
- **The product's information architecture treats implementation objects as first-class nav items.** Assets, Videos, Compositions, and Bundles are four different lenses on largely the same thing. Sara, Rob, Marcus, and Pastor Dan all lost time hunting for something they had just made.
- **The product's operator surfaces are exposed in the customer nav** ("bootstrap-review", "provider-status", "engine-connections"), which every persona either avoided or, in Rob's case, opened and immediately worried about polish.
- **Data / privacy / retention has no surface** in the product. This is a hard block for every regulated vertical (therapist, dentist, accountant, teacher).
- **The onboarding tour is the product's best surface AND uses its worst vocabulary at the highest-stakes moment.** "Provision your first spokesperson" is what the very first minute of use asks the user to do.
- **The verifier is a moat AND a wall.** The dentist chose "strict" (correct instinct), got a legitimate block on an unsupported medical claim (K6.4 doing its job), and had no path to resolve it. The most valuable thing in the product is currently invisible-to-the-competent-user.
- **The wizard, welcome page, and empty states already speak in a warm, plain, encouraging voice.** They are the model the rest of the product needs to grow toward.

Two consolidated observations frame the rest of this document:

1. **The product has two voices.** One in the wizard/welcome/empty-states (warm, plain, honest). One everywhere else (engineering, ceremonial, insider). The ceremonial one is polarizing (helps 3/10, distances 5/10). The engineering one is universally negative for non-engineers.
2. **The nav is a map of the backend, not of the customer's day.** Every top-level item corresponds to a backend model or process concept. No item corresponds to a customer job.

---

## §2 — What the customer believes they are doing

Before naming objects or nav items, the question is: **what is the atomic unit of value the customer perceives?**

### Testing the "persistent AI communicator" hypothesis

The operator hypothesis is that Character OS is less about content creation and more about **creating a persistent AI communicator that can represent, teach, explain, guide, promote, or interact on the user's behalf**.

I tested this against the persona review. Results are mixed and instructive.

**Where the hypothesis is confirmed:**

- Rob (consultant) explicitly describes what he built as "an AI version of me" that "answers prospect questions in DMs + generates short video takes." The persistence, the multi-modal use (chat + video), and the "on my behalf" character are all present.
- Pastor Dan tells his wife about talking to "Pastor Dan Video" — he perceives it as a continuous entity, not as a video-generation tool.
- Coach Mike sees himself as *hiring* an AI clone to reduce his personal recording burden. The AI is persistent; it accumulates knowledge; he trains it once and it works forever.
- The wizard flow itself is designed around this: identity → portrait → voice → confirm. It's an *identity-creation* flow, not a *content-creation* flow.

**Where the hypothesis is weaker:**

- Marcus (realtor) is not creating a persistent communicator. He is creating a *video factory*. His mental model is closer to a mail-merge template than a persona. He does not talk to his spokesperson; he does not care what it knows. He just wants 25 personalized videos this week.
- Ms. Patel (teacher) is closer to Marcus. She wants weekly parent updates. The "persistent AI communicator" framing is over-scoped for her; she wants a *recurring video maker*.
- Sara (curator) creates a *character per exhibit* (The Docent for one show; maybe another character for the next). Her mental model is per-exhibit, not persistent.
- Jamie (coffee shop) created "Bean" — a mascot — but her actual jobs are (a) weekly Reels and (b) FAQ answerer. Bean is instrumental to both, but she thinks about the *outputs* more than about *Bean*.

**Reconciled hypothesis (proposed):**

> Character OS gives the customer a **named, on-camera identity they design once and use many times** — to make videos, hold live conversations, run personalized outreach, and reply to questions — grounded in things they've taught it. The persistence is real but is not the object of desire; it is the *substrate* that makes many downstream outputs feel consistent and true.

This reframing matters because it says: **the AI identity is not the product; it is the enabling condition for the product. The product is what the user does with it.**

Practical consequence: the product should introduce the AI identity as the *setup step*, then quickly move the user into *doing* things with it. The current product does the opposite — after the wizard, the user lands on the spokesperson detail page, which is an admin surface, not a doing surface.

### The customer's true atomic unit

Across all 10 personas, the atomic unit of *value* the customer wants is a **piece of communication that reaches an audience** — a video, a live conversation, a personalized outreach, a shared social clip. The **AI identity is the tool** that produces those things.

This means the product's mental model should be:
- **The tool** (the AI identity) — set up once, refined over time
- **What the tool draws on** (what you've taught it)
- **What the tool produces** (videos, conversations, personalized messages, social variations)

Three concepts. Everything else is either an internal detail or an advanced surface.

---

## §3 — Customer object model

The smallest set of concepts a customer genuinely needs to understand.

### The three customer-first objects

**Object 1 — Your AI (the tool the customer builds)**
- What it is: the named, on-camera identity the customer designs. Has a face, a voice, a personality, a business/purpose brief, and a set of things it knows.
- Why it exists in the customer's mind: because the wizard produces it and the customer named it. Bean, Pastor Dan Video, The Docent, Marcus Digital, Ms. Patel Assistant.
- What the customer does with it: reviews/adjusts it; teaches it more; uses it to make things.
- Class-noun question: unresolved. See §4 — the correct class term is not "spokesperson" for most personas; the correct class term may in fact be nothing (the user's chosen name is the noun) with contextual meta-terms ("your team" for collections, or category-specific like "your presenter" / "your character" per use case).

**Object 2 — What it knows (the material the AI draws on)**
- What it is: the documents, notes, PDFs, URLs, and pasted text the customer attaches so the AI can speak/answer with real content.
- Why it exists in the customer's mind: because the welcome page's most successful line is "*{name}* doesn't know your **specifics** yet." That single sentence gives the user the mental model.
- What the customer does with it: uploads/pastes/imports; occasionally deletes or replaces.
- Class-noun candidates: "sources," "materials," "reference documents," "what it knows," "brief" (already used in scattered places). "Knowledge" is not wrong but is elevated; "sources" is more concrete and matches how educators/researchers already think.

**Object 3 — What it makes (the outputs the customer publishes)**
- What it is: videos, conversations, personalized outreach messages, social variations. The stuff the customer came here to produce.
- Why it exists in the customer's mind: this IS the reason for the product.
- What the customer does with it: makes them; browses them; downloads or shares them.
- Class-noun candidates: "outputs" is too generic; "videos" is the primary noun for 8/10 personas; the product needs additional nouns for non-video outputs (a live conversation transcript is not a video). Working proposal: use the specific noun where possible ("videos", "conversations", "campaigns", "shares") and use a shared library surface where the user browses across kinds.

### Disposition of the current 10 top-level customer-facing concepts

For each, one of four dispositions:
- **A — Keep as a customer concept:** the customer already thinks in this term and it maps to their mental model.
- **B — Hide (implementation-necessary but not user-facing):** the capability is essential but the term is engineering. The concept must not appear in normal customer workflows.
- **C — Move to advanced/operator surface:** the concept is legitimate for power users or operators, but does not belong in the primary customer nav.
- **D — Eliminate from customer mental model:** the concept is a legacy backend framing that no persona actually thinks in.

| Concept | Persona-review evidence | Disposition | Rationale |
|---|---|---|---|
| **Spokesperson** | 5-7 of 10 personas reject the noun. The wizard produces a *named* AI that the user thinks of by its chosen name. | **Class term: A (retained) BUT the specific word is under review — see §4.** The class concept ("the AI you built") is essential. The class term "spokesperson" is not. | The concept is atomic and load-bearing. The word is a leading candidate for change. See §4 for options. |
| **Knowledge** | Every persona who uploaded something understood what it was for. The word "knowledge" is acceptable; "workspace knowledge" is jargon; "corpus" is worse; "ingest" is worst. | **A (retained), plain-name pass on wrapping terms.** | Concept is atomic and correct. The verbs and adjacent nouns ("workspace knowledge", "ingest", "corpus", "chunks") are the friction, not "knowledge" itself. |
| **Transcript** | Pastor Dan understood "Transcripts are created automatically at the end of a live session"; Coach Mike understood transcript-of-recording; nobody understood "Transcript miner." | **A for transcript-as-noun; concept is retained.** The metaphor "miner" is playful for some, opaque for others; it is a candidate for a plainer name. | The customer does know what a transcript is. The mining flow (which yields shareable highlights) is legitimate; its name is not load-bearing. |
| **Script** | Marcus, Ms. Patel, Coach Mike, Priya all recognize "script" as "the words the AI will say." No persona bounced on the word "script." | **A — keep.** The wrapping ("K6.4 verifier mode", "K2 knowledge retrieval") is the problem, not the word. | Plainest technical noun in the current product. |
| **Recipe** | Sara appreciated the metaphor; Coach Mike ignored it; several personas were unsure whether a "recipe" was a template or a produced thing. | **A — retained as a concept BUT the class term is ambiguous.** Candidate replacements: "template," "video kind," "starting point." | The concept (pick a starting shape for what you're making) is correct. The word "recipe" is friendly but ambiguous. |
| **Campaign** | Marcus and Ms. Patel both recognized this from marketing/education vocabulary. No persona bounced on the word. | **A — keep.** | Load-bearing feature; existing word is understood. |
| **Bundle** | 5/10 personas confused. Coach Mike hooked on the value ("$0 incremental cost") but not the word. Nobody thinks about "bundling." | **B — hide the term; keep the capability.** Candidate replacements: "share to social," "cross-post," "publish." | The capability is powerful; the word is IT-shelf-speak. |
| **Video** | Universal comprehension. This should be the *primary* customer noun. | **A — keep AND promote.** Videos should sit at the top of the nav for most personas. | The plainest noun in the product; the object every persona came for. |
| **Asset** | No persona thinks in this term. Accounting-adjacent. Overlaps confusingly with Videos, Bundles, Compositions. | **D — eliminate from customer nav.** The capability (browse everything my AI has produced) is real; the correct customer surface is a "Library" that browses across kinds — not a nav item called "Assets." | The word is a data-model term, not a customer term. |
| **Composition** | Zero comprehension across all personas. Not one persona used or recognized the word. | **D — eliminate from customer surface entirely.** The composition detail page is a *how-it-was-made* view that belongs behind progressive disclosure on the video detail (e.g., "How this video was built"). | The pure engineering concept. No customer thinks in this term. |

### Concepts not currently in the top-level nav but present in the customer's world

- **Live conversation** — the "Talk to {name}" feature. Currently accessed only from the spokesperson detail page. Every persona who tried it enjoyed it; some tried to find it later and couldn't remember where it lived. This should be first-class in the customer's model, not buried.
- **Chat / DMs / async conversation** — Rob's use case. Currently exists under "Conversations" (a route that has no nav item). Should be surfaced.
- **Your library** — the browsable set of outputs. Currently split across Videos / Assets / Bundles.

### The proposed customer object graph (in customer-language, not engineering-language)

```
You have a Workspace (your Character OS account).

Inside it, you build one or more AIs (name TBD — see §4).
Each AI has:
  - a face and voice (identity)
  - a personality + brief (who it is)
  - things it knows (sources you've given it)

With each AI, you can:
  - make videos (single or in a campaign)
  - have a live conversation
  - chat by text
  - share videos to social platforms
  - view a running record of what it has produced (library)

Everything else the product does is either:
  - handled behind the scenes (rendering, verification, storage)
  - for advanced users or the operator
```

The intent of this graph is that a customer, asked "what is Character OS?", could answer using only the words in bold in the paragraph above.

---

## §4 — Vocabulary contract

Not a substitution table. For each concept, this section states **what the customer needs to understand**, then proposes **candidate language** with rationale and open questions.

### 4.1 The "spokesperson" noun — the open question

The persona review makes clear that "spokesperson" is the wrong word for 5-7 of 10 target users. What is less clear is what the right word IS. Three candidate directions, each with real cost:

**Direction A — Single generic class term for the AI identity.**
Candidates: "AI presenter," "AI character," "AI helper," "AI representative," "AI persona."
Cost analysis:
- **AI presenter** — market-adjacent (HeyGen, D-ID use it). Fits video-first use. Weak for: pastors (a pastor doesn't have a "presenter"), teachers (an assistant isn't a presenter), consultants (Rob doesn't "present," he *thinks in public*).
- **AI character** — matches the product name ("Character OS"). Warm; educators, pastors, and mascot-builders (Jamie/Bean) already use "character." Weak for: consultants and coaches who think of the AI as themselves, not as a character.
- **AI helper** — plain; matches Ms. Patel, Dr. Alvarado, Priya. Weak for: creators (Rob, Coach Mike — an "AI helper" isn't glamorous enough to represent their brand).
- **AI representative** — matches the professional-services personas (dentist, therapist, accountant). Weak for: coaches, teachers, mascots.
- **AI persona** — psychology-adjacent, weakly technical, mildly cold; nobody bounces on it but nobody warms to it either.

**Direction B — Contextual class terms; no single word.**
Use different words in different contexts. In the sidebar: "Your team" (collection). On the welcome flow: use the user-chosen name ("Meet Bean"). On the empty state: "Build your first AI" or "Add someone new." In documentation/marketing: whichever single term ends up chosen for Direction A.
Cost: consistency risk; a term used only sometimes can feel accidental. Benefit: the user's name for their creation carries the mental model, and the class term never has to be a bad fit.

**Direction C — Elevate "character" as the class term AND lean into the product name.**
Character OS ships as a product where every AI is a "character." The name "Character OS" already implies it; the operator has already invested branding around "Character." Coach Mike says "my character," Jamie says "Bean, the character," Sara says "The Docent, a character for the exhibit," Rob says "my character for LinkedIn," Ms. Patel says "the class character."
Cost: professional-services personas (therapist, accountant) may find "character" too casual for their brand.

**My leaning (not a decision):**
- **Direction B is safest** and preserves the wizard's already-good pattern (user names the thing; the system respects the name).
- **If a single term must be chosen, "character" is the strongest candidate** — it aligns with the product name, is broad enough to cover mascots + personas + on-camera identities + institutional voices, and is warmer than "presenter" / "representative" / "persona."
- **The word "spokesperson" should be retired from customer surfaces** irrespective of which direction is chosen. It is unrecoverable for the majority of target users.

**Unresolved (operator decision required):** which direction is the product's spine. This is the single most consequential vocabulary decision in this document.

### 4.2 Vocabulary that should not appear on customer surfaces

For each: what the customer needs to understand; candidate customer-facing language; what NOT to do.

**Render / Render queue / Rendered**
- What the customer needs to understand: their video is being produced; it may take some time.
- Candidate language: "make," "making," "made," "ready." "Your video is being made" / "Video ready" / "Making Bean's video…"
- Do not: replace with "generate" (equally engineering-y) or "process" (equally cold).
- Open question: retain "render" as a term for *the technical process of producing the file* in an operator/audit context; it is precise there.

**Composition**
- What the customer needs to understand: nothing. This is an implementation term.
- Candidate language: none. The concept should be invisible.
- Do not: replace with "video project" (adds a new noun that isn't necessary — the video is the project). The composition detail page's purpose is "How this video was made" (progressive disclosure on the video detail), not a top-level object.

**Provision / Provision your first spokesperson**
- What the customer needs to understand: build the AI that will be the face of what you make.
- Candidate language: "build," "create," "set up," "meet." "Build your first character" / "Set up your first AI" / "Meet the AI you'll build."
- Do not: use "commission" (already in place; sounds PE-firm). "Provision" is unrecoverable for non-IT users.

**Fire / Fire a composition**
- What the customer needs to understand: start making a video.
- Candidate language: "make," "start," "run." "Make a video" / "Start making" / "Run the template."
- Do not: use "fire" as a verb on customer surfaces at all. "Fire" is developer/CLI idiom.

**Ship**
- What the customer needs to understand: the thing is ready / done.
- Candidate language: "done," "ready," "published," "sent."
- Do not: use "ship" as a verb on customer surfaces.

**Ground / Grounding brief**
- What the customer needs to understand: the AI's answers are based on what you've taught it, not made up.
- Candidate language: "based on what you've taught it," "using your uploaded sources," "grounded in your materials" (only if "grounded" is explained inline; safer to avoid).
- Do not: use "ground" as a technical term. It's LLM-culture, not customer-culture.

**Bake / Re-bake avatar**
- What the customer needs to understand: their AI's face needs to be prepared before it can appear in videos or live sessions; occasionally that preparation needs to be redone.
- Candidate language: "prepare," "generate face," "regenerate face." "Preparing Bean's face…" / "Regenerate face."
- Do not: use "bake." This is culinary metaphor with zero semantic grip.

**K2, K6, K6.4, K6.6**
- What the customer needs to understand: nothing. These are internal version identifiers for the retrieval + verification systems.
- Candidate language: for K2 (knowledge retrieval), simply describe as "your uploaded sources" or "what your AI knows." For K6.4 (claim verification), simply describe as "fact check against your sources" or "double-check what your AI says against your uploaded sources." K6.6 (opener pinning) is a per-field feature, not a class name.
- Do not: use the "K" codes on customer surfaces ever. They are internal.

**Mock / Mock mode**
- What the customer needs to understand: whether the video was made with the real AI provider or was a test with a placeholder.
- Candidate language: for most customers, mock mode should not be visible; it's a development-time state. If visible: "test video," "sample," "preview only." Better: real mode is the customer's default and mock mode is an operator preference; the customer never sees the word "mock."
- Do not: expose "mock" as a badge on customer-facing outputs. The word implies "fake" and creates trust anxiety.

**Pipeline**
- What the customer needs to understand: nothing. This is engineering.
- Candidate language: none. The concept should be invisible. "Click any row for the full pipeline view" should become "Click any row to see the video."
- Do not: use "pipeline" on any customer surface.

**Primitive**
- What the customer needs to understand: nothing. This is a step-in-a-composition concept.
- Candidate language: on the "how it was made" progressive disclosure, use plain descriptions of each step ("Wrote the script," "Recorded the audio," "Assembled the video"). Never call a step a "primitive."
- Do not: expose the word "primitive" on customer surfaces.

**Embedding / Chunk**
- What the customer needs to understand: their uploaded material was processed so the AI can search it.
- Candidate language: "indexed," "processed," "ready to search." Avoid explaining the mechanism unless the user asks.
- Do not: expose "embedding" or "chunk" as user-facing units on knowledge/document detail pages. The count of chunks is not useful to the customer.

**Corpus, Ingest, Ingested via**
- What the customer needs to understand: the material they've uploaded, and where each piece came from.
- Candidate language: "sources," "your uploads," "added from paste/upload/URL/search." "Added via" is plainer than "ingested via."
- Do not: use "corpus" or "ingest" as customer nouns/verbs.

**Frozen candidate ID, Bootstrap run, Promotion audit**
- What the customer needs to understand: nothing. Operator-only vocabulary.
- Candidate language: none. These live behind an operator gate.
- Do not: expose these on any customer-visible surface, including the settings tab.

**Runway (as a provider name shown to customers)**
- What the customer needs to understand: their AI is powered in part by third-party technology; certain sessions have caps set by that partner.
- Candidate language: for cap explanations, describe the cap without naming the provider ("Live sessions last up to X minutes"). For trust/compliance contexts, name the providers on a dedicated page (see §5, "Data & Providers").
- Do not: expose "Runway" on live-session preflight copy in a way that makes the user wonder about upcharges or contracts.

**Verifier mode: strict / warn / off / default (warn)**
- What the customer needs to understand: how careful they want the AI to be about staying grounded in their uploaded sources.
- Candidate language: something like "Fact-check strictness: careful (recommended) / balanced / off." The trade-offs each mode makes should be described in plain terms next to the selector ("Careful means the AI will refuse to say things your uploaded sources don't support. Balanced flags claims but still shows them. Off skips the check.")
- Do not: expose "K6.4" as a label; do not use "strict"/"warn" without an explanation of what happens under each.

### 4.3 Vocabulary that is fine and should be preserved

These words already work. Do not change them.

- **Video** / **Videos** — plainest and most-comprehended noun in the product
- **Conversation** / **Chat** — universally understood
- **Campaign** — recognized from marketing/education
- **Script** — recognized universally when it means "what the AI will say"
- **Portrait** — clearer than "avatar" for most personas; already used in the wizard
- **Voice** — plain and correct
- **Sources** / **Documents** — plainer alternatives to "knowledge documents" that customers already use
- **Save** / **Cancel** / **Delete** / **Retry** — standard verbs; keep exactly as they are

### 4.4 The tone and voice contract

The wizard, welcome page, and empty states already speak in a voice the product should adopt everywhere. Its characteristics:

- **Warm without being cutesy.** "Meet Bean" not "Say hi to your new AI friend!"
- **Honest about limitations.** "*{name}* doesn't know your specifics yet." "If you talk to *{name}* before adding knowledge, they'll answer generically."
- **Concrete about next steps.** "Paste content or upload a PDF above. Every spokesperson in the workspace will be able to draw from it."
- **Plain about what things are.** "A spokesperson is the on-camera identity your workspace renders against — portrait, voice, and grounding brief." (This sentence is only 30% good — "spokesperson," "workspace," "renders against," "grounding brief" all need work — but the structure is the model: object + attributes + purpose.)
- **Never uses the user's job title against them.** "For your business" only if the user *is* a business. Teachers, therapists, pastors, curators are not businesses in the way the current copy assumes.

The polarizing italic-gold "§ N —" section-mark typography is a separate question — the persona review shows it splits the audience roughly 3/10 charmed, 5/10 alienated, 2/10 neutral. That is a design/brand-voice question rather than a vocabulary question. This document does not resolve it. Recommended: leave the current typography in place for now; flag it as an audience-fit question for a future brand pass.

---

## §5 — Information architecture

Proposed customer-facing IA. This is not a component design; it is a map of *what surfaces exist for the customer, in what order, and with what relationships.*

### 5.1 Two entirely separate products

**The customer product.** For anyone who signed up. Contains only the customer objects (§3), only the customer vocabulary (§4), and only the customer job flows (below).

**The operator product.** For staff/superusers. Contains bootstrap-review, provider-status, engine-connections, and any future admin surface. Lives behind a staff-only gate. Uses whatever internal vocabulary is precise; is not held to customer-tone constraints.

The current product mixes these. This must stop.

### 5.2 Customer navigation

**Proposed shape** (the six items a customer sees at the top of every page):

1. **Home** — dashboard; personalized "what to do next"; recent activity
2. **Your team** (or "Your AIs" or "Your characters" — see §4 open question) — the collection of AI identities the customer has built
3. **Sources** (or "What they know" — see §4) — the uploaded materials
4. **Make** — the templates + starting points for producing videos and other outputs (currently "Recipes")
5. **Library** — everything the customer has produced (videos + images + audio + transcripts, unified)
6. **Campaigns** — personalized-at-scale outreach

**What is removed from the top-level customer nav:**
- **Assets** (folded into Library)
- **Bundles** (becomes an action on a Library item — "Share to social" — not a separate concept)
- **Compositions** (invisible to the customer; the video detail exposes a "How this was made" progressive disclosure)
- **Tools** (the bridge-tool interactive-ask surface — arguable; either fold into a "Ask directly" affordance under the AI identity, or hide entirely until Rob-persona-scale demand justifies re-surfacing it)
- **Signature** (not part of the product's core loop — belongs on a settings or resource page, not the top nav)
- **About** (footer)
- All operator surfaces (staff-only gate)

### 5.3 Progressive disclosure and secondary nav

Below the primary six, contextual affordances live on the relevant object page:

- **Live conversation** — surfaced prominently on the AI's page (already is); should also have a discoverable path from Home
- **Chat/DMs** — surfaced prominently on the AI's page (currently is "Conversations" without a nav item)
- **Delete/archive** — on the object detail
- **Share to social** — an action on a video, not a separate nav item

### 5.4 Settings

A single **Settings** entry (footer or user-menu, not top nav):
- Account (email, password)
- Workspace (name, tier, usage, billing when it exists)
- **Data & Providers** — the currently-missing surface for regulated personas. Names third-party providers, explains what data goes where, offers export/permanent-delete, links to any compliance documentation
- Sign out

### 5.5 Operator/staff nav

**Entirely separate rail**, only visible when `is_staff=True`. Contains:
- Bootstrap review
- Provider status
- Engine connections
- (Future operator surfaces)

Uses internal vocabulary (bootstrap, provider, engine, K6.4, primitive, run, fingerprint) without translation. Is not part of the customer product and is not held to customer-vocabulary rules.

### 5.6 The first-mile customer flow (proposed)

The critical first 10 minutes:

1. **Sign up.** Email + password. Copy: warm and plain. No "commission your operating partner." No "The hour is irrelevant."
2. **Land on Home in tour mode.** Three steps, each in customer language:
   - Step 1: **"Build your first [character/AI/presenter — TBD]."** Description: "Give it a name, a face, and a short brief about who it is and what it talks about." CTA: "Get started."
   - Step 2: **"Give it something to work with."** Description: "Upload documents, paste notes, or add web links. Your AI will draw on these when it speaks — so it says real things, not made-up things." CTA: "Add sources."
   - Step 3: **"Make your first video."** Description: "Pick a template, fill in what you want to say (or what topic to talk about), and hit make. Your first video takes about 60 seconds." CTA: "See templates."
3. **Wizard.** Currently excellent (see §6). Preserve.
4. **Welcome page.** Currently excellent (see §6). Preserve.
5. **Landing after welcome — currently the spokesperson detail page. Change:** land on a "What's next?" page or on Home with the tour advanced to step 2 or 3. The spokesperson detail page as a landing target is an admin surface; the user's momentum is in doing, not administering.

### 5.7 The "library" concept

The single most consequential IA change proposed is unifying Videos, Assets, Bundles, and Compositions into one **Library**.

- **Library home** shows everything the customer's AIs have produced, filterable by kind (Videos, Images, Audio, Transcripts), by AI, by date.
- **Video detail page** is the primary object; shows the video first, metadata second. "How this was made" is a *progressive-disclosure section* on the same page, not a separate route.
- **"Share to social"** is an action button on a video detail, not a separate nav item.
- Assets that are not videos (audio, images, transcripts) live in the Library with their own filter chip. The user does not need to know they are "assets."

### 5.8 Naming the surfaces (working names)

The current italic-gold "§ N — Surface" pattern would need updating. Working names (not final):

- Home
- Your team (or the resolved noun from §4)
- Sources
- Make
- Library
- Campaigns
- Settings (footer / user-menu)
- Operator (staff-only rail; probably called just "Admin")

Section numbering ("§ 01 — Workspace") should either extend the model coherently across ALL customer surfaces or be dropped from ALL customer surfaces. The current partial application (§ 01 Workspace + § 02 Render queue + § — Setup + § — New spokesperson + § 03 Recipe gallery + § — Identity + § 7 Asset Library + § 5 Bundles + § 6 Videos + § — Spokesperson + § — Welcome back + § — New account) is inconsistent. Choice belongs in a separate brand pass, not this document.

---

## §6 — Preserve the good parts

The pieces of the shipped UI that already speak well and should become models for the rest of the product.

### 6.1 The 4-step wizard

**Why it works.** Numbered steps, clear labels ("Identity, Portrait, Voice, Confirm"), concrete placeholders ("Casey, Coach Ben, The Bell Curve…"), helpful example briefs, freedom to move backward and forward. The italic-verb H1 ("Compose the ***spokesperson***.") is the only friction and would be replaced by whatever noun choice §4 resolves to.

**What to preserve verbatim as a design pattern:**
- Numbered steps with a labeled progress indicator that is *always visible* while inside the flow
- Concrete example placeholders that give the user permission to be casual
- The voice-preview step's frank framing ("Runway turned your recording into the bound spokesperson voice. Listen below — if it sounds right, continue…")
- The "Continue and land on detail" button copy — explicit about what the next step will be

**Where to apply this pattern next:** the campaign-creation flow (currently a wall of form fields), the recipe-form flow (currently a wall of fields with engineering vocabulary), the source-upload flow (currently four tabs with no scaffolding).

### 6.2 The welcome page

**Why it works.** "**Meet Bean.**" is the first user-visible line where the customer's own voice is used back to them (Bean is the customer's chosen name). The bullets are honest without being negative: "Their name and personality / The brief you gave them about your business / How to sound like themself, in their own voice." The **honest limitation** — "*{name}* doesn't know your **specifics** yet" — sets an expectation that prevents disappointment later.

**What to preserve verbatim:**
- The pattern of using the user's chosen name back to them
- Honest naming of what's included and what's not
- Two-CTA layout with a clearly-labeled tertiary escape hatch
- The frank "Heads up" footnote about consequences of skipping

**Where to apply this pattern next:** every "you just completed X, here's what's next" moment — after first video, after first campaign, after first live conversation, after first upload.

### 6.3 Empty states

**Why they work.** "No documents yet. Paste content or upload a PDF above. Every spokesperson in the workspace will be able to draw from it." — identifies the empty state; explains what would populate it; explains what value it delivers.

**What to preserve:**
- Structure: what's missing → how to add it → why it matters
- Warmth without cutesy
- Concrete next action

**Where to apply this pattern next:** every populated state. When a list has 3 items, the copy should still feel this human. Currently, populated states abandon the voice.

### 6.4 The transcript-miner orientation

**Why it works.** "Every live session produces a transcript. Pick one, mine it for shareable highlights, then approve the clips you want rendered." — three sentences that explain the entire flow. The user reads it and understands the loop before doing anything.

**What to preserve:**
- Three-sentence purpose statement at the top of a feature page
- The "then approve" language that keeps the user in control of the AI's output

**Where to apply this pattern next:** every feature page that isn't self-explanatory (recipes, campaigns, bundles, live-conversation preflight).

### 6.5 The usage panel

**Why it works.** "Videos this period: {used} / {limit}" with a tier badge and a progress bar tells Priya (accountant) exactly what she needs. The panel is small, glanceable, and factual.

**What to preserve:**
- Numeric fact + limit + progress + tier — in that order
- Muted color until approaching limit
- Amber, then red as the limit approaches

**Where to apply this pattern next:** the pricing/upgrade story, which currently doesn't exist proactively.

### 6.6 The live-conversation core

**Why it works.** The Talk feature IS the product's magic moment. Once the user gets past the preflight anxiety, the experience of talking to an AI grounded in their own material is the thing they tell their friends about.

**What to preserve:**
- The core interaction (WebRTC live audio, tool invocation, transcript capture)
- The end-of-session panel's straightforward summary ("Duration: {seconds}s. The transcript is being captured in the background — it will appear in this spokesperson's recent conversations shortly.")

**What to fix (not the concept — the packaging):**
- The preflight anxiety triggers (Runway callout, cost-ticker turning red, "wear headphones" warning that reads as a mic-setup problem)
- The invisibility of the feature after first use (only accessible from spokesperson detail; should also live on Home + on any AI's list card)

### 6.7 The recipe card grouping

**Why it works.** Recipes are grouped into families ("Talking head," "Cinematic," "Audio & Voice") with counts. This is a strong pattern that helps users find the right starting point.

**What to preserve:**
- Family-based grouping
- Per-card descriptions
- Visible field-count so the user knows how much work they're about to do

**Where to extend:** the descriptions should shift from pipeline-oriented ("prebuilt step sequence the render pipeline executes against the media engine") to use-case-oriented ("A 30-90 second video of your AI talking directly to camera — good for updates, explainers, and social posts").

---

## §7 — Unresolved questions

Open decisions this document does not resolve. Each requires operator input.

### Q-1 · The "spokesperson" noun (single most consequential)

Which of §4.1's three directions is the product's spine — a single class term (and if so, which of "AI presenter" / "AI character" / "AI helper" / "AI representative" / "AI persona"), or a contextual approach that uses the user's own naming, or an elevation of "character" tied to the product name?

**My leaning:** "character," aligned with the product name, with contextual meta-terms elsewhere ("your team" for collections, plain descriptions in flows). Not final.

### Q-2 · Section-mark typography and voice

Is the "§ NN — Section" + italic-verb H1 pattern part of the product's permanent identity, or is it a brand phase that no longer serves the target audience? The persona review shows it splits the audience. This is a brand-voice decision that outranks vocabulary.

### Q-3 · How much of the product is for the technical user

Rob (consultant) is the current product's ideal user. Marcus (realtor) tolerates it because the value is high. The other 8 personas need substantial vocabulary + IA work. What's the go-to-market target — the technical creator/consultant vertical (in which case the current product is closer than it feels), or the broader small-business owner (in which case this document's changes are the roadmap)?

### Q-4 · Data & Privacy surface

The persona review flagged this as a hard block for 4 regulated verticals (therapist, dentist, accountant, teacher). What does a "Data & Providers" surface commit to? Are there BAAs? Are there retention guarantees? These are business-and-legal decisions the design cannot make on its own.

### Q-5 · The verifier's exposure to the customer

K6.4 is a strategic differentiator. How much of its machinery does the customer see? Options range from "hide entirely and default to a sensible mode" to "expose as a labeled slider with a rich explanation." Different choices imply different pricing, positioning, and support burden.

### Q-6 · Multi-AI product shape

The product supports multiple AIs per workspace (Jamie has Bean; Sara has The Docent per exhibit; a large organization could have dozens). Is the primary model *one workspace = one AI's team* (like Slack), or *one workspace = many independent AIs* (like a stock library)? The current product is closer to the latter but nothing tells the user that.

### Q-7 · Live vs asynchronous conversation status

The Talk feature and the async conversation feature currently share the "Conversations" model but have different UX shapes and different frontend surfaces. Should they be unified in the customer's model ("Talk to it" — the mode is chosen contextually), or presented as two distinct capabilities?

### Q-8 · Where "your team" (or the chosen class term) points

If the customer builds one AI, is it their whole team? If they build ten, is each one a team member? Does the product want to encourage many AIs per workspace (which unlocks segmentation but risks fragmenting the mental model), or one AI per workspace (which is simpler)?

### Q-9 · Onboarding tour scope

The current 3-step tour hits the key surfaces (build → teach → make). Should the tour extend to cover live conversation and campaigns (the two features personas most enjoyed but had to discover on their own)? Cost: longer onboarding. Benefit: higher retention.

### Q-10 · Pricing / tier surfacing

The usage panel is good but the upgrade story is reactive (only appears when limit is hit). Should the product surface pricing/tier value proactively (Priya's need), or preserve the "value first, pricing second" reveal (which many SaaS products favor)?

---

## §8 — Explicit things that should NOT change yet

To prevent this document from being read as a green light for wholesale rewrite.

### 8.1 Backend model names

The Django model names (`Spokesperson` → `Teammate` per canonical identity contract §17.1.b; `Composition`, `Asset`, `IdentityReference`, `NormalizationManifest`, `GenerationRecord`, `Bundle`, etc.) are contract identifiers. They are NOT changed by this document. Customer-vocabulary decisions above translate at the presentation layer only.

### 8.2 The Step 10 sequence

Step 10 and every §19.3 downstream step (Step 11 consumer migration, Step 12 realtime lifecycle, Step 13 growth-window close, Step 14 R10 verifier extension, Step 15 Portrait Territory Study V2) are unaffected. This document does not open, defer, or reprioritize any of them.

### 8.3 The P-0 workflow

Chris's real Step 9.b operator review workflow (currently pending — Chris to run the SPA at `/settings/bootstrap-review/…` after his `is_staff=True` promotion) is unaffected by this document.

### 8.4 The P-1 prerequisite (PP-EXT)

The PortraitProvider regeneration prerequisite scope-locked in the prior operator-authorized design report is unaffected. Ratifications 1-8 stand.

### 8.5 Operator surfaces

The bootstrap-review, provider-status, and engine-connections surfaces continue to use their internal vocabulary unchanged. The proposed change is *isolation* (staff-only gate) rather than *rewrite*.

### 8.6 The wizard, welcome page, and empty states

These are the models. They stay in place. If anything is changed at all, it should be the noun "spokesperson" (per §4.1) and only after Q-1 resolves.

### 8.7 Contract documents

`CANONICAL_IDENTITY_CONTRACT_V1.md`, `KNOWLEDGE_LAYER.md`, `VIDEO_COMPOSITION_V1.md`, `REALTIME_AVATAR_V1.md`, `WORKSPACE_FABRIC_V1.md`, and every ratification block within them are unaffected. The customer-vocabulary contract lives adjacent to these, not inside them.

### 8.8 Anything on any operator handoff, INVENTORY, or design lock

Handoffs, INVENTORY regeneration, and design locks continue to use engineering vocabulary. This document is customer-vocabulary only.

---

## §9 — Acceptance criteria for a future UX implementation milestone

When a future session opens a "customer-vocabulary + IA" milestone, it succeeds when these are true. This is the contract that says "the design in this document is realized."

### 9.1 Vocabulary criteria (must all hold)

- Zero appearances of "K2," "K6," "K6.4," "K6.6," "primitive," "chunk," "embedding," "corpus," "ingest," "pipeline," "composition," "mock" (as a badge on customer output), "provision," "fire" (as a verb), "ship" (as a verb), "bake," "commission" (as the sign-up verb) on any customer surface.
- The "spokesperson" noun replaced with the term chosen in Q-1.
- Every remaining acronym or shorthand has an inline plain-English explanation on first appearance.
- Every empty state uses the §6.3 pattern (what's missing + how to add + why it matters).
- Every "you just completed X" moment uses the §6.2 welcome-page pattern.

### 9.2 IA criteria (must all hold)

- Customer top-nav is the six items in §5.2 (or fewer). Assets, Bundles, and Compositions are not top-nav items.
- Bootstrap-review, provider-status, engine-connections do not appear in the customer nav; they live behind a staff-only gate.
- Video detail is the primary surface for a video; "How this was made" is a progressive disclosure on that page, not a separate route.
- The Library unifies videos, images, audio, and transcripts under one browse surface.
- A Data & Providers surface exists (even if minimal — see Q-4) and is linked from the primary sign-up and from every ingest flow.
- Sign-up drops the "commission your operating partner" copy and uses plain-language equivalents.
- The onboarding tour uses the customer verbs (build / add / make), not the engineering verbs (provision / attach / fire).

### 9.3 Preservation criteria (must all hold)

- The 4-step wizard is intact, structurally unchanged.
- The welcome page is intact, structurally unchanged, with the same warm honest voice.
- Empty state copy across knowledge/spokespeople/scripts/campaigns is preserved (with vocabulary substitutions applied).
- The usage panel is preserved.
- The recipe-card family grouping is preserved.
- Transcript-miner three-sentence orientation is preserved.
- Live conversation core interaction (WebRTC, tool invocation, transcript capture) is preserved.

### 9.4 Persona criteria (10 walk-throughs post-implementation)

For at least 8 of the 10 personas from the SESSION 250 review, a walk-through of the first 10 minutes should show:
- The persona completes sign-up without bouncing at the tagline or the H1
- The persona completes the wizard
- The persona uploads at least one source
- The persona produces at least one video
- The persona reads at least one page and says (metaphorically) "this is a product I'd tell someone about"

For at least 4 of the 10 personas (specifically: the therapist, dentist, accountant, teacher), the walk-through should additionally show:
- The persona finds a Data & Providers surface without hunting for it
- The persona reads it and understands what happens to their material

### 9.5 What NOT to check for

The acceptance criteria explicitly do NOT require:
- Any component redesign
- Any color/typography change (unless Q-2 opens a brand pass)
- Any new backend model
- Any renamed backend model
- Any new engineering capability

The milestone is a **product-language and information-architecture** milestone. It is a *presentation-layer* change with adjacent onboarding-tour + copy work. It is not a redesign.

---

## §10 — What this document does NOT do

To be explicit:

- **It does not open Step 10.**
- **It does not touch the PP-EXT prerequisite.**
- **It does not touch Chris's real Step 9.b P-0 workflow.**
- **It does not change any backend model, field, migration, contract, or API.**
- **It does not touch any operator surface's internal vocabulary or shape.**
- **It does not create implementation tasks.**
- **It does not create a scope-lock for a UX milestone** — it creates the acceptance criteria (§9) that a future scope-lock would ratify against.
- **It does not choose the "spokesperson" replacement noun** (Q-1 is unresolved by design).
- **It does not commit to a brand voice change** (Q-2 is unresolved by design).
- **It does not commit to a Data & Privacy product decision** (Q-4 is a business/legal question).
- **It does not choose the go-to-market persona** (Q-3 is a strategy question).

---

## §11 — What to do next (recommended, non-binding)

Two natural next actions, either order:

**A — Resolve the top open questions.**
Q-1 (the noun) and Q-3 (the GTM persona) are the two decisions that shape everything else. If Q-3 lands on "technical creator/consultant" the current product is closer to right than the persona review suggested and this document's scope shrinks. If Q-3 lands on "broader small business" the roadmap is closer to what §5 outlined. Q-1 depends on Q-3 partially — a technical creator can live with "spokesperson"; a small business owner cannot.

**B — Return to the P-0/PP-EXT track.**
Resume the paused sequence: Chris runs the real Step 9.b operator review, gate closes green, we produce the final PP-EXT design report, we ship PP-EXT, then Step 10 opens. This document is a durable artifact regardless of when the customer-facing work begins.

Both tracks (product-language + Step 10 stack) are independent. Neither blocks the other. This document commits to nothing except being a durable reference for whichever session first opens the "customer-vocabulary + IA" milestone.

---

## STOP

Design artifact complete. No code. No implementation tasks. No Step 10 movement. No P-0 movement. No PP-EXT movement.
