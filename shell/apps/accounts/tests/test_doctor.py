"""Tests for the runtime-truth doctor (P1 2.4-a).

The doctor is a general project capability that refuses to open a
new slice when critical operational documentation has silently
drifted beyond the code it describes. INVENTORY is the first
consumer; these tests exercise the discovery + check logic against
in-memory fixture docs so they do not depend on the real docs/
tree or the real git HEAD.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from apps.accounts.management.commands.doctor import (
    _extract_sha,
    _parse_frontmatter,
    run_doctor,
)


def _write_regenerated(
    dir_: Path,
    *,
    name: str = "INVENTORY.md",
    sha: str | None = "abc1234",
    generated_at: str | None = "2026-07-22T05:55:43+00:00",
    status: str = "regenerated",
) -> Path:
    lines = ["---", f"status: {status}"]
    if generated_at is not None:
        lines.append(f"generated_at: {generated_at}")
    if sha is not None:
        lines.append(f"git_sha: {sha}")
    lines += ["---", "", "# body"]
    path = dir_ / name
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


class TestFrontmatterParser:
    def test_flat_kv_pairs_parse(self, tmp_path: Path) -> None:
        doc = _write_regenerated(tmp_path)
        fm = _parse_frontmatter(doc)
        assert fm["status"] == "regenerated"
        assert fm["git_sha"] == "abc1234"
        assert fm["generated_at"] == "2026-07-22T05:55:43+00:00"

    def test_quoted_values_are_unwrapped(self, tmp_path: Path) -> None:
        doc = tmp_path / "d.md"
        doc.write_text(
            '---\ntitle: "Character OS"\nstatus: regenerated\n---\n',
            encoding="utf-8",
        )
        fm = _parse_frontmatter(doc)
        assert fm["title"] == "Character OS"

    def test_missing_frontmatter_returns_empty(self, tmp_path: Path) -> None:
        doc = tmp_path / "no-fm.md"
        doc.write_text("# just a heading\n", encoding="utf-8")
        assert _parse_frontmatter(doc) == {}

    def test_unterminated_frontmatter_returns_empty(
        self, tmp_path: Path
    ) -> None:
        doc = tmp_path / "bad.md"
        doc.write_text("---\nstatus: regenerated\n\n# body\n", encoding="utf-8")
        assert _parse_frontmatter(doc) == {}


class TestExtractSha:
    def test_bare_sha_returned_as_is(self) -> None:
        assert _extract_sha("f542434") == "f542434"

    def test_trailing_annotation_stripped(self) -> None:
        assert _extract_sha("f542434 (working tree dirty)") == "f542434"

    def test_none_and_empty_return_none(self) -> None:
        assert _extract_sha(None) is None
        assert _extract_sha("") is None
        assert _extract_sha("   ") is None


class TestRunDoctor:
    def test_clean_when_sha_matches_and_fresh(self, tmp_path: Path) -> None:
        fresh = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        _write_regenerated(tmp_path, sha="f542434", generated_at=fresh)
        results = run_doctor(
            docs_root=tmp_path, head_sha="f542434", max_age_days=30.0
        )
        assert len(results) == 1
        assert results[0].blocking == []
        assert results[0].advisory == []
        assert results[0].clean is True

    def test_sha_mismatch_within_stale_window_is_advisory_only(
        self, tmp_path: Path
    ) -> None:
        # SESSION 222 shape: same-session commits move HEAD faster
        # than an INVENTORY regen is warranted; fresh SHA drift
        # advises but does not block.
        fresh = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        _write_regenerated(tmp_path, sha="9ccf714", generated_at=fresh)
        results = run_doctor(
            docs_root=tmp_path,
            head_sha="f542434",
            max_age_days=30.0,
            max_stale_age_days=7.0,
        )
        assert len(results) == 1
        assert results[0].clean is True
        assert any(
            "regen recommended" in msg for msg in results[0].advisory
        )

    def test_sha_mismatch_past_stale_window_blocks(
        self, tmp_path: Path
    ) -> None:
        # S147/S151/S221 pathology: SHA drift + old age = block.
        old = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        _write_regenerated(tmp_path, sha="9ccf714", generated_at=old)
        results = run_doctor(
            docs_root=tmp_path,
            head_sha="f542434",
            max_age_days=30.0,
            max_stale_age_days=7.0,
        )
        assert results[0].clean is False
        assert any(
            "block threshold" in msg for msg in results[0].blocking
        )

    def test_sha_mismatch_without_age_blocks(self, tmp_path: Path) -> None:
        # No generated_at means we cannot gauge staleness — block
        # rather than silently pass a mismatched doc.
        _write_regenerated(
            tmp_path, sha="9ccf714", generated_at=None
        )
        results = run_doctor(
            docs_root=tmp_path,
            head_sha="f542434",
            max_age_days=30.0,
            max_stale_age_days=7.0,
        )
        assert results[0].clean is False
        assert any(
            "no generated_at" in msg for msg in results[0].blocking
        )

    def test_dirty_annotation_stripped_before_compare(
        self, tmp_path: Path
    ) -> None:
        _write_regenerated(
            tmp_path, sha="f542434 (working tree dirty)"
        )
        results = run_doctor(
            docs_root=tmp_path, head_sha="f542434", max_age_days=30.0
        )
        assert results[0].clean is True
        assert results[0].declared_sha == "f542434"

    def test_missing_git_sha_blocks(self, tmp_path: Path) -> None:
        _write_regenerated(tmp_path, sha=None)
        results = run_doctor(
            docs_root=tmp_path, head_sha="f542434", max_age_days=30.0
        )
        assert results[0].clean is False
        assert any(
            "no parseable git_sha" in msg for msg in results[0].blocking
        )

    def test_age_over_threshold_warns_but_does_not_block(
        self, tmp_path: Path
    ) -> None:
        stale = (
            datetime.now(timezone.utc) - timedelta(days=45)
        ).isoformat()
        _write_regenerated(
            tmp_path, sha="f542434", generated_at=stale
        )
        results = run_doctor(
            docs_root=tmp_path, head_sha="f542434", max_age_days=30.0
        )
        assert results[0].clean is True
        assert any("d old" in msg for msg in results[0].advisory)

    def test_matching_sha_without_generated_at_still_clean(
        self, tmp_path: Path
    ) -> None:
        # When SHA matches HEAD, missing generated_at is only an
        # advisory (not blocking) — the doc is genuinely fresh.
        _write_regenerated(
            tmp_path, sha="f542434", generated_at=None
        )
        results = run_doctor(
            docs_root=tmp_path, head_sha="f542434", max_age_days=30.0
        )
        assert results[0].clean is True
        assert any(
            "generated_at" in msg for msg in results[0].advisory
        )

    def test_non_regenerated_docs_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "living.md").write_text(
            "---\nstatus: living\ngit_sha: 0000000\n---\n",
            encoding="utf-8",
        )
        (tmp_path / "narrative.md").write_text("# no frontmatter\n")
        results = run_doctor(
            docs_root=tmp_path, head_sha="f542434", max_age_days=30.0
        )
        assert results == []

    def test_missing_docs_root_returns_empty(self, tmp_path: Path) -> None:
        results = run_doctor(
            docs_root=tmp_path / "nope",
            head_sha="f542434",
            max_age_days=30.0,
        )
        assert results == []

    def test_multiple_mirrors_all_checked(self, tmp_path: Path) -> None:
        _write_regenerated(tmp_path, name="A.md", sha="f542434")
        # B is stale beyond the block window — should block.
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        _write_regenerated(
            tmp_path, name="B.md", sha="deadbee", generated_at=old
        )
        results = run_doctor(
            docs_root=tmp_path,
            head_sha="f542434",
            max_age_days=90.0,
            max_stale_age_days=7.0,
        )
        assert len(results) == 2
        by_name = {r.path.name: r for r in results}
        assert by_name["A.md"].clean is True
        assert by_name["B.md"].clean is False


class TestRuntimeMirrorCheckDataclass:
    def test_to_dict_shape(self, tmp_path: Path) -> None:
        _write_regenerated(tmp_path, sha="f542434")
        results = run_doctor(
            docs_root=tmp_path, head_sha="f542434", max_age_days=30.0
        )
        payload = results[0].to_dict()
        assert set(payload) == {
            "path",
            "declared_sha",
            "head_sha",
            "generated_at",
            "age_days",
            "blocking",
            "advisory",
        }
        assert payload["declared_sha"] == "f542434"
        assert payload["head_sha"] == "f542434"
