/**
 * /how-it-works — public product explainer.
 *
 * Structure mirrors `~/development/signal-studio/frontend/src/App.tsx`
 * `HowItWorksPage` (7 sections: Hero, Monday side-by-side, 5-step
 * pipeline, What's live today, What's NOT built yet, Early-access
 * CTA, FAQ). Visual register is character-os's BRAND_IDENTITY_V3
 * editorial dark-luxe — `SectionHeader`, `DoctrineQuote`,
 * `HairlineDivider`, `EngagementBrief` — not signal-studio's
 * gray-950/blue-400 Tailwind aesthetic.
 *
 * Per BRAND_ECOSYSTEM_V1 contract rule 3, every brand string flows
 * through `@/lib/brand` (product name, parent name, contact). No
 * hardcoded company / product strings in component code.
 *
 * ── Truth contract (load-bearing — read before editing copy) ─────
 *
 * 1. Every "What's live today" claim must be runtime-verifiable
 *    against the SPA *as it ships today*. No aspirational features
 *    in that block.
 * 2. The "What's NOT built yet" section is the honesty pressure
 *    valve. If a Live-Today bullet feels half-true, demote it here
 *    instead of softening the wording above.
 * 3. Tier / pricing intentionally not shown — a paid tier doesn't
 *    exist. The CTA opens a `mailto:` to the parent-company contact
 *    (no fake "join waitlist" form, no fake backend).
 * 4. Counts in copy (recipes, primitives, tools) are anchored to
 *    `docs/CHARACTER_OS_INVENTORY.md` + CLAUDE.md phase status at
 *    the time of authoring. If the runtime grows past the doc, the
 *    inventory regen + a copy bump go together.
 */
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import {
  DoctrineQuote,
  HairlineDivider,
  SectionHeader,
} from "@/components/editorial";
import { BRAND, parentBrand } from "@/lib/brand";

export function HowItWorksRoute() {
  return (
    <div
      className="flex flex-col gap-20 py-6"
      data-testid="how-it-works-route"
    >
      <Hero />
      <MondayContrast />
      <Pipeline />
      <LiveToday />
      <NotBuiltYet />
      <EarlyAccessCta />
      <Faq />
      <Closer />
    </div>
  );
}

// ── Section 1 · Hero ────────────────────────────────────────────────

function Hero() {
  return (
    <header
      className="relative flex flex-col gap-5 pb-10"
      data-testid="how-hero"
    >
      <div className="flex items-center gap-3">
        <span
          className="h-1.5 w-1.5 rounded-full bg-gold shadow-[0_0_8px_2px_rgba(201,169,97,0.4)]"
          aria-hidden="true"
        />
        <span className="font-mono text-[11px] uppercase tracking-[0.34em] text-gold">
          How it works · {BRAND.product.name}
        </span>
      </div>
      <h1 className="font-display text-4xl leading-[0.98] tracking-tight text-cream md:text-6xl">
        One spokesperson. Every{" "}
        <span className="italic gold-text">channel.</span>
      </h1>
      <p className="max-w-2xl font-display text-lg leading-relaxed text-mist md:text-xl">
        {BRAND.product.name} gives a small business a persistent on-camera
        AI representative — the same face, voice, and knowledge across
        recorded videos and live conversations. You bring the brand;
        the system handles the production.
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
        <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.28em] text-gold">
          <span className="h-1.5 w-1.5 rounded-full bg-gold animate-pulse" />
          Early access
        </span>
        <span className="text-gold/30">·</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-fog">
          Pricing in design
        </span>
        <span className="text-gold/30">·</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-fog">
          One customer live today
        </span>
      </div>
      <div
        className="hairline-gold absolute inset-x-0 bottom-0 h-px"
        aria-hidden="true"
      />
    </header>
  );
}

// ── Section 2 · Monday side-by-side ─────────────────────────────────

function MondayContrast() {
  const without = [
    "Hire a video editor for each cut — three days, three drafts, one usable take",
    "Write the script yourself · pay a voice actor · pay a colorist",
    "Re-shoot a face on camera every time the message changes",
    "Glue an avatar tool to a CMS to a captioning tool — and pray they stay in sync",
    "End of week: one polished asset, six rough drafts, no library",
  ];
  const withCos = [
    `Open ${BRAND.product.name} · open the spokesperson you already built`,
    "Pick a recipe (talking head · cinematic · long-form ad · co-host · 16 more)",
    "Drop a script — or have the platform write one from your knowledge",
    "Render. The same face, same voice, same brand knowledge land in every cut",
    "End of week: a library of branded videos plus a live avatar that can hold a conversation",
  ];
  return (
    <section className="flex flex-col gap-6" data-testid="how-monday">
      <SectionHeader number={1} title="Your Monday morning" />
      <header className="flex items-baseline justify-between border-b border-luxe pb-3">
        <h2 className="font-display text-2xl tracking-tight text-cream md:text-3xl">
          Production without the{" "}
          <span className="italic gold-text">studio.</span>
        </h2>
        <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-fog">
          before · after
        </span>
      </header>
      <div className="grid gap-6 md:grid-cols-2">
        <ContrastColumn label="Without" tone="dim" items={without} />
        <ContrastColumn label="With" tone="gold" items={withCos} />
      </div>
    </section>
  );
}

function ContrastColumn({
  label,
  tone,
  items,
}: {
  label: string;
  tone: "dim" | "gold";
  items: string[];
}) {
  const isGold = tone === "gold";
  return (
    <div
      className={
        "flex flex-col gap-5 rounded-sm border p-6 " +
        (isGold
          ? "border-gold/30 bg-gold/[0.03]"
          : "border-luxe bg-card")
      }
      data-testid={`how-monday-${tone}`}
    >
      <div className="flex items-center gap-2">
        <span
          className={
            "font-mono text-[10px] uppercase tracking-[0.28em] " +
            (isGold ? "text-gold" : "text-fog")
          }
        >
          {label}
        </span>
        <HairlineDivider
          width="sm"
          tone={isGold ? "bright" : "muted"}
        />
      </div>
      <ul className="flex flex-col gap-3">
        {items.map((item) => (
          <li
            key={item}
            className="flex gap-3 text-sm leading-relaxed text-mist"
          >
            <span
              className={
                "mt-1 inline-block h-1 w-1 flex-shrink-0 rounded-full " +
                (isGold ? "bg-gold" : "bg-fog/60")
              }
              aria-hidden="true"
            />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── Section 3 · How the pipeline works (5 numbered steps) ───────────

function Pipeline() {
  const steps = [
    {
      n: 1,
      title: "Build a spokesperson",
      body:
        "A 4-step wizard captures the spokesperson's identity, brand voice, " +
        "and on-camera portrait. The portrait is rigged into a Runway avatar " +
        "you can re-use across every cut — same face every time, no re-shoots.",
    },
    {
      n: 2,
      title: "Feed the knowledge layer",
      body:
        "Upload docs, paste URLs, drop transcripts. The platform chunks + " +
        "embeds the content into a per-spokesperson knowledge index. Every " +
        "video the spokesperson stars in — and every live conversation they " +
        "hold — pulls answers from that index. No copy-pasting facts into " +
        "scripts; the brain stays in one place.",
    },
    {
      n: 3,
      title: "Pick a recipe",
      body:
        "Eighteen starter recipes cover the common formats: talking head, " +
        "cinematic visual, long-form ad, picture-in-picture, co-host, B-roll " +
        "splice, music bed, Reels, multi-language dub, voice design, storyboard " +
        "ad, dialogue scene, and more. Each recipe is a composition of named " +
        "primitives (generate_avatar_speech, generate_visual_clip, composite, " +
        "captions, etc.) — so adding a new recipe is one config file, not a " +
        "code branch.",
    },
    {
      n: 4,
      title: "Render the video",
      body:
        "A Django shell hands the recipe to a FastAPI media engine; the engine " +
        "calls Runway for avatar + visuals, ElevenLabs for voice when needed, " +
        "and composites the result. The finished render lands in your asset " +
        "library with full provenance — which spokesperson, which recipe, which " +
        "version of the knowledge.",
    },
    {
      n: 5,
      title: "Or hold a live conversation",
      body:
        "Press Talk on any spokesperson and the same identity becomes a live " +
        "WebRTC avatar — Runway streams audio + video, the platform supplies the " +
        "knowledge document, and a small set of tools (render a video, recall " +
        "knowledge, hand off to another spokesperson) lets the avatar do real " +
        "work mid-conversation, not just chat.",
    },
  ];
  return (
    <section className="flex flex-col gap-6" data-testid="how-pipeline">
      <SectionHeader number={2} title="How the pipeline works" />
      <p className="max-w-2xl text-sm leading-relaxed text-mist">
        You see the spokesperson, the recipe gallery, and the finished
        video. Underneath, five passes run end-to-end every time you ship a
        cut or open a conversation.
      </p>
      <ol className="flex flex-col gap-4">
        {steps.map((step) => (
          <li
            key={step.n}
            className="flex gap-6 rounded-sm border border-luxe bg-card p-6 transition-colors hover:border-gold/30"
            data-testid={`how-pipeline-step-${step.n}`}
          >
            <div
              className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border border-gold/40 bg-gold/5 font-mono text-sm text-gold"
              aria-hidden="true"
            >
              {String(step.n).padStart(2, "0")}
            </div>
            <div className="flex min-w-0 flex-col gap-2">
              <h3 className="font-display text-lg leading-snug text-cream md:text-xl">
                {step.title}
              </h3>
              <p className="text-sm leading-relaxed text-mist">
                {step.body}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

// ── Section 4 · What's live in the app today ────────────────────────
//
// EVERY ITEM IN THIS BLOCK MUST BE VERIFIABLE IN THE CURRENT SPA.
// If a feature is half-shipped or behind a flag, demote it to
// "Not built yet" below. No "coming soon", no "in beta" hedging here.

function LiveToday() {
  const features = [
    {
      title: "Spokesperson wizard",
      body:
        "4-step create flow (identity · voice · portrait · review). The " +
        "portrait bakes through Runway and the spokesperson is reusable " +
        "across every recipe and conversation.",
    },
    {
      title: "Knowledge layer",
      body:
        "Per-spokesperson knowledge index with chunk-level retrieval. " +
        "Upload docs, paste URLs, mine a transcript. Every avatar answer " +
        "and every script pulls from the same source.",
    },
    {
      title: "Recipe gallery (18 starters)",
      body:
        "Browse the recipe gallery at /recipes — each recipe ships a " +
        "metadata-driven form, runs end-to-end against the media engine, " +
        "and lands a composed render with full provenance.",
    },
    {
      title: "Realtime avatar conversations",
      body:
        "Press Talk on a spokesperson detail page to open a live " +
        "WebRTC session. Cost ticker, in-conversation tool dispatch " +
        "(render a video mid-chat, recall knowledge), and post-session " +
        "transcript capture all ship.",
    },
    {
      title: "Workspace library",
      body:
        "Asset library, video library, transcript miner, auto-script " +
        "drafts, publish bundles, personalized-video campaigns. Each " +
        "workspace surface lists what the studio has produced so far.",
    },
    {
      title: "Engine bridge (early)",
      body:
        "A spokesperson can surface answers from an external AI engine " +
        "(agents, spider data, knowledge graphs) over HTTP. v1 instance " +
        "powers a single live customer; per-workspace engine config is " +
        "the next slice.",
    },
  ];
  return (
    <section className="flex flex-col gap-6" data-testid="how-live-today">
      <SectionHeader number={3} title="What's live in the app today" />
      <header className="border-b border-luxe pb-3">
        <h2 className="font-display text-2xl tracking-tight text-cream md:text-3xl">
          Everything below ships{" "}
          <span className="italic gold-text">today.</span>
        </h2>
      </header>
      <div className="grid gap-4 sm:grid-cols-2">
        {features.map((f) => (
          <div
            key={f.title}
            className="flex flex-col gap-2 rounded-sm border border-luxe bg-card p-5"
            data-testid={`how-live-${f.title.toLowerCase().replace(/\s+/g, "-")}`}
          >
            <div className="flex items-center gap-2">
              <HairlineDivider width="sm" tone="bright" />
              <span className="font-display text-sm text-cream">
                {f.title}
              </span>
            </div>
            <p className="text-xs leading-relaxed text-mist">{f.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── Section 5 · What's NOT built yet (honest list) ──────────────────
//
// Pulled from `00-START-NEXT-SESSION.md` "Slice queue" + "queued"
// items at the time of authoring. The point of this block is: a
// third-party reader sees the real shape of the product, not the
// marketing version. Demote here freely; promote up only when a
// slice ships.

function NotBuiltYet() {
  const gaps = [
    {
      title: "A public paid tier",
      body:
        "No pricing yet. The product is live with one customer in early " +
        "access. We'll publish tiers once the second customer is onboarded.",
    },
    {
      title: "Self-serve sign-up",
      body:
        "Anyone can technically create an account, but workspace seeding, " +
        "billing, and tier gates assume an invited operator. Treat sign-up " +
        "as alpha until we say otherwise.",
    },
    {
      title: "Per-workspace engine connection (UI)",
      body:
        "The bridge tools that let a spokesperson surface a customer's " +
        "external engine work — but currently read one customer's URL from " +
        "an env var. A per-workspace EngineConnection model + admin UI is " +
        "the next queued slice.",
    },
    {
      title: "Light mode",
      body:
        "BRAND_IDENTITY_V3 ships dark only. Light mode is queued.",
    },
    {
      title: "Asset upload UI",
      body:
        "The backend accepts uploads (and the asset library renders them); " +
        "the upload wizard itself is queued.",
    },
    {
      title: "Multiple workspaces per user",
      body:
        "Today each operator account is bound to one workspace. Switching " +
        "between workspaces (and inviting teammates into one) is queued.",
    },
    {
      title: "Notifications · scheduled renders · public API",
      body:
        "No email / Slack / push alerts. No cron-style scheduled video " +
        "runs. No public API for developers. All three are roadmap, not " +
        "today.",
    },
    {
      title: "Voiceover recipes (VO.3–VO.6)",
      body:
        "Two voiceover slices shipped (provider + overlay primitive); " +
        "the recipe-gallery wiring and two more starters (cta_swap, " +
        "narrated_intro) are queued.",
    },
    {
      title: "Multi-provider avatar",
      body:
        "Runway is the only realtime avatar provider in v1. The provider " +
        "abstraction is drift-verified, but a second provider (HeyGen / " +
        "D-ID / push-to-speak) is not wired.",
    },
    {
      title: "Known avatar quirks",
      body:
        "The Runway avatar enforces a \"Hello, I'm [name]\" first-turn " +
        "shape we can't override via document or personality edits. Tool-" +
        "result narration is operator-mediated rather than spoken by the " +
        "avatar. Both are documented v1 limitations.",
    },
    {
      title: "YouTube ingest coverage",
      body:
        "Some YouTube URLs report as \"processed\" but yield no usable " +
        "transcript (extractor coverage incomplete). Tracked; fix is in " +
        "the K7 queue.",
    },
  ];
  return (
    <section className="flex flex-col gap-6" data-testid="how-not-built">
      <SectionHeader number={4} title="What's not built yet (honest)" />
      <header className="border-b border-luxe pb-3">
        <h2 className="font-display text-2xl tracking-tight text-cream md:text-3xl">
          Where the product{" "}
          <span className="italic gold-text">isn't</span> yet.
        </h2>
      </header>
      <p className="max-w-2xl text-sm leading-relaxed text-mist">
        Read this before opening a deal. The point of this list is so a
        third-party reader sees the real shape of the product, not the
        marketing version. If something here matters to your use case,
        tell us — your input decides what we build next.
      </p>
      <ul className="flex flex-col">
        {gaps.map((gap) => (
          <li
            key={gap.title}
            className="grid gap-3 border-b border-luxe py-4 last:border-b-0 md:grid-cols-[200px_1fr] md:items-baseline md:gap-8"
            data-testid={`how-not-${gap.title.toLowerCase().split(" ").slice(0, 3).join("-")}`}
          >
            <div className="flex items-center gap-2">
              <span
                className="h-1 w-1 rounded-full bg-gold/40"
                aria-hidden="true"
              />
              <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-fog">
                {gap.title}
              </span>
            </div>
            <p className="text-sm leading-relaxed text-mist">{gap.body}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

// ── Section 6 · Early-access CTA ────────────────────────────────────
//
// signal-studio uses a paid-interest pill + form posting to a real
// backend endpoint. character-os has no such endpoint and is invite-
// only — so the CTA opens a mailto: to the parent-company contact.
// Honest match for the page's "early access" framing.

function EarlyAccessCta() {
  const subject = encodeURIComponent(
    `${BRAND.product.name} — early access inquiry`,
  );
  const body = encodeURIComponent(
    `Hi ${parentBrand.contact.name.split(" ")[0]},\n\n` +
      `I'd like to learn more about ${BRAND.product.name}. ` +
      `Here's what I'd use it for:\n\n— \n\n` +
      `(Source: how-it-works)`,
  );
  const mailto = `mailto:${parentBrand.contact.email}?subject=${subject}&body=${body}`;
  return (
    <section className="flex flex-col gap-6" data-testid="how-cta">
      <SectionHeader number={5} title="Early access" />
      <div className="relative overflow-hidden rounded-sm border border-gold/30 bg-gradient-to-br from-gold/[0.05] via-card to-card p-8 md:p-10">
        <div className="flex flex-col gap-5">
          <h2 className="font-display text-3xl leading-tight tracking-tight text-cream md:text-4xl">
            Help shape what gets{" "}
            <span className="italic gold-text">built next.</span>
          </h2>
          <p className="max-w-2xl text-sm leading-relaxed text-mist md:text-base">
            {BRAND.product.name} is in early access. If you'd use this — a
            spokesperson that holds knowledge, stars in your videos, and
            holds a conversation — write us a brief. Tell us your use case
            and what would make it worth paying for. That input decides
            what we build first.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <a
              href={mailto}
              className="inline-flex items-center gap-2 rounded-sm border border-gold bg-gold px-5 py-2.5 font-mono text-[11px] uppercase tracking-[0.22em] text-ink transition-colors hover:bg-gold-bright"
              data-testid="how-cta-mailto"
            >
              Send a brief
              <ArrowRight className="h-3.5 w-3.5" />
            </a>
            <Link
              to="/about"
              className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.22em] text-fog transition-colors hover:text-gold"
              data-testid="how-cta-about"
            >
              About 24/7 Global AI
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="pt-4">
            <HairlineDivider width="lg" tone="muted" />
          </div>
          <DoctrineQuote size="sm">
            One spokesperson · every channel · the same brain across all of
            them.
          </DoctrineQuote>
        </div>
      </div>
    </section>
  );
}

// ── Section 7 · FAQ ─────────────────────────────────────────────────

function Faq() {
  const items = [
    {
      q: "Is this a video editor?",
      a:
        "No. It's a spokesperson layer that produces video. You don't edit " +
        "timelines; you pick a recipe and a script (or have one drafted) " +
        "and the platform composes the cut.",
    },
    {
      q: "Who renders the avatars and the voice?",
      a:
        "Runway powers the on-camera avatar (recorded and realtime). " +
        "ElevenLabs powers voice when a recipe calls for voice design or " +
        "narration. OpenAI powers the knowledge embeddings and script " +
        "synthesis. The platform composes the result locally.",
    },
    {
      q: "Where does the knowledge come from?",
      a:
        "Whatever you give it — uploaded documents, pasted URLs, mined " +
        "transcripts of previous videos. Everything is chunked and " +
        "embedded into a per-spokesperson index. Every answer the " +
        "spokesperson gives (in a live conversation or as a baked script) " +
        "is grounded in that index.",
    },
    {
      q: "Can the spokesperson hold a real conversation?",
      a:
        "Yes — Runway's realtime avatar streams over WebRTC. The platform " +
        "loads the spokesperson's knowledge document, dispatches " +
        "tool calls (render a video, recall knowledge, hand off to another " +
        "spokesperson) mid-conversation, and persists the transcript when " +
        "the session ends.",
    },
    {
      q: "Can I connect my own AI agents or backend?",
      a:
        "In v1 a spokesperson can call out to an external HTTP engine. " +
        "We currently hardcode the engine URL for one live customer; a " +
        "per-workspace EngineConnection model + admin UI is the next " +
        "queued slice. If this matters for your use case, tell us when " +
        "you write the brief.",
    },
    {
      q: "What does it cost to run?",
      a:
        "There is no published price yet. Runtime cost per video and per " +
        "conversation is bounded — the platform tracks an estimate before " +
        "each render or session and an actual after. Pricing tiers are in " +
        "design.",
    },
    {
      q: "Is the underlying brain locked to one provider?",
      a:
        "The avatar provider (Runway) is single-source in v1, but the " +
        "interface is abstracted and drift-verified — swapping or adding a " +
        "second provider is a tightly scoped change rather than a rewrite.",
    },
  ];
  return (
    <section className="flex flex-col gap-6" data-testid="how-faq">
      <SectionHeader number={6} title="FAQ" />
      <header className="border-b border-luxe pb-3">
        <h2 className="font-display text-2xl tracking-tight text-cream md:text-3xl">
          Common <span className="italic gold-text">questions.</span>
        </h2>
      </header>
      <dl className="flex flex-col">
        {items.map((item) => (
          <div
            key={item.q}
            className="grid gap-3 border-b border-luxe py-5 last:border-b-0 md:grid-cols-[280px_1fr] md:gap-10"
            data-testid={`how-faq-${item.q.toLowerCase().split(" ").slice(0, 3).join("-")}`}
          >
            <dt className="font-display text-base italic text-cream/90 md:text-lg">
              {item.q}
            </dt>
            <dd className="text-sm leading-relaxed text-mist">{item.a}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

// ── Closer ──────────────────────────────────────────────────────────

function Closer() {
  return (
    <div
      className="flex items-center justify-between border-t border-luxe pt-6 font-mono text-[10px] uppercase tracking-[0.28em] text-fog"
      data-testid="how-closer"
    >
      <span>
        {BRAND.product.name} · {BRAND.product.subtitle}
      </span>
      <span className="font-display italic text-gold/80 normal-case tracking-normal text-sm">
        {parentBrand.poweredByLabel}
      </span>
    </div>
  );
}
