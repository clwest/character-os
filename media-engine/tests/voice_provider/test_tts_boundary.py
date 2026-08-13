"""TTS-boundary architectural test — §19 Step 6.a (SESSION 245).

Enforces §17.4.a bullets 1–2:

* ``VoiceDesignProvider`` owns identity creation only. Its
  responsibility ends once it returns a durable ``voice_id``.
  It NEVER synthesizes speech.
* ``TextToSpeechProvider`` consumes approved voices only. TTS
  never knows how a voice was created.

The clean boundary already exists in the current code (verified
by inspection at Step 6 planning): TTS providers accept
``voice_id`` as input and never POST to ``/v1/voices``. This
test makes the boundary a mechanical invariant, not a code-
review vigilance requirement (SESSION 245 discipline: "A test
should make this architectural boundary explicit, not merely
rely on today's imports").

Approach: static AST inspection of import statements in each
package's Python files. The two packages must not import from
each other. If a future refactor accidentally couples them, this
test fails immediately.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

from app.services import tts_provider as tts_pkg
from app.services import voice_provider as voice_pkg


def _package_dir(pkg) -> Path:
    return Path(inspect.getfile(pkg)).parent


def _iter_python_files(pkg_dir: Path) -> list[Path]:
    """All .py files in the package root. Sub-packages included
    for future-proofing; test/build artefacts excluded.
    """
    return sorted(p for p in pkg_dir.rglob("*.py") if "__pycache__" not in p.parts)


def _module_dotted_paths(source: str) -> set[str]:
    """Collect every dotted module path referenced in ``import``
    and ``from ... import`` statements. Relative imports resolve
    to their absolute dotted form at import time; the AST alone
    doesn't have that context, so we compare against fragments
    that survive both absolute and relative expression.
    """
    tree = ast.parse(source)
    dotted: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                dotted.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                dotted.add(node.module)
    return dotted


def _references_package(source: str, forbidden_leaf: str) -> list[str]:
    """Return dotted module paths in ``source`` whose final path
    segment equals ``forbidden_leaf``, or that contain
    ``.{forbidden_leaf}.`` / ``.{forbidden_leaf}`` as a segment
    boundary. Handles absolute (``app.services.tts_provider``)
    and relative-then-referenced (``..tts_provider``) forms.
    """
    hits: list[str] = []
    for dotted in _module_dotted_paths(source):
        segments = dotted.split(".")
        if forbidden_leaf in segments:
            hits.append(dotted)
    return hits


def test_voice_provider_package_does_not_import_tts_provider():
    """Every .py file in ``app.services.voice_provider`` must
    contain zero imports referencing ``tts_provider``. If this
    test fails, the boundary has been breached — revisit
    §17.4.a bullets 1–2 before landing.
    """
    voice_dir = _package_dir(voice_pkg)
    offenders: list[tuple[str, list[str]]] = []
    for path in _iter_python_files(voice_dir):
        source = path.read_text(encoding="utf-8")
        hits = _references_package(source, "tts_provider")
        if hits:
            offenders.append((str(path.relative_to(voice_dir.parent)), hits))
    assert offenders == [], (
        f"voice_provider package imports tts_provider — §17.4.a "
        f"boundary violation. Voice authoring must never depend "
        f"on the TTS abstraction. Offenders:\n"
        f"  {offenders}"
    )


def test_tts_provider_package_does_not_import_voice_provider():
    """Symmetric check: TTS must not import from voice-authoring
    either. TTS consumes an already-existing ``voice_id`` string;
    it doesn't need to know how the identity was created.
    """
    tts_dir = _package_dir(tts_pkg)
    offenders: list[tuple[str, list[str]]] = []
    for path in _iter_python_files(tts_dir):
        source = path.read_text(encoding="utf-8")
        hits = _references_package(source, "voice_provider")
        if hits:
            offenders.append((str(path.relative_to(tts_dir.parent)), hits))
    assert offenders == [], (
        f"tts_provider package imports voice_provider — §17.4.a "
        f"boundary violation. TTS must never depend on the voice-"
        f"authoring abstraction. Offenders:\n"
        f"  {offenders}"
    )


def test_voice_provider_does_not_expose_synthesize_method():
    """Second-line guard: even if imports stayed clean, a
    ``synthesize`` method sneaking onto the Protocol would blur
    the boundary. §17.4.a bullet 1 is explicit — voice authoring
    NEVER synthesizes speech.

    Check both the Protocol and every concrete adapter surface.
    """
    from app.services.voice_provider import VoiceDesignProvider
    from app.services.voice_provider.mock import MockVoiceProvider

    for cls in (VoiceDesignProvider, MockVoiceProvider):
        method_names = {
            name for name in dir(cls)
            if not name.startswith("_")
        }
        forbidden = {"synthesize", "speak", "render_speech", "tts"}
        overlap = method_names & forbidden
        assert overlap == set(), (
            f"{cls.__name__} exposes TTS-like method(s) {overlap} — "
            f"§17.4.a bullet 1 violation. Voice authoring must "
            f"never synthesize speech."
        )


def test_tts_provider_does_not_expose_authoring_methods():
    """Symmetric second-line guard for TTS. §17.4.a bullet 2:
    TTS consumes approved voices only; it never creates or
    clones them.
    """
    from app.services.tts_provider import TextToSpeechProvider

    method_names = {
        name for name in dir(TextToSpeechProvider)
        if not name.startswith("_")
    }
    forbidden = {"design_voice", "clone_voice", "create_voice", "enroll_voice"}
    overlap = method_names & forbidden
    assert overlap == set(), (
        f"TextToSpeechProvider exposes voice-authoring method(s) "
        f"{overlap} — §17.4.a bullet 2 violation. TTS must never "
        f"create or clone voices."
    )
