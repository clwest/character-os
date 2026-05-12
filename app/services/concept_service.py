import json
import logging
from typing import Optional

from ..config import Settings
from ..models import AdConcept, ConceptRequest, ConceptResponse

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a senior creative director generating short cinematic ad concepts. "
    "Return strictly valid JSON matching the requested schema. No prose."
)


def _user_prompt(req: ConceptRequest) -> str:
    return (
        "Generate 3 distinct cinematic short-ad concepts for the following.\n"
        f"Business: {req.business}\n"
        f"Product/service: {req.product or 'n/a'}\n"
        f"Tone: {req.tone or 'cinematic'}\n"
        f"Audience: {req.audience or 'general'}\n\n"
        "Return JSON with this exact schema:\n"
        "{\n"
        '  "concepts": [\n'
        '    {"title": str, "hook": str, "visual": str, "caption": str, "cta": str}\n'
        "  ],  // exactly 3 items\n"
        '  "recommended_index": int (0-2),\n'
        '  "runway_prompt": str  // single cinematic video prompt for the recommended concept,\n'
        "                        // 1-2 sentences, vivid camera + lighting + subject + motion\n"
        "}\n"
    )


def _mock_concepts(req: ConceptRequest) -> ConceptResponse:
    biz = req.business.strip() or "the brand"
    product = req.product.strip() or "the product"
    tone = req.tone.strip() or "cinematic"
    audience = req.audience.strip() or "modern customers"

    concepts = [
        AdConcept(
            title=f"Origin Spark — {biz}",
            hook=f"Where {product} began.",
            visual=(
                f"Slow push-in on a single craftsman's hands shaping {product}, "
                f"warm tungsten light, dust motes drifting; cuts to a finished hero shot."
            ),
            caption=f"Built for {audience}. Made to last.",
            cta="Discover the story →",
        ),
        AdConcept(
            title=f"Daily Ritual — {biz}",
            hook=f"Your day, upgraded by {product}.",
            visual=(
                f"Fast-cut montage of {audience} weaving {product} into morning, work, "
                f"and night routines, neon-and-glass color palette, kinetic camera."
            ),
            caption=f"From sunrise to skyline — {biz} keeps up.",
            cta="Try it today →",
        ),
        AdConcept(
            title=f"Frontier — {biz}",
            hook=f"What {product} unlocks next.",
            visual=(
                f"Wide aerial of a vast landscape at golden hour, lone figure activating "
                f"{product}, light blooms outward, score swells; ends on logo."
            ),
            caption=f"For {audience} ready to move first.",
            cta="Step forward →",
        ),
    ]
    runway_prompt = (
        f"Cinematic {tone} ad for {biz}: slow dolly-in on hero {product}, "
        f"golden-hour rim light, shallow depth of field, subtle particle haze, "
        f"smooth handheld motion, final beat reveals brand mark."
    )
    return ConceptResponse(
        concepts=concepts,
        recommended_index=1,
        runway_prompt=runway_prompt,
        mock_mode=True,
    )


def _coerce_response(payload: dict, fallback: ConceptResponse) -> ConceptResponse:
    raw = payload.get("concepts") or []
    concepts: list[AdConcept] = []
    for item in raw[:3]:
        try:
            concepts.append(AdConcept(**item))
        except Exception:
            continue
    if len(concepts) != 3:
        return fallback
    idx = payload.get("recommended_index", 0)
    if not isinstance(idx, int) or not 0 <= idx <= 2:
        idx = 0
    runway_prompt = payload.get("runway_prompt") or fallback.runway_prompt
    return ConceptResponse(
        concepts=concepts,
        recommended_index=idx,
        runway_prompt=runway_prompt,
        mock_mode=False,
    )


# ---- PR EJ — short spoken-ad script generation --------------------
#
# Different prompt shape from `generate_concepts`: produces ONE
# natural-spoken script (the kind the avatar will read aloud) sized
# to fit Runway's 300-char `speech.text` cap. The concept endpoint
# returns hook/visual/caption metadata — useful for thinking about
# the ad but not directly speakable. This produces a script the
# operator can paste straight into Step 2's variant.

SCRIPT_SYSTEM_PROMPT_SHORT = (
    "You write ONE 15-second spoken commercial for an AI brand "
    "spokesperson. ONE complete ad, NOT a fragment of a longer story.\n"
    "\n"
    "STRUCTURE — mandatory three beats:\n"
    "  1. HOOK (1 sentence, 8-15 words). A surprising claim, a "
    "question, or a tension that grabs attention.\n"
    "  2. SINGLE CLAIM (1-2 sentences). Make ONE specific promise. "
    "Pick THE punchiest angle from the campaign brief. Do NOT try to "
    "summarise everything in the brief.\n"
    "  3. CTA (1 sentence, 6-10 words). A specific action with a verb.\n"
    "\n"
    "STAND-ALONE RULE — if a listener heard ONLY this script, they "
    "should feel the ad is COMPLETE. No setup-without-payoff. No "
    "'first… then… finally…' narratives. No 'this is how we built it' "
    "stories that need 30+ seconds to land. If the campaign brief "
    "contains a complex story (a build journey, a multi-stage feature "
    "set, a founder narrative), pick ONE angle from it and go deep on "
    "that single angle. The rest of the story is for a longer ad — "
    "not this one.\n"
    "\n"
    "VOICE — natural spoken English. The avatar reads this aloud on "
    "camera. No stage directions. No parenthetical asides. No "
    "quotation marks around the whole script. No 'voiceover' labels. "
    "Just the words the avatar will say.\n"
    "\n"
    "LENGTH — STRICT MAX 280 characters total. The avatar API rejects "
    "anything over 300 chars and we truncate at 300, which produces "
    "mid-word cutoffs. Stay well under 280. Target 200-260 characters. "
    "If your draft is over 280, you wrote too much — cut a sentence, "
    "don't rely on the truncator.\n"
    "\n"
    "TITLE — also generate a 3-6 word noun phrase title summarising the "
    "ad's angle. The operator sees this in the variant chip row instead "
    "of generic 'Ad 1, Ad 2, Ad 3'. Examples: 'Founder pitch for indie "
    "SaaS', 'Coffee subscription hook', 'YC application angle'.\n"
    "\n"
    "OUTPUT FORMAT — return EXACTLY two lines, no preamble:\n"
    "TITLE: <your 3-6 word noun phrase>\n"
    "SCRIPT: <your single complete ≤280-char ad>\n"
    "\n"
    "Do NOT add any words like 'Here is your spoken ad script:' or any "
    "other framing. Just TITLE: and SCRIPT: lines."
)


SCRIPT_SYSTEM_PROMPT_LONG = (
    "You write longer-form (45-60 second) spoken ad scripts for an AI "
    "brand spokesperson. The script will be read aloud by an avatar on "
    "camera AND chunked at sentence boundaries for rendering — so use "
    "SHORT, SELF-CONTAINED SENTENCES. Each sentence should stand on "
    "its own. Avoid run-ons or sentences that depend on the previous "
    "one. No stage directions. No parenthetical asides. No quotation "
    "marks around the script. No 'voiceover' labels. Just the spoken "
    "words.\n"
    "\n"
    "STRUCTURE — open with a 1-2 sentence hook, three or four micro-"
    "beats of substance / proof in the middle, close with one clear "
    "call-to-action. Treat each sentence as a distinct beat — the "
    "renderer cuts on sentence boundaries. THIS format gives you the "
    "room to tell a multi-beat story (a build journey, a feature tour, "
    "a founder narrative). Use that room.\n"
    "\n"
    "LENGTH — Target 1000-1400 characters total (roughly 35-50 seconds "
    "when read aloud). Hard ceiling 1500 chars.\n"
    "\n"
    "TITLE — also generate a 3-6 word noun phrase title summarising "
    "the ad's angle. The operator sees this in the variant chip row "
    "instead of generic 'Ad 1, Ad 2, Ad 3'. For long ads, the title "
    "should signal the story arc: 'Why we built Character OS', "
    "'Founder origin story', 'Hackathon-to-product journey'.\n"
    "\n"
    "OUTPUT FORMAT — return EXACTLY two lines, no preamble:\n"
    "TITLE: <your 3-6 word noun phrase>\n"
    "SCRIPT: <your spoken ad script>\n"
    "\n"
    "Do NOT add any framing words like 'Here is your spoken ad script:' "
    "Just TITLE: and SCRIPT: lines."
)


def _script_user_prompt(
    business: str,
    product: str,
    audience: str,
    tone: str,
    *,
    mode: str = "short",
    spin: Optional[str] = None,
) -> str:
    extra = f"\nAngle hint: {spin}" if spin and spin.strip() else ""
    target = (
        "1000-1400 chars (35-50 seconds spoken)"
        if mode == "long"
        else "200-260 chars (one Runway avatar_videos line)"
    )
    return (
        f"Write ONE spoken ad script, target length {target}:\n"
        f"Business: {business or '(unspecified)'}\n"
        f"Product / service: {product or '(unspecified)'}\n"
        f"Audience: {audience or 'general'}\n"
        f"Tone: {tone or 'punchy'}{extra}\n\n"
        "Return ONLY the spoken script as plain text. No JSON, no "
        "markdown, no labels, no surrounding quotation marks. "
        "Just the words to be spoken."
    )


def _clean_script_output(raw: str) -> str:
    """Strip the most common LLM ornamentation: wrapping quotes,
    stray 'Script:' labels, leading dashes, surrounding code fences."""
    if not raw:
        return ""
    text = raw.strip()
    # Strip code fences
    for fence in ("```", "~~~"):
        if text.startswith(fence):
            text = text.lstrip("`~ \n")
        if text.endswith(fence):
            text = text.rstrip("`~ \n")
    # Strip leading "Here is the script:" / "Here's the ad:" / etc.
    # ornaments that smaller open models add despite instructions.
    # PR EU — added "Here is your spoken ad script:" + variants that
    # Llama keeps emitting despite the explicit prompt instruction.
    for prefix in (
        "Here is your spoken ad script:",
        "Here's your spoken ad script:",
        "Here is your ad script:",
        "Here's your ad script:",
        "Here is your ad:",
        "Here's your ad:",
        "Here is the script:",
        "Here's the script:",
        "Here is the ad:",
        "Here's the ad:",
        "Here is the spoken script:",
        "Here's the spoken script:",
        "Here's a punchy spoken ad script:",
        "Here is a punchy spoken ad script:",
        "Script:",
        "Ad:",
        "Script -",
        "Ad -",
    ):
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].lstrip()
    # Strip wrapping quotes
    if len(text) >= 2 and text[0] in {'"', "'", "“", "‘"} and text[-1] in {'"', "'", "”", "’"}:
        text = text[1:-1].strip()
    return text


# PR EU — sentence-boundary truncation safety net. The system prompt
# asks Llama for ≤280 chars but it routinely exceeds that. Without
# this, the 300-char DB / Runway cap truncates mid-word ("...buil")
# and the spoken ad ends abruptly. Find the last sentence-ending
# punctuation under `max_chars` and truncate there; if no sentence
# boundary fits, truncate at the last word boundary.
_SENTENCE_ENDERS = ".!?"

def _truncate_at_sentence(text: str, max_chars: int = 280) -> str:
    if not text or len(text) <= max_chars:
        return text
    window = text[:max_chars]
    # Find the last sentence ender in the window.
    last_end = -1
    for ender in _SENTENCE_ENDERS:
        idx = window.rfind(ender)
        if idx > last_end:
            last_end = idx
    if last_end >= 60:
        # Include the ender itself; strip trailing whitespace.
        return window[: last_end + 1].rstrip()
    # No sentence-ending punctuation found in window — fall back to
    # last word boundary so we at least don't cut mid-word.
    last_space = window.rfind(" ")
    if last_space >= 60:
        return window[:last_space].rstrip()
    # Last resort — hard truncate. Unlikely to hit because the prompt
    # already targets 200-260 chars.
    return window.rstrip()


# PR EU — parse the TITLE: / SCRIPT: structured output the prompt
# requests. Returns (title, script). Falls back gracefully when the
# model didn't follow the format — older mock paths and any LLM that
# emits plain script without the TITLE prefix still work.
def _parse_titled_output(raw: str) -> tuple[str, str]:
    text = (raw or "").strip()
    if not text:
        return "", ""
    title = ""
    script_lines: list[str] = []
    in_script = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if in_script:
                script_lines.append("")
            continue
        lower = stripped.lower()
        if not title and (lower.startswith("title:") or lower.startswith("title -")):
            colon = stripped.find(":")
            dash = stripped.find("-")
            cut = colon if colon != -1 else dash
            title = stripped[cut + 1 :].strip().strip('"\'""\'\'')
            continue
        if lower.startswith("script:") or lower.startswith("script -"):
            colon = stripped.find(":")
            dash = stripped.find("-")
            cut = colon if colon != -1 else dash
            script_lines.append(stripped[cut + 1 :].lstrip())
            in_script = True
            continue
        # Once we're in the SCRIPT block, everything else is body.
        if in_script:
            script_lines.append(stripped)
        elif not title:
            # No labels at all; treat the whole blob as script.
            script_lines.append(stripped)
            in_script = True
    script = "\n".join(s for s in script_lines if s is not None).strip()
    # Cap title; the avatar variant title input has its own length
    # limit (80 chars). Trim aggressively here.
    if title and len(title) > 60:
        title = title[:60].rstrip()
    return title, script


def generate_ad_script(
    business: str,
    product: str,
    audience: str,
    tone: str,
    settings: Settings,
    *,
    mode: str = "short",
    spin: Optional[str] = None,
) -> dict:
    """Generate one spoken ad script for the supplied brief.

    ``mode``:
      - ``"short"`` (default) — 200-260 chars, fits one
        `avatar_videos` call (Runway's 300-char cap).
      - ``"long"``  — 1000-1400 chars, ~35-50s of speech, fed into
        the long_ad_service's chunk-and-stitch pipeline.

    Returns a dict with ``script`` (the cleaned text), ``provider``
    (which LLM produced it), ``model``, ``mode``, and ``mock_mode``
    (True when no real LLM was reachable and we returned a
    templated fallback).

    Never raises. Falls back to a templated script when the LLM is
    unreachable, returns malformed output, or the openai_mock gate
    fires for the cloud provider.
    """
    provider = (settings.llm_provider or "openai").strip().lower()
    mode_norm = (mode or "short").strip().lower()
    if mode_norm not in {"short", "long"}:
        mode_norm = "short"

    def _mock_script() -> dict:
        biz = (business or "").strip() or "our brand"
        prod = (product or "").strip() or "this product"
        aud = (audience or "").strip() or "you"
        if mode_norm == "long":
            # Multi-beat fallback ~1200 chars. Short sentences so the
            # long-ad chunker has clean cut points.
            sentences = [
                f"Hey {aud}. I want to tell you about {biz}.",
                f"We built {prod} because we got tired of the old way.",
                "The old way is slow. The old way is generic. The old way wastes your time.",
                f"With {biz}, you stop fighting tools and start shipping work.",
                "It learns your context, your voice, and your brand.",
                "Every output stays consistent. Every campaign feels yours.",
                f"You skip the busywork, and {prod} handles the rest.",
                "Founders use it to move faster. Teams use it to stay aligned.",
                f"Try {biz} today. See the difference in one afternoon.",
                "Visit our site, watch a real demo, and see for yourself.",
            ]
            script = " ".join(sentences)
            title = f"{biz} long-form pitch"
        else:
            script = (
                f"Hey {aud} — meet {biz}. {prod} done right, no fluff. "
                f"Built to ship, designed to last. See it for yourself today."
            )
            if len(script) > 260:
                script = script[:257].rstrip() + "..."
            title = f"{biz} hook"
        return {
            "script": script,
            "title": title,
            "provider": provider,
            "model": "(template fallback)",
            "mode": mode_norm,
            "mock_mode": True,
        }

    if provider == "openai" and settings.openai_mock:
        return _mock_script()

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed; returning mock script")
        return _mock_script()

    if provider == "ollama":
        client = OpenAI(
            api_key="ollama",
            base_url=settings.ollama_base_url,
        )
        model = settings.ollama_model
    else:
        client = OpenAI(api_key=settings.openai_api_key)
        model = settings.openai_model

    system_prompt = (
        SCRIPT_SYSTEM_PROMPT_LONG if mode_norm == "long" else SCRIPT_SYSTEM_PROMPT_SHORT
    )

    try:
        logger.info(
            "ad script generation via %s model=%s mode=%s",
            provider, model, mode_norm,
        )
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": _script_user_prompt(
                        business, product, audience, tone,
                        mode=mode_norm, spin=spin,
                    ),
                },
            ],
            # Higher temperature → more variation across re-rolls.
            temperature=0.95,
        )
        raw: Optional[str] = completion.choices[0].message.content
        # PR EU — parse the TITLE: / SCRIPT: structured format first,
        # THEN clean the script portion. Title may be empty for long
        # mode (system prompt only asks for title in short mode) or
        # when the LLM ignores the format (graceful fallback handled
        # in _parse_titled_output).
        parsed_title, parsed_script = _parse_titled_output(raw or "")
        cleaned = _clean_script_output(parsed_script)
        if not cleaned:
            logger.warning("ad script generation returned empty content")
            return _mock_script()
        # PR EU — sentence-boundary truncation. Short mode is hard-
        # bounded by Runway's 300-char cap; truncate at the last
        # sentence ender below 280 so spoken ads never cut off mid-
        # word. Long mode keeps the existing 1500-char ceiling via
        # the previous loop pattern.
        if mode_norm == "long":
            ceiling = 1500
            if len(cleaned) > ceiling:
                cut = cleaned[:ceiling]
                for sep in (". ", "! ", "? "):
                    idx = cut.rfind(sep)
                    if idx > 100:
                        cleaned = cut[: idx + 1].rstrip()
                        break
                else:
                    cleaned = cut.rstrip() + "..."
        else:
            cleaned = _truncate_at_sentence(cleaned, 280)
        return {
            "script": cleaned,
            "title": parsed_title or "",
            "provider": provider,
            "model": model,
            "mode": mode_norm,
            "mock_mode": False,
        }
    except Exception as exc:
        logger.exception(
            "ad script generation failed (provider=%s model=%s mode=%s): %s",
            provider, model, mode_norm, exc,
        )
        return _mock_script()


def generate_concepts(req: ConceptRequest, settings: Settings) -> ConceptResponse:
    """PR EH — provider-aware concept generation. Branches on
    `settings.llm_provider`:

      - `openai` (default) — chat.completions against the OpenAI
        cloud API. Requires OPENAI_API_KEY; falls back to mock when
        the key is empty (`settings.openai_mock=True`).
      - `ollama` — chat.completions against a local Ollama server
        via its OpenAI-compatible endpoint (default
        http://localhost:11434/v1). No API key needed. Falls back to
        mock when Ollama is unreachable or the model returns junk.

    Both paths use the same OpenAI Python client — Ollama implements
    the chat.completions API surface byte-for-byte. The only change
    is the base_url + model name.
    """
    fallback = _mock_concepts(req)
    provider = (settings.llm_provider or "openai").strip().lower()

    # OpenAI cloud path stays gated on the API key (existing
    # behaviour). Mock returns immediately when no key is set.
    if provider == "openai" and settings.openai_mock:
        return fallback

    try:
        from openai import OpenAI  # lazy import — same client for both providers
    except ImportError:
        logger.warning("openai package not installed; returning mock concepts")
        return fallback

    # Provider-specific client construction. The body shape below is
    # identical for both providers — Ollama implements
    # chat.completions byte-for-byte including `response_format`.
    if provider == "ollama":
        client = OpenAI(
            api_key="ollama",  # any non-empty string; ignored by Ollama
            base_url=settings.ollama_base_url,
        )
        model = settings.ollama_model
        logger.info(
            "concept generation via ollama model=%s base=%s",
            model, settings.ollama_base_url,
        )
    else:
        client = OpenAI(api_key=settings.openai_api_key)
        model = settings.openai_model

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(req)},
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )
        content: Optional[str] = completion.choices[0].message.content
        if not content:
            logger.warning("concept generation returned empty content (provider=%s)", provider)
            return fallback
        payload = json.loads(content)
        return _coerce_response(payload, fallback)
    except Exception as exc:
        logger.exception("concept generation failed (provider=%s): %s", provider, exc)
        return fallback
