# CHARACTER OS — PRE-STEP 10 PRODUCT REVIEW
### 10 real-world personas · full workflow walk · patterns · priorities

> **Correction added 2026-08-08 (from the three-way comparison
> pass — see
> [`IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md`](IDENTITY_MODEL_V1_THREE_WAY_COMPARISON.md)
> §DAC-2 + DA-2):** the P-8 finding below states that operator
> surfaces are "exposed in the customer nav" and specifically names
> `/settings/bootstrap-review`, `/settings/provider-status`, and
> `/settings/engine-connections`. On direct SPA inspection during
> the three-way comparison pass, only `/settings/provider-status`
> is footer-linked; `/settings/bootstrap-review` and
> `/settings/engine-connections` are direct-URL-only (not reachable
> via any nav link). The finding's spirit stands — direct-URL
> reachability with 403-at-API is still a polish concern — but the
> specific "in the customer nav" claim was empirically inaccurate
> for two of three surfaces. Original P-8 body preserved below
> unchanged as historical evidence from the simulated-persona walk.

**Status:** evidence artifact (companion to `CUSTOMER_MENTAL_MODEL_V1.md`)
**Session:** SESSION 250
**Scope:** product-level UX review; not code review, not engineering review, not implementation
**Method:** read every user-visible string in the shipped SPA; simulated first-10-minutes walk from each of 10 personas
**Companions:** `docs/design/CUSTOMER_MENTAL_MODEL_V1.md` (design reconciliation built on this evidence)

---

## Methodology + caveats

I reviewed the actual user-visible copy on every SPA surface: sign-up/in, dashboard, all nav items, spokesperson creation + welcome + detail + identity + talk, recipes, images, knowledge, transcripts, scripts, campaigns, tools, assets, bundles, videos, compositions, conversations, signature, about, provider-status, engine-connections, and the entire bootstrap-review family. Every quoted phrase below is on-screen text extracted from the shipped SPA components.

Two things I explicitly did NOT test that would sharpen this review: (a) the actual interactive feel (motion, loading times, error recovery flows) — I inferred these from copy + component structure only; (b) the mobile experience — the surveys focused on desktop copy. Where I flag friction, it's rooted in wording, information architecture, or asked-for prerequisites the user reads on screen.

The header on every page reads: **"Character" + "OS"** with subtitle **"Persistent AI Spokesperson Infrastructure"** and top-right chip **"a product of 24/7 GLOBAL AI"**. That subtitle appears above the fold on every page. I refer back to it in nearly every persona because it colors the entire first impression.

---

# 1. PERSONA REVIEWS

## Persona A — Jamie, coffee shop owner (2 locations, 6 baristas)

**Why she signed up.** Instagram ad promised "an AI that talks to customers for you." Wants a friendly on-camera face for her weekly Reels + a way to answer FAQ on Google without personally being on camera.

**Sign-up.** The gold "§ — New account" mark and the italic phrase "**Commission your operating partner**" reads like a private equity pitch. She thinks she landed on a B2B enterprise site by accident and almost bounces. She proceeds only because the email/password form is standard.

**Dashboard first landing.** "§ 01 — Workspace" over her own email is confusing — is that her account name? The onboarding tour saves her: three clear steps ("Provision your first spokesperson" / "Attach workspace knowledge" / "Fire a composition"), but every verb feels wrong. **"Provision"** is IT-speak; **"Fire"** feels violent for what should be creative; **"composition"** makes her think of music homework. She clicks "Open the wizard" anyway because the sparkle icon and picture of a person are inviting.

**New spokesperson wizard.** This is Character OS at its best for her. "Four steps: identity, portrait, voice, confirm" is understandable. The placeholder "Casey, Coach Ben, The Bell Curve…" gives her permission to be casual. The brief example ("Sells artisan bicycle bells to small bike shops…") is concrete and unlocks her writing. She names her spokesperson "Bean" and finishes the wizard.

**Spokesperson welcome page.** "Meet **Bean**." with the portrait — she smiles for the first time. The italic-personal "Their name and personality / How to sound like themself, in their own voice" and the honest warning ("Bean doesn't know your **specifics** yet…") feels like a real product talking to a real person. Best copy on the entire site.

**Spokesperson detail.** Immediately alienating again. "Ready to render" as a badge. "Re-bake" button with an obscure Flame icon. Status pills "Status: draft / Avatar: pending / Voice: not set" read like server logs. **She has no idea what "bake" means, why avatars need re-baking, or what "draft" means when she just made it.**

**"Teach Bean about your business" (knowledge).** Knowledge tab title reads "What your **spokespeople** know." That's clear. But the H2 "Add knowledge" over four tabs — Paste / Upload PDF / URL / Search — makes her freeze. She has a menu. What tab is a menu? She uploads a PDF of the menu. Success. She's proud.

**Recipes gallery.** "Pick a **composition** recipe" — she has no idea what a composition is. She clicks a "talking_head" tile because it's the only word that sounds like what she wants. The form asks for "K2 knowledge mode" (opaque), "K6.4 verifier mode" (completely opaque), and "verifier: default/strict/warn/off". She picks defaults and hopes.

**Wait for render.** Dashboard's "Recent activity" fills in. "Bean · talking_head · mock" — the badge "mock" makes her wonder if her video isn't real. It isn't, but nothing tells her how to make it real.

**Would she pay?** She'd pay for the wizard-to-first-video flow. She'd quit before her second video because "verifier", "composition", "bake", and "mock badge" made her feel dumb repeatedly. **Verdict: intrigued → confused → tentative purchase. Retention risk high.**

---

## Persona B — Ms. Patel, first-grade teacher

**Why she signed up.** Colleague at PD showed her a video "avatar" a middle-school teacher had made for parent communication. Wants weekly 60-second updates for parents in English + Spanish without recording herself.

**Sign-up.** "Persistent AI Spokesperson Infrastructure" hits her like a wall of concrete. She thinks: this is not for teachers. She only continues because a colleague vouched.

**Dashboard.** "Render queue" makes her think of print jobs. "§ 02 — Render queue: Compose a render. Ground in workspace knowledge. Ship." reads like a computer science syllabus. The word "ship" for delivering a video makes no sense to her.

**Wizard.** She writes: "I'm the teacher, but this AI version of me talks to parents." She names it "Ms. Patel Assistant." The tone/personality fields help. The portrait step confuses her — she does not want to be on camera (that's why she's here) but "The on-camera look" implies she must be. She uploads a stock illustration of a teacher.

**Welcome page.** She likes this page. "Teach Ms. Patel Assistant about your business" — the word **business** stops her cold. She's a teacher, not a business. But she clicks anyway.

**Knowledge.** She pastes her class syllabus and last week's lesson plan. It uploads. Status pill says "processed." Fine.

**Recipes.** She sees "talking_head", "cinematic_visual", "backdrop_layout", "reels_format". None of these speak to "60-second parent update." She's not sure where to start. She tries "talking_head" — form asks "K6.4 verifier mode" and she doesn't know if she wants strict or warn or off. She picks default.

**Result.** The video comes out. But she has to go to "Video library" to find it, and the page is titled "Video **library.**" with subtitle "Every composition rendered in this workspace — talking heads, backdrops, polished outputs, layouts. Click any row for the full pipeline view." **"Pipeline"** ejects her out of the fantasy. She just wanted a video.

**Campaigns.** She discovers this. "Write one script template, paste a CSV of recipients, and launch — the system renders a personalized talking-head video for each row." She lights up — 24 parents, personalized "Dear {first_name}" videos. But: "Header row must include: {first_name}, {milestone}…" — she doesn't know what CSV headers are. She's from a Google Sheets world. **The word "CSV" is a wall.**

**Would she pay?** Possibly, for parent-comms use. But the whole product speaks to her in the voice of an infrastructure vendor, not an educator. **Verdict: friction-heavy but salvageable. Would need serious hand-holding.**

---

## Persona C — Dr. Reyes, child therapist (small private practice)

**Why she signed up.** Wants a warm, on-brand explainer video for her practice website about her intake process. Considered hiring a videographer for $2,500 and thought: maybe AI.

**Sign-up.** "Commission your operating partner" hits her differently — she thinks this is a legal-tech product. She's a licensed clinician. She's already worried about HIPAA. The words "Persistent AI Infrastructure" trigger her privacy antennae. She actually reads the "About" page before signing up (most personas don't). About page's line "The future belongs to those who put their **decisions** on autopilot and reserve their **judgment** for what only a human can do" resonates faintly, but "decisions on autopilot" makes her nervous re: clinical ethics.

**Dashboard.** She logs in and immediately looks for privacy/data settings. Not present in the nav. **Big problem for her professionally — the nav shows "Spokespeople / Knowledge / Transcripts / Scripts / Recipes / Campaigns / Bundles / Videos / Assets / Images" but no "Privacy," "Data," "Retention," or "Compliance."** She cannot verify where her intake language and business knowledge live.

**Knowledge.** "Every render and conversation draws from this corpus." She reads "corpus" and thinks: what happens if I upload something with a client's example? "Snapshot at ingest — content is captured as it looks now and isn't re-fetched." She doesn't know what "ingest" means and it sounds like the system is eating her material. She stops before uploading anything sensitive.

**Talk feature.** Discovers "Talk to Ms. X" on the spokesperson page. Reads the warning: "Sessions last up to N minutes (Runway's per-session cap). Wear headphones. Speaker audio leaks back into your microphone otherwise." The phrase "Runway's per-session cap" tells her a third party is involved. She clicks the "Ended session" flow — "The transcript is being captured in the background." She stops immediately: **captured where? Retained for how long? Is Runway HIPAA-compliant?** The product answers none of these on screen.

**Would she pay?** No. Not until there is visible language about data handling, retention, third-party processors, and BAA availability. **Verdict: bounces at first sensitive-content moment. Compliance-adjacent verticals need a "Data & Privacy" section in nav OR clear inline copy on every ingest/session surface.**

---

## Persona D — Marcus, realtor (mid-market suburban)

**Why he signed up.** Sends 40+ personalized property intro videos per month. Currently records each himself. Somebody said AI can do this now.

**Sign-up.** Doesn't read the subtitle. Just wants to get in.

**Dashboard.** Skims the tour, dismisses it. Wants to see if this actually does the thing.

**Wizard.** Fastest through the wizard of any persona. Names the spokesperson "Marcus (Digital)". Uses his headshot.

**The magic moment (for him) is Campaigns.** "Write one script template, paste a CSV of recipients, and launch — the system renders a personalized talking-head video for each row." **This is the killer feature for him and it's buried behind 9 other nav items.**

**But then:** the campaign form. "K2 knowledge retrieval / K6.4 verifier / verifier mode: default (warn) / strict / warn / off." He does not care. He just wants his script rendered against 25 rows. The form's insistence on "K6.4" naming — visible in the UI as literal "K6.4" — makes him think he's using developer beta software. Not a product.

**Rendering.** His first render fires. Activity feed shows "Draft" then "Running". He waits. **The onscreen copy for rendering says: "Runway is processing. Mock mode lands in ~13s; real mode takes 60–120s."** The word "Runway" makes him wonder if there's an upcharge or third-party contract.

**Videos library.** He finds his 25 personalized videos. Downloads them via "Open original ↗". This works. He's impressed.

**Would he pay?** Yes, for volume campaigns. He'll ignore 80% of the product. **Verdict: happy customer despite bad UX. The core value cuts through, but he doesn't tell his network because he can't easily explain what it does.**

---

## Persona E — Dr. Alvarado, dentist (single practice, 2 hygienists)

**Why she signed up.** Wants short pre-appointment explainer videos for common procedures (root canal, whitening, sleep apnea appliance) to send to new patients.

**Sign-up.** "Operating partner" reads corporate. She's used to buying practice-management software and mostly ignores marketing copy.

**Wizard.** She names it "Alvarado Dental Assistant." Uses a stock dental-office image. Skips voice (picks default).

**Knowledge.** She uploads a PDF of her patient-facing FAQ. "Processed." Good.

**Recipes.** She wants a 90-second explainer for "root canal — what to expect." She sees "talking_head" and picks it. The form: "K6.4 verifier mode." She has no idea. **The most damaging thing here is the "Verifier mode: strict — blocks the draft if any claim is unsupported" option.** She's a doctor. She's terrified the AI will hallucinate a medical claim, so she picks strict.

**Render.** Fires. Comes back with **"K6.4 verification blocked — This script cannot be approved until you regenerate and resolve the flagged claims."** She reads flagged claims: "root canal is generally painless" — flagged as unsupported. She thinks: **great, the AI is being cautious.** But she has no idea how to "resolve the flagged claim." She's not going to write it herself; she signed up to avoid that.

**Would she pay?** The instinct is good ("K6.4 caught a hallucination in a medical claim!") but the resolution path is dead-end for a non-technical user. **She either lowers verifier to warn (and now trusts nothing) or quits.** Verdict: **the verifier is a moat AND a wall. Amazing capability, buried in engineering-review UI.**

---

## Persona F — Pastor Dan, church pastor (mid-size congregation)

**Why he signed up.** Wants short weekly video devotionals for the church app + a way to help elderly members feel connected during the week.

**Sign-up.** The word "Commission" throws him — he thinks about commissioning missionaries. He goes anyway.

**Dashboard.** "Render queue: Compose a render. Ground in workspace knowledge. Ship." — three sentences in an idiom he doesn't share. He interprets "ground in" as a spiritual metaphor and appreciates that briefly.

**Wizard.** He calls his spokesperson "Pastor Dan (Video)". Uses his headshot. Portrait step's phrase "The on-camera look" reads well.

**Knowledge.** Pastes his sermon notes. Uploads the church's history PDF. Processed.

**Talk.** He tries the realtime feature. "Live two-way conversation grounded in your workspace knowledge." He's charmed. He talks to Pastor Dan (Video) for two minutes and it responds using his own sermon content. He tells his wife.

**Transcripts.** He notices "Transcript **miner.**" in the nav. Opens it. **"Transcripts are created automatically at the end of a live realtime session… Every live session produces a transcript. Pick one, mine it for shareable highlights, then approve the clips you want rendered."** He gets it. He mines a transcript. It works.

**But:** "Mine highlights" gives him back "3 highlight(s), pending, [Approve] [Reject]." He approves one. The status changes to "Rendering…" then "View composition →". He clicks. The composition detail page shows him "K6 synthesized brief / K6.4 claim verifier / template_kind: recut_teaser / Steps: #1 audio_extract / #2 split_script / #3 concat_clips / …" — **a full engineering pipeline view. He cannot recover from this.** He goes back and never opens compositions again.

**Would he pay?** Yes, for the Talk + mine flow. He'll never touch anything with "K6" or "composition" in the title. **Verdict: 40% of the product is his; 60% actively repels him.**

---

## Persona G — Sara, museum curator (mid-size regional museum)

**Why she signed up.** Wants short "docent-in-your-pocket" video vignettes for each exhibition — a 45-second AI-narrated intro to each piece for the museum app.

**Sign-up.** Reads slowly. Finds "Commission your operating partner" fine — she works with commissions professionally. Understands "brief" from museum context. Signs up.

**Dashboard.** "§ 01 — Workspace" — she reads section marks like a scholar. Actually likes the numbered-section brand voice. This is the persona the italic-gold "§" typography was designed for.

**Wizard.** She creates "The Docent." Uses a stock museum image. Skips voice.

**Knowledge.** She uploads three PDF catalogs. Beautiful. Two of them get status "failed." She scrolls to the knowledge detail page. **"The document may have failed to embed — check the error message above."** But there is no error message above. Dead end.

**She tries the URL ingest.** Pastes the museum's wall-text URL. "Fetching + extracting…" Then "processed." Chunks appear.

**Recipes.** She goes to recipes. "Cinematic visual" catches her eye. Perfect for museum content. Clicks. Form asks for a "Reference image" — she uploads a photo of a Rembrandt. Runs the recipe. Gets a cinematic-styled video. She's genuinely excited.

**The wall:** her cinematic clip ended up in "Compositions" and "Assets" and "Videos" and she has to search three places to find it. **The IA (information architecture) around the produced artifact is fragmented. Assets vs Videos vs Compositions are three overlapping views of the same thing and no page explains why.**

**Would she pay?** Yes. She'll be a power user. **Verdict: the product's most sophisticated buyer, but the IA fragmentation will eat her time and make her look bad to her director.**

---

## Persona H — Coach Mike, fitness coach (Instagram + 1:1 clients)

**Why he signed up.** Cranks 20 short-form fitness videos a week. Burnout. Wants an AI version of himself to talk to camera.

**Sign-up.** Ignores everything. Types email/password.

**Wizard.** Fast. Uses his real face + real voice (records the audio sample). Impressed by the voice-preview step: "Runway turned your recording into the bound spokesperson voice. Listen below — if it sounds right, continue…"

**Knowledge.** Skips it. Doesn't upload anything. His stuff is off the top of his head anyway.

**Recipes.** Picks "reels_format" — the name meets him where he lives. Runs it. Works.

**The moment he leans in.** Discovers "Publish bundles" and reads: "Publish bundles fan a source clip out to 5+ social platforms in one click. All ffmpeg — $0 incremental cost." **He does not know what ffmpeg is, but the "$0 incremental cost" hooks him hard.** Creates a bundle. Ships his clip to Instagram Reels + YouTube Shorts + TikTok + X + LinkedIn. Downloads each at the right aspect ratio.

**The friction:** he wants social scheduling. The product stops at file delivery. He has to open Buffer to actually schedule. **Product feels like it does 90% but expects him to do the final publish step manually.**

**Would he pay?** Yes, subscribes today. He is the ideal user for the current shape of the product. **Verdict: strong PMF for creator-solo use case. The very best of what's shipped.**

---

## Persona I — Priya, accountant (small firm, 3 partners)

**Why she signed up.** Wants short internal-training videos for firm's staff about new tax code changes.

**Sign-up.** Reads "Persistent AI Spokesperson Infrastructure" and thinks: infrastructure = capex or opex? What line does this expense on? Small alarm. Continues.

**Dashboard.** Numbers-oriented. Notices "Videos this period: 0 / 50" in the usage panel + tier badge "starter" + status badge "active" and appreciates the transparency. **Best-designed panel on the dashboard for her.**

**Wizard.** Creates "Kaplan Tax Assistant." Uploads a headshot of the senior partner. Types a brief. Fine.

**Knowledge.** Uploads a PDF of the new tax code notes. It fails processing. She tries a URL. That fails too. Doesn't understand why. **No error message tells her what's wrong.**

**Recipes.** Picks talking_head. Fills form. "K6.4 verifier mode: strict — blocks the draft if any claim is unsupported." She reads this and thinks: **this is actually the most important feature for me. I cannot have hallucinated tax law.**

**Draft.** Comes back with warnings. She reads them. K6.4 flagged three claims. She has no way to know if the claims are wrong or if the retriever missed the right passage. **The K6.4 verifier is her feature but she can't operate it.**

**Would she pay?** Only after a "verifier tuning" workflow exists. She's a real prospect but not today's UI. **Verdict: high-value vertical, blocked by inability to steer the verifier.**

---

## Persona J — Rob, solo consultant (fractional CMO)

**Why he signed up.** LinkedIn thought-leadership. Wants an AI version of himself that can answer prospect questions in DMs + generate short video takes on trends.

**Sign-up.** Reads everything. The tagline "Persistent AI Spokesperson Infrastructure" actually attracts him — he sees "spokesperson" and thinks "personal brand at scale." He is the target user for the current copy.

**Dashboard.** "Ready to render" doesn't bother him; he came from Notion + Zapier + Airtable. He knows this idiom.

**Wizard.** Fast. Uses himself. Records voice. Notices the wizard is genuinely well-designed and says so out loud.

**Knowledge.** Uploads three of his own PDFs. All process. Adds three URL ingests of his own blog posts. Works.

**Recipes.** Fires "talking_head" first. Then "cinematic_visual" for LinkedIn variety. Then discovers "long_form_ad" — described as a launch differentiator. Delighted.

**Talk.** Live conversation. Loves it. Tests it with a prospect question. It answers in his voice, grounded in his own blog posts. **This is the product's holy-shit moment for the ideal user.**

**Wall he hits:** the entire "settings/bootstrap-review" surface is exposed in the nav even though it's operator-only. He clicks it out of curiosity and lands on **"Operator surface · §19 Step 9.b — Bootstrap review — runs"** with a JSON-ish table. He assumes he found an internal dev panel by accident and worries about the product's polish.

**Would he pay?** Absolutely. He's already telling his fractional-CMO peers. **Verdict: the persona the product was written for. Even for him, the exposed operator surfaces are a polish concern.**

---

# 2. CROSS-PERSONA FINDINGS

Patterns that appeared across 3+ personas — these are product issues, not niche complaints.

### P-1 · "Spokesperson" is the wrong noun for 7 of 10 personas

Coffee shop (Bean), teacher ("assistant"), pastor (Pastor Dan Video), therapist, dentist, coach (himself), accountant (firm brand) — none of them think of what they're building as a **spokesperson**. A "spokesperson" is a PR-industry term for someone who speaks *on behalf of a larger organization*. The product is used most naturally as an *AI version of yourself* or an *AI helper for your business*. The name filters out solo operators, teachers, clinicians, and small-team users — the exact people the wizard is otherwise perfect for.

### P-2 · The engineering vocabulary is pervasive and cumulative

Words that appear in the nav or on the dashboard and immediately signal "this is for engineers":
- **render** / **render queue** / **rendered** (7/10 personas confused or repelled)
- **composition** / **fire a composition** / **compose a render** (8/10)
- **provision** (10/10 — nobody outside IT provisions anything)
- **infrastructure** (in the site subtitle — 8/10)
- **bake** / **re-bake** (10/10 — culinary metaphor but nobody understands why an avatar needs baking)
- **ship** (5/10 — engineer idiom for "deliver")
- **ground** / **grounding brief** (6/10 — LLM-speak)
- **bundle** / **publish bundle** (5/10 — IT term)
- **asset** (as a top-nav item — 6/10 read as accounting)
- **pipeline** (in "click any row for the full pipeline view" — 7/10)
- **runway** (5/10 wonder if it's an upcharge)
- **mock** / **mock mode** (10/10 — nobody signed up wanting a "mock" of anything)
- **K2**, **K6**, **K6.4**, **K6.6** (10/10 — completely opaque, appear as literal labels in forms)

None of these are individually fatal. Cumulatively they establish that Character OS was built by engineers for a technical audience — which contradicts the audience the wizard and welcome pages actually speak to.

### P-3 · The dashboard's onboarding tour is the product's best surface AND uses its worst vocabulary

The tour saves half the personas from bouncing. But its three step headings — "Provision your first spokesperson" / "Attach workspace knowledge" / "Fire a composition" — use the three most-alienating verbs in the product at the highest-stakes moment (first minute of use).

### P-4 · The verifier (K6.4) is a strategic differentiator and an unusable UI

Dr. Alvarado (dentist), Priya (accountant), Ms. Patel (teacher), Pastor Dan (fact-checking sermon claims) — 4/10 personas would pay MORE for a demonstrably reliable AI voice. K6.4 is exactly that. But the UI:
- Uses the literal internal name "K6.4" as a user-facing label.
- Presents 4 modes (default/strict/warn/off) with terse hint text.
- On block, tells the user "regenerate and resolve the flagged claims" without any workflow for resolving.

The most valuable feature in the product is invisible to the users who need it most.

### P-5 · Assets vs Videos vs Compositions vs Bundles = 4 nav items showing overlapping views of the same thing

Sara (curator), Rob (consultant), Marcus (realtor) all lost time hunting for something they'd just made. The nav treats "Assets", "Videos", "Bundles", "Compositions" as coequal top-level surfaces, but from a user's perspective:
- I made a video → where is it?
- Video library shows videos.
- Assets shows videos AND their components AND transcripts AND audio.
- Compositions shows the same videos with pipeline internals exposed.
- Bundles shows the reformatted versions of the same videos.

There is no user model in which these are four different things. Any of them getting deleted would surprise the user because they don't understand which is authoritative.

### P-6 · Empty states are among the best copy in the product

Consistently: knowledge ("No documents yet. Paste content or upload a PDF above. Every spokesperson in the workspace will be able to draw from it."), spokespeople ("A spokesperson is the on-camera identity your workspace renders against… Commission one to begin."), scripts, campaigns — all use plain, encouraging language with a concrete next action. This is a *voice the product already knows how to use.* The problem is that populated states abandon it.

### P-7 · The italic-gold section-mark ("§") + wordy H1 pattern is polarizing

Sara (curator), Rob (consultant), Dr. Reyes (therapist) — the three most-literate personas — either appreciate it or read past it. The other 7 either think they landed on a legal/PE/art site (Jamie, Ms. Patel, Priya, Pastor Dan, Coach Mike) or ignore the ornament and struggle with the wordy verbs underneath ("Auto **scripts.**" — is "Auto" a noun?). It's a distinctive brand voice but it's costing about half the audience clarity.

### P-8 · The operator surfaces are exposed in the customer nav

The sidebar includes:
- **/settings/bootstrap-review** — literally titled "Operator surface · §19 Step 9.b — Bootstrap review — runs"
- **/settings/provider-status** — "Operator-only view of provider configuration"
- **/settings/engine-connections** — "See ENGINE_BRIDGE_V1.md for the contract"

Even the perfect persona (Rob) noticed this and worried about the product's polish. For the other 9 personas, one accidental click into any of these would probably end their session. These are internal tools showing internal jargon at the same nav level as "Videos" and "Spokespeople".

### P-9 · Data / privacy / retention is absent from the visible product

Dr. Reyes (therapist), Priya (accountant), Ms. Patel (teacher — student data considerations) all needed to understand where their content goes, what third parties see it, and how to delete permanently. **The product mentions Runway inline** (implying third-party processing) but has no "Data" tab, no per-asset "who has seen this," no clear delete-permanent flow. For any regulated or professional-liability vertical, this is a hard blocker.

### P-10 · The upload / ingest error surface is a black hole

Sara, Priya, Ms. Patel all had PDFs fail. Detail page says: "No chunks. The document may have failed to embed — check the error message above." — but the error message above is often blank or a stack trace-adjacent string. Empty states elsewhere in the product are warm; this one is Kafka.

### P-11 · The realtime "Talk" feature is universally magical AND universally scary

7 of 10 personas tried it and enjoyed it. Every one of them read the warning "Wear headphones. Speaker audio leaks back into your microphone…" and started worrying about tech setup. The genuinely cool feature has a genuinely off-putting preflight. The cost ticker turning red at 4 minutes adds another anxiety spike. The magic is real; the packaging punishes the user for using it.

### P-12 · Campaigns is a killer feature buried behind IT-vocabulary access requirements

Marcus (realtor) and Ms. Patel (teacher) both stopped at "CSV". Realtor pushed through because he already uses CSVs. Teacher didn't. **"Paste recipients CSV"** is a mid-2000s Salesforce idiom. A modern equivalent might be "add your list" with paste-table / paste-emails / Google Sheets connect / upload spreadsheet options.

---

# 3. PRODUCT-LEVEL OBSERVATIONS

**O-1 · The wizard is the product.** The 4-step spokesperson wizard + welcome page + first video is a genuinely delightful experience — clear steps, warm copy, honest expectations, a sense of accomplishment. This is what makes people become customers. Everything after step 1's completion feels like a different product built by a different team.

**O-2 · There are two personas in the copy, not the market.** All product copy assumes the user is either (a) a fluent operator of the AI/creative-tools stack ("render", "composition", "primitive_kind"), or (b) someone charmed by literary brand voice ("Commission your operating partner," "§ 02"). The 80% of the addressable market that sits between those two — small-business owners with modest technical fluency who want plain, encouraging language — is unserved by the current voice.

**O-3 · The product doesn't tell users what success looks like on each page.** The dashboard shows counts and status. The video library shows a list. The campaigns page shows recipients. But no page says: "You're doing well. Your next best step is X." The onboarding tour does this for the first 3 minutes and then vanishes. After that, users have to construct their own theory of what "success" means for a Character OS workspace.

**O-4 · The product exposes its lineage/audit trail as a first-class user surface.** Composition detail shows steps + verifier + citations + derived-from + used-by lineage. That is astounding engineering and it belongs in an "Advanced" or "For engineers" or "Audit" surface, not on the primary path from "I made a video" to "let me watch it." The right default for the composition detail is: play the video + show the brief + hide everything else behind a "How this was made" disclosure.

**O-5 · The operator surfaces need to disappear from the customer product.** Bootstrap-review, provider-status, and engine-connections should be behind a `/admin` or `/staff` gate, not a top-level `/settings` gate visible to all users. Their presence in the customer nav is the single largest polish tax the product pays.

**O-6 · The product has no pricing/upgrade story on-screen.** Usage panel shows "0 / 50 videos" and "Upgrade to Pro to add more" appears only when a limit is hit. Priya (accountant) would want to see the upgrade path proactively. Rob (consultant) would want to see agency-tier value if he's asked to recommend it. The product hides its commercial story until the user hits a wall.

**O-7 · Recipes are the second-best surface in the product.** Naming them, giving each a card + description + field count, grouping into families — this is thoughtful. The problem is that the field-form UI immediately re-imports engineering vocabulary ("K2 knowledge mode", "K6.4 verifier"). A recipe should be the moment the product speaks most simply, because it's the moment the user commits.

**O-8 · There is a real product here.** Coach Mike would buy today. Rob would buy today. Marcus will buy despite the friction. Sara would be a champion for the museum vertical. That's a plausible early-adopter base with strong word-of-mouth potential. The path from "50 users" to "5,000 users" requires nothing besides making the current product legible to people who don't already share its vocabulary.

---

# 4. PRIORITIZED UX ISSUES

Highest impact = "removing this friction unblocks the largest cross-section of the personas above." Impact rating is a combined judgment of *how many personas hit it × how badly they hit it × how commercially load-bearing the surface is.*

| # | Priority | Issue | Personas affected | Where it lives |
|---|---|---|---|---|
| 1 | **P0 · fatal** | The word "spokesperson" (nav, headings, every wizard step) doesn't match how 7/10 target users think about what they're building | Jamie, Ms. Patel, Dr. Reyes, Dr. Alvarado, Pastor Dan, Coach Mike, Priya | Global |
| 2 | **P0 · fatal** | Onboarding tour uses the three most-alienating verbs ("provision", "attach", "fire") at the first-minute stakes moment | All 10 | Dashboard tour |
| 3 | **P0 · fatal** | Operator surfaces (bootstrap-review, provider-status, engine-connections) are exposed in the customer nav with internal jargon titles | All 10 (5 would actively worry; 5 wouldn't notice but the product looks unpolished to anyone who does) | Sidebar + /settings |
| 4 | **P0 · fatal** | K6.4 / K2 appear as literal user-facing labels on form fields; the highest-differentiation feature is invisible to the users who most need it | Jamie, Ms. Patel, Dr. Alvarado, Priya, Pastor Dan, Marcus | Recipes, scripts, campaigns, conversations |
| 5 | **P0 · fatal** | "Bake" / "Re-bake avatar" (with a Flame icon) — nobody understands what this means or why they should ever click it | All 10 | Spokesperson detail |
| 6 | **P0 · fatal** | Data/privacy/retention has no visible surface, blocking all regulated verticals | Dr. Reyes, Dr. Alvarado, Priya, Ms. Patel | Global (missing nav item + missing inline copy on ingest/session flows) |
| 7 | **P1 · significant** | Assets / Videos / Compositions / Bundles are 4 overlapping nav items showing the same thing four ways — no user model matches this IA | Sara, Marcus, Rob, Coach Mike, Pastor Dan | Sidebar nav |
| 8 | **P1 · significant** | Composition detail page dumps engineering internals (Steps, primitive_kind, K6 synthesized brief, K6.4 claim verifier) into the default view | Pastor Dan, Ms. Patel, Jamie, Dr. Alvarado | /compositions/:id |
| 9 | **P1 · significant** | The verifier's "resolve the flagged claim" workflow does not exist — users get "blocked" but no path forward | Dr. Alvarado, Priya, Ms. Patel | Scripts detail, composition detail, conversations |
| 10 | **P1 · significant** | Upload / ingest errors are opaque — "check the error message above" points to no error message; failure state is a dead end | Sara, Priya, Ms. Patel | Knowledge detail |
| 11 | **P1 · significant** | "mock mode" is exposed to users as a badge/pill without any explanation of what it means or how to turn it off | All 10 | Dashboard activity, composition detail, video detail, video library |
| 12 | **P1 · significant** | Realtime session preflight ("wear headphones", "Runway per-session cap", cost ticker turning red) manufactures anxiety around the product's most magical feature | Coach Mike, Rob, Pastor Dan, Dr. Reyes, Sara | /spokespeople/:id/talk |
| 13 | **P1 · significant** | "Compose a render. Ground in workspace knowledge. Ship." — the primary dashboard headline is opaque to non-engineers | Ms. Patel, Jamie, Dr. Alvarado, Pastor Dan, Coach Mike | Dashboard |
| 14 | **P1 · significant** | "CSV" as the only ingest verb for campaign recipients — teachers, coaches, pastors all bounce off this | Ms. Patel, Dr. Alvarado, Pastor Dan, Coach Mike | Campaign detail |
| 15 | **P2 · noticeable** | Italic-gold "§ NN — Section" typography is polarizing; helps 3/10 personas, distances 5/10 | Jamie, Ms. Patel, Coach Mike, Priya, Pastor Dan (net-negative) vs. Sara, Rob, Dr. Reyes (net-positive) | Global page mastheads |
| 16 | **P2 · noticeable** | "24/7 GLOBAL AI" parent-brand chip + tagline confuses users about what they're actually buying (Character OS? 24/7 Global AI? A subscription to which?) | Jamie, Ms. Patel, Priya, Dr. Reyes | Global header |
| 17 | **P2 · noticeable** | No visible upgrade / pricing / tier-value story until the user hits a limit | Priya, Rob, Marcus | Dashboard usage panel, all limit-adjacent flows |
| 18 | **P2 · noticeable** | Populated states abandon the plain-English voice of the empty states | All 10 | Every list page after first item |
| 19 | **P2 · noticeable** | Recipe descriptions are pipeline-oriented ("prebuilt step sequence the render pipeline executes against the media engine"), not use-case-oriented | Ms. Patel, Jamie, Dr. Alvarado, Pastor Dan | /recipes |
| 20 | **P3 · polish** | The word "workspace" is used inconsistently — sometimes it's a company name, sometimes a product surface, sometimes an object noun | Priya, Rob, Sara | Global |

---

## Two suggestions specifically for the operator's next planning session

The list above is 20 items but there are really two moves that would unlock most of the value:

**Move 1 — do a vocabulary pass.** Not a redesign. Just a word swap. "Spokesperson" → "AI presenter" (or the product's chosen equivalent — the word matters less than the fact that it's plain English). "Render" → "video". "Composition" → "video project" or gone entirely. "Fire" / "Ship" → "make" / "publish". "Bake" → "generate portrait". "K6.4 verifier" → "Fact check". "Mock" → gone from the customer product (this is a build-time concept, not a runtime user concept). Even without touching layout or components, this alone would recover 4-6 of the 10 personas from bounce risk.

**Move 2 — separate the operator product from the customer product.** Move `/settings/bootstrap-review`, `/settings/provider-status`, `/settings/engine-connections`, and possibly `/compositions/:id` (as the default landing for a video) behind a staff-only nav that non-operator users literally cannot see. The customer nav shrinks to something like: Dashboard · AI presenters · Knowledge · Videos · Campaigns · Recipes. This alone would recover polish across all 10 personas.

Everything else on the priority list is meaningful; these two would move the needle the most.

## STOP

Product review complete. No engineering changes proposed. No P-0 or Step 10 work touched.
