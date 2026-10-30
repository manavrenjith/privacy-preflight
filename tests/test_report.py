"""
Tests for Report Generator (scripts/report.py).
Validates report structure, label shapes, status computation,
date-flipping behavior, negative constraints, and CLI execution.
"""

from __future__ import annotations

import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.report import generate_report


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Creates a temporary isolated copy of the workspace files needed for validation and reporting."""
    ref_dir = tmp_path / "references" / "jurisdictions"
    ref_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(WORKSPACE_ROOT / "references" / "jurisdictions" / "india.md", ref_dir / "india.md")
    shutil.copy(WORKSPACE_ROOT / "references" / "check-schema.md", tmp_path / "references" / "check-schema.md")

    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(WORKSPACE_ROOT / "config" / "effective-dates.yaml", cfg_dir / "effective-dates.yaml")
    if (WORKSPACE_ROOT / "config" / "restricted-countries.yaml").exists():
        shutil.copy(WORKSPACE_ROOT / "config" / "restricted-countries.yaml", cfg_dir / "restricted-countries.yaml")

    res_dir = tmp_path / "research" / "india"
    res_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(WORKSPACE_ROOT / "research" / "india" / "verification-log.md", res_dir / "verification-log.md")
    shutil.copy(WORKSPACE_ROOT / "research" / "india" / "open-questions.md", res_dir / "open-questions.md")

    return tmp_path


def test_finding_headings_contain_required_labels():
    """Every finding heading must show all required labels in the specified shape."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    # Law heading pattern:
    # [LAW · <status> · verified <date> · <verified_against>, <verified_by>, human check pending]
    law_pattern = re.compile(
        r"^### \[LAW · (READINESS from \d{4}-\d{2}-\d{2}|IN FORCE NOW|UNRESOLVED \([^)]+\)) · verified \d{4}-\d{2}-\d{2} · [^\]]+\]$",
        re.MULTILINE,
    )
    # Best Practice heading pattern:
    # [BEST PRACTICE · not a legal requirement · verified <date>]
    bp_pattern = re.compile(
        r"^### \[BEST PRACTICE · not a legal requirement · verified \d{4}-\d{2}-\d{2}\]$",
        re.MULTILINE,
    )

    law_headings = law_pattern.findall(md_report)
    bp_headings = bp_pattern.findall(md_report)

    assert len(law_headings) >= 5
    assert len(bp_headings) >= 2

    # Check JSON records match
    for f in json_report["sections"]["in_force_now"] + json_report["sections"]["readiness"]:
        assert "LAW" in f["heading_label"]
        assert "verified" in f["heading_label"]


def test_today_2026_10_29_statuses():
    """With --today 2026-10-29: DPDP LAW checks are READINESS and IN-SPDI-001 is IN FORCE NOW."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    # IN-SPDI-001 must be IN FORCE NOW
    in_force_cids = [f["check_id"] for f in json_report["sections"]["in_force_now"]]
    assert "IN-SPDI-001" in in_force_cids

    # DPDP checks with found/not-found must be in readiness
    readiness_cids = [f["check_id"] for f in json_report["sections"]["readiness"]]
    assert "IN-DPDP-002" in readiness_cids
    assert "IN-DPDP-004" in readiness_cids
    assert "IN-DPDP-008" in readiness_cids

    # Check markdown text presence
    assert "[LAW · IN FORCE NOW · verified 2026-10-29 · official-text, ai-read, human check pending]" in md_report
    assert "[LAW · READINESS from 2027-05-13 · verified 2026-10-29 · official-text, ai-read, human check pending]" in md_report


def test_today_2027_05_13_status_flip():
    """With --today 2027-05-13: DPDP LAW checks flip to IN FORCE NOW and IN-SPDI-001 becomes UNRESOLVED (Q8, Q23)."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2027, 5, 13)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    # DPDP checks flip to IN FORCE NOW
    in_force_cids = [f["check_id"] for f in json_report["sections"]["in_force_now"]]
    assert "IN-DPDP-002" in in_force_cids
    assert "IN-DPDP-004" in in_force_cids
    assert "IN-DPDP-008" in in_force_cids

    # IN-SPDI-001 flips to UNRESOLVED
    unresolved_cids = [f["check_id"] for f in json_report["sections"]["unresolved"]]
    assert "IN-SPDI-001" in unresolved_cids

    # Check markdown heading text
    assert "[LAW · UNRESOLVED (Q8, Q23) · verified 2026-10-29 · official-text, ai-read, human check pending]" in md_report


def test_best_practice_never_gets_in_force_or_readiness_tag():
    """BEST PRACTICE entries must have 'not a legal requirement' and never an in-force or readiness tag."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    for test_date in (datetime.date(2026, 10, 29), datetime.date(2027, 5, 13)):
        md_report, json_report = generate_report(
            findings_path=findings_path,
            jurisdiction="india",
            today=test_date,
            base_dir=WORKSPACE_ROOT,
        )

        bp_findings = (
            json_report["sections"]["best_practice"]
            + json_report["sections"]["informational_inventory"]
        )
        for f in bp_findings:
            if f["label"] == "BEST PRACTICE":
                assert f["status"] == "not a legal requirement"
                assert "IN FORCE NOW" not in f["heading_label"]
                assert "READINESS" not in f["heading_label"]
                assert "[BEST PRACTICE · not a legal requirement" in f["heading_label"]


def test_proposed_check_appears_only_under_proposed_checks():
    """The proposed check appears only under 'Proposed checks (not active)' and never as a finding."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    # Must appear in Proposed Checks section
    proposed_cids = [c["check_id"] for c in json_report["proposed_checks"]]
    assert "IN-CERTIN-001" in proposed_cids
    assert "## Proposed Checks (Not Active)" in md_report
    assert "- **IN-CERTIN-001**" in md_report

    # Must NOT appear as a finding in any of the findings sections
    all_finding_cids = [
        f["check_id"]
        for section in json_report["sections"].values()
        for f in section
    ]
    assert "IN-CERTIN-001" not in all_finding_cids


def test_proposed_check_in_findings_fails(tmp_path: Path):
    """Attempting to evaluate a proposed check as a finding must fail with a clear error."""
    invalid_findings = tmp_path / "invalid_proposed.json"
    invalid_findings.write_text(
        json.dumps([
            {
                "check_id": "IN-CERTIN-001",
                "result": "found",
                "evidence": ["/etc/ntp.conf:1"],
            }
        ]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Proposed checks cannot be evaluated as findings"):
        generate_report(
            findings_path=invalid_findings,
            jurisdiction="india",
            today=datetime.date(2026, 10, 29),
            base_dir=WORKSPACE_ROOT,
        )


def test_unknown_check_id_fails_with_clear_error(tmp_path: Path):
    """A finding referencing an unknown check ID must fail with a clear error."""
    invalid_findings = tmp_path / "unknown_check.json"
    invalid_findings.write_text(
        json.dumps([
            {
                "check_id": "IN-DPDP-999",
                "result": "found",
                "evidence": ["some_file.py:1"],
            }
        ]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Finding references unknown check ID: 'IN-DPDP-999'"):
        generate_report(
            findings_path=invalid_findings,
            jurisdiction="india",
            today=datetime.date(2026, 10, 29),
            base_dir=WORKSPACE_ROOT,
        )


def test_active_check_with_no_finding_appears_in_not_run():
    """An active check with no finding supplied must appear under 'Not run'."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    not_run_cids = [c["check_id"] for c in json_report["not_run"]]
    assert "IN-DPDP-009" in not_run_cids
    assert "IN-DPDP-010" in not_run_cids
    assert "IN-DPDP-013" in not_run_cids
    assert "IN-BP-002" in not_run_cids
    assert "IN-BP-003" in not_run_cids

    assert "## Not Run" in md_report
    assert "- **IN-DPDP-009**:" in md_report


def test_stale_last_verified_produces_staleness_warning(temp_workspace: Path, tmp_path: Path):
    """A stale last_verified (> 90 days before today) produces the staleness warning section."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    mutated = content.replace("last_verified: 2026-10-29", "last_verified: 2026-01-01", 1)
    india_md.write_text(mutated, encoding="utf-8")

    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)

    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=temp_workspace,
    )

    assert "## Staleness Warning" in md_report
    assert "2026-01-01" in md_report
    assert json_report["staleness_warning"] is not None


def test_output_never_contains_compliant_or_secure():
    """Neither 'compliant' nor 'secure' appears anywhere in the markdown or JSON output (case-insensitive)."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    json_str = json.dumps(json_report)

    # Word boundary match
    assert re.search(r"\bcompliant\b", md_report, re.IGNORECASE) is None
    assert re.search(r"\bsecure\b", md_report, re.IGNORECASE) is None
    assert re.search(r"\bcompliant\b", json_str, re.IGNORECASE) is None
    assert re.search(r"\bsecure\b", json_str, re.IGNORECASE) is None

    # Substring match
    assert "compliant" not in md_report.lower()
    assert "secure" not in md_report.lower()
    assert "compliant" not in json_str.lower()
    assert "secure" not in json_str.lower()


def test_refuses_to_render_when_pack_fails_validation(temp_workspace: Path):
    """Refuses to render and prints validation failures when the jurisdiction pack fails validation."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    mutated = content.replace("label: LAW", "label: INVALID_LABEL", 1)
    india_md.write_text(mutated, encoding="utf-8")

    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    with pytest.raises(ValueError, match="Check pack validation failed; refusing to generate report."):
        generate_report(
            findings_path=findings_path,
            jurisdiction="india",
            today=datetime.date(2026, 10, 29),
            base_dir=temp_workspace,
        )


def test_cli_execution_markdown_and_json(tmp_path: Path):
    """Verify CLI flags --out and --json write valid report files."""
    out_md = tmp_path / "out_report.md"
    out_json = tmp_path / "out_report.json"
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/report.py",
            "--findings",
            str(findings_path),
            "--jurisdiction",
            "india",
            "--today",
            "2026-10-29",
            "--out",
            str(out_md),
            "--json",
            str(out_json),
        ],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert out_md.is_file() and out_md.stat().st_size > 0
    assert out_json.is_file() and out_json.stat().st_size > 0

    content_md = out_md.read_text(encoding="utf-8")
    assert "# Privacy Preflight Findings Report: India" in content_md
    assert "This report lists findings. It is not legal advice and it does not certify anything." in content_md

