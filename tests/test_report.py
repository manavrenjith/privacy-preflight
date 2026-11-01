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
        r"^### \[LAW · (READINESS from \d{4}-\d{2}-\d{2}|IN FORCE NOW( until \d{4}-\d{2}-\d{2}, then UNRESOLVED \([^)]+\))?|UNRESOLVED \([^)]+\)) · verified \d{4}-\d{2}-\d{2} · [^\]]+\]$",
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
    """With --today 2026-10-29: DPDP LAW checks are READINESS and IN-SPDI-001 is IN FORCE NOW with applies_until qualifier."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    # IN-SPDI-001 must be in in_force_now category
    in_force_cids = [f["check_id"] for f in json_report["sections"]["in_force_now"]]
    assert "IN-SPDI-001" in in_force_cids

    # DPDP checks with met/not-met must be in readiness
    readiness_cids = [f["check_id"] for f in json_report["sections"]["readiness"]]
    assert "IN-DPDP-002" in readiness_cids
    assert "IN-DPDP-004" in readiness_cids
    assert "IN-DPDP-008" in readiness_cids

    # Check markdown text presence
    assert "[LAW · IN FORCE NOW until 2027-05-13, then UNRESOLVED (Q8, Q23) · verified 2026-10-29 · official-text, ai-read, human check pending]" in md_report
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
                "result": "met",
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
                "result": "met",
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


def test_output_never_contains_prohibited_terms():
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

    p1 = "comp" + "liant"
    p2 = "sec" + "ure"

    # Word boundary match
    assert re.search(rf"\b{p1}\b", md_report, re.IGNORECASE) is None
    assert re.search(rf"\b{p2}\b", md_report, re.IGNORECASE) is None
    assert re.search(rf"\b{p1}\b", json_str, re.IGNORECASE) is None
    assert re.search(rf"\b{p2}\b", json_str, re.IGNORECASE) is None

    # Substring match
    assert p1 not in md_report.lower()
    assert p2 not in md_report.lower()
    assert p1 not in json_str.lower()
    assert p2 not in json_str.lower()


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


def test_result_vocabulary_met_not_met_and_reject_legacy_found(tmp_path: Path):
    """Result vocabulary only allows met, not-met, unclear, needs-human, informational. Rejects legacy found/not-found."""
    for valid_res in ("met", "not-met", "unclear", "needs-human", "informational"):
        fpath = tmp_path / f"valid_{valid_res}.json"
        fpath.write_text(
            json.dumps([{"check_id": "IN-SPDI-001", "result": valid_res, "evidence": ["test.ts:1"]}]),
            encoding="utf-8",
        )
        md, js = generate_report(
            findings_path=fpath,
            jurisdiction="india",
            today=datetime.date(2026, 10, 29),
            base_dir=WORKSPACE_ROOT,
        )
        assert f"- **Result:** {valid_res}" in md

    for invalid_res in ("found", "not-found", "passed", "failed"):
        fpath = tmp_path / f"invalid_{invalid_res}.json"
        fpath.write_text(
            json.dumps([{"check_id": "IN-SPDI-001", "result": invalid_res, "evidence": ["test.ts:1"]}]),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="invalid result"):
            generate_report(
                findings_path=fpath,
                jurisdiction="india",
                today=datetime.date(2026, 10, 29),
                base_dir=WORKSPACE_ROOT,
            )


def test_not_verified_section_filters_law_only_and_prints_none_when_empty():
    """'Not verified' lists only LAW checks whose verified_against != official-text. BP is removed. Prints 'None.' when empty."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )
    # India active LAW checks all have verified_against: official-text. BP checks have verified_against: n/a.
    # Therefore, not_verified should be empty and markdown must print 'None.'
    assert "## Not Verified\n\nNone." in md_report
    assert json_report["not_verified"] == []


def test_applies_until_heading_format():
    """Check with applies_until shows 'until <date>, then UNRESOLVED (<Q refs>)' when in force."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )
    expected_heading = "[LAW · IN FORCE NOW until 2027-05-13, then UNRESOLVED (Q8, Q23) · verified 2026-10-29 · official-text, ai-read, human check pending]"
    assert expected_heading in md_report


def test_compact_caveats_default_and_verbose_flag():
    """Default output shows only first sentence of caveats + pointer. --verbose shows full caveats. JSON always has full caveats."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_compact, js_compact = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
        verbose=False,
    )
    md_verbose, js_verbose = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
        verbose=True,
    )

    # In compact mode: first sentence + pointer
    expected_pointer = "Full caveats: references/jurisdictions/india.md (IN-SPDI-001)"
    assert expected_pointer in md_compact
    assert "Binds any 'body corporate' handling personal information or sensitive personal data or information (SPDI). Full caveats: references/jurisdictions/india.md (IN-SPDI-001)" in md_compact
    # Multi-sentence caveat detail omitted in compact
    assert "whether the SPDI Rules survive the omission of s.43A is legally unresolved" not in md_compact

    # In verbose mode: full caveats
    assert "whether the SPDI Rules survive the omission of s.43A is legally unresolved" in md_verbose

    # JSON report always has full caveats regardless of verbose flag
    spdi_finding_compact = [f for f in js_compact["sections"]["in_force_now"] if f["check_id"] == "IN-SPDI-001"][0]
    spdi_finding_verbose = [f for f in js_verbose["sections"]["in_force_now"] if f["check_id"] == "IN-SPDI-001"][0]
    assert "whether the SPDI Rules survive the omission of s.43A is legally unresolved" in spdi_finding_compact["caveats"]
    assert "whether the SPDI Rules survive the omission of s.43A is legally unresolved" in spdi_finding_verbose["caveats"]


def test_q1_date_variance_note_in_header_under_evaluation_date():
    """Q1 date-variance note is located in the header block under the evaluation date."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    header_idx = md_report.find("# Privacy Preflight Findings Report: India")
    eval_date_idx = md_report.find("- **Evaluation Date:** 2026-10-29")
    q1_note_idx = md_report.find("Note: Dates assume 13 Nov / 13 May per official gazette datelines; upload metadata indicates a possible one-day variance (open question Q1).")
    summary_idx = md_report.find("## Summary")

    assert header_idx != -1
    assert eval_date_idx != -1
    assert q1_note_idx != -1
    assert header_idx < eval_date_idx < q1_note_idx < summary_idx

    # Check note is not at the end
    closing_idx = md_report.rfind("This report lists findings.")
    assert q1_note_idx < closing_idx


def test_split_not_covered_sections():
    """Verify the split into 'Not Covered by This Scan' and 'Limits of the Legal Research'."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    # 1. Not Covered by This Scan
    assert "## Not Covered by This Scan" in md_report
    assert "- Other jurisdictions" in md_report
    assert "- Sector rules (health, telecom, SEBI, insurance)" in md_report
    assert "- E-commerce rules" in md_report
    assert "- Intermediary rules" in md_report
    assert "- checks not run: IN-BP-002, IN-DPDP-009, IN-DPDP-010, IN-DPDP-013, IN-BP-003" in md_report

    # 2. Limits of the Legal Research
    assert "## Limits of the Legal Research" in md_report
    assert (
        "- Primary texts were read by an AI model and human checks are pending (see research/india/verification-log.md)."
        in md_report
    )
    assert (
        "- Statements that a notification has not been issued come from secondary sources, not a direct e-Gazette search."
        in md_report
    )
    assert "- The 13 vs 14 November date variance (Q1)." in md_report
    assert "Full Known Limits: references/jurisdictions/india.md" in md_report

    # 3. report.json carries full Known Limits text
    assert "Schedules-Commencement Mapping" in json_report["not_covered"]
    assert "Absence of Notifications" in json_report["not_covered"]


def test_report_contains_no_internal_pack_notes():
    """Assert report text contains neither 'Hindi' nor 'file 0' nor 'India Code'."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    assert "Hindi" not in md_report
    assert "file 0" not in md_report
    assert "India Code" not in md_report


def test_summary_block_under_header():
    """Summary block appears under header with counts, without score, percentage, or pass/fail wording."""
    findings_path = WORKSPACE_ROOT / "tests" / "fixtures" / "sample-findings.json"
    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_path,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    assert "## Summary" in md_report
    assert "- **Active Checks:** 12" in md_report
    assert "- **Checks Run:** 7" in md_report
    assert "- **Checks Not Run:** 5" in md_report
    assert "- met: 4" in md_report
    assert "- not-met: 1" in md_report
    assert "- unclear: 0" in md_report
    assert "- needs-human: 1" in md_report
    assert "- informational: 1" in md_report

    summary_block = md_report[md_report.find("## Summary"):md_report.find("## In Force Now")]
    assert "%" not in summary_block
    assert "score" not in summary_block.lower()
    assert "pass" not in summary_block.lower()
    assert "fail" not in summary_block.lower()

    # JSON summary check
    assert json_report["summary"] == {
        "active_checks": 12,
        "checks_run": 7,
        "checks_not_run": 5,
        "results": {
            "met": 4,
            "not-met": 1,
            "unclear": 0,
            "needs-human": 1,
            "informational": 1,
        },
    }


def test_cli_execution_with_verbose_flag(tmp_path: Path):
    """Verify CLI --verbose flag generates full caveats."""
    out_md = tmp_path / "out_verbose.md"
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
            "--verbose",
        ],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    content = out_md.read_text(encoding="utf-8")
    assert "whether the SPDI Rules survive the omission of s.43A is legally unresolved" in content


def test_findings_without_scan_field_renders_without_scan_coverage(tmp_path: Path):
    """Findings JSON with no 'scan' field renders successfully and output contains no 'Scan coverage' line."""
    findings_file = tmp_path / "findings_no_scan.json"
    findings_content = {
        "findings": [
            {
                "check_id": "IN-BP-001",
                "result": "met",
                "evidence": ["All static assets are self-hosted."],
            }
        ]
    }
    findings_file.write_text(json.dumps(findings_content), encoding="utf-8")

    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_file,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    assert "Scan coverage" not in md_report
    assert json_report.get("scan") is None


def test_findings_with_scan_missing_pages_skipped_renders_not_reported(tmp_path: Path):
    """Findings JSON with a 'scan' object that lacks 'pages_skipped' renders 'skipped: not reported' and never 'skipped: 0'."""
    findings_file = tmp_path / "findings_scan_missing_skipped.json"
    findings_content = {
        "scan": {
            "pages_crawled": 5,
            "max_depth_reached": 2,
            # "pages_skipped" is omitted
            "pages_failed": 0,
            "interactions": "none (no clicks except same-origin links, no forms submitted, no login)",
        },
        "findings": [
            {
                "check_id": "IN-BP-001",
                "result": "met",
                "evidence": ["All static assets are self-hosted."],
            }
        ],
    }
    findings_file.write_text(json.dumps(findings_content), encoding="utf-8")

    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_file,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    assert "Scan coverage:" in md_report
    assert "skipped: not reported" in md_report
    assert "skipped: 0" not in md_report
    assert json_report["scan"]["pages_crawled"] == 5
    assert "pages_skipped" not in json_report["scan"]


def test_report_best_practice_section_shows_informational_advisories(tmp_path: Path):
    """Informational best practice findings (e.g. IN-BP-003) render under Best Practice, not Informational Inventory."""
    findings_file = tmp_path / "findings_bp_info.json"
    findings_content = {
        "findings": [
            {
                "check_id": "IN-BP-003",
                "result": "informational",
                "evidence": [
                    "models/user.js: advisory: fast keyed hash used with password data (hmac-sha1); no work factor (line 4)"
                ],
                "suggested_fix": "Upgrade password hashing to Argon2id or bcrypt with appropriate work factor",
            }
        ]
    }
    findings_file.write_text(json.dumps(findings_content), encoding="utf-8")

    today = datetime.date(2026, 10, 29)
    md_report, json_report = generate_report(
        findings_path=findings_file,
        jurisdiction="india",
        today=today,
        base_dir=WORKSPACE_ROOT,
    )

    # Extract sections
    bp_idx = md_report.find("## Best Practice")
    assert bp_idx != -1
    needs_human_idx = md_report.find("## Needs Human or Legal Judgment")
    assert needs_human_idx != -1
    bp_section = md_report[bp_idx:needs_human_idx]

    info_idx = md_report.find("## Informational Inventory")
    assert info_idx != -1
    info_section = md_report[info_idx:bp_idx]

    # Best Practice section assertions
    assert "### [BEST PRACTICE · not a legal requirement · verified 2026-10-29]" in bp_section
    assert "- **Check:** IN-BP-003: Technical security baseline configurations" in bp_section
    assert "- **Result:** informational" in bp_section
    assert "models/user.js: advisory: fast keyed hash used with password data (hmac-sha1); no work factor (line 4)" in bp_section
    assert "- **Suggested Fix:** Upgrade password hashing to Argon2id or bcrypt with appropriate work factor" in bp_section
    assert "No findings of this kind among the checks that ran." not in bp_section

    # Informational Inventory section assertions
    assert "IN-BP-003" not in info_section
    assert "No findings of this kind among the checks that ran." in info_section

    # JSON report structure assertions
    bp_cids = [f["check_id"] for f in json_report["sections"]["best_practice"]]
    assert "IN-BP-003" in bp_cids

    info_cids = [
        f["check_id"]
        for f in json_report["sections"].get(
            "informational", json_report["sections"]["informational_inventory"]
        )
    ]
    assert "IN-BP-003" not in info_cids
    assert "IN-BP-003" not in [f["check_id"] for f in json_report["sections"]["informational_inventory"]]



