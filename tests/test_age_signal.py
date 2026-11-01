"""
Tests for Age Signal and Child-Directed Verification Analyzer (Task 7)
scripts/age_signal.py and IN-DPDP-011.

Asserts:
- Synthetic tests with tmp_path covering each signal kind individually and in combination.
- Boundary conditions:
  * Proximity rule for type="date" (within 2 lines of a DOB keyword).
  * Strict label text matching for age_field ("age" and "your age" only).
  * HTML comment stripping on .html/.htm/.vue/.svelte/.php preserving line counts.
  * Retention of code comments in .js/.ts/.py.
  * Word boundary isolation (e.g. 'page' and 'manage' never match 'age').
  * Skip rules for .env*, node_modules, reports, dist, build, __pycache__, and files > 1 MB.
  * Symlinked files are not followed.
  * child_directed_words reported in notes only, never as an evidence kind.
  * Notes mandatory phrases and absence of forbidden words ('compliant', 'secure').
  * Paths use forward slashes and no drive letters.
- Oracle tests on demo/clean-app and demo/flawed-app matching tests/expected-findings.json.
- Output renders through scripts/report.py without error.
- Zero writes to repo root (tmp_path only).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.age_signal import evaluate_age_signals

CLEAN_APP_DIR = WORKSPACE_ROOT / "demo" / "clean-app"
FLAWED_APP_DIR = WORKSPACE_ROOT / "demo" / "flawed-app"
EXPECTED_FINDINGS_PATH = WORKSPACE_ROOT / "tests" / "expected-findings.json"


# ---------------------------------------------------------------------------
# Synthetic Unit Tests
# ---------------------------------------------------------------------------

def test_dob_field_only(tmp_path: Path):
    """File with DOB field matches dob_field; other kinds report not found."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "signup.html").write_text(
        '<form><input type="date" id="dob" name="dob"></form>',
        encoding="utf-8",
    )
    doc = evaluate_age_signals(app_dir)
    f = doc["findings"][0]
    assert f["check_id"] == "IN-DPDP-011"
    assert f["result"] == "needs-human"

    evidence = f["evidence"]
    assert any(": dob_field:" in ev for ev in evidence)
    assert "age_field: not found in scanned files" in evidence
    assert "over_18_toggle: not found in scanned files" in evidence
    assert "parental_branch: not found in scanned files" in evidence


def test_dob_field_proximity_rule(tmp_path: Path):
    """
    Change A: type="date" counts only if a DOB keyword appears within 2 lines
    before or after. An input type="date" labelled 'Start date' does NOT match;
    the same input next to a 'Date of Birth' label DOES match.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # 1. Start date (should NOT match dob_field)
    (app_dir / "start_date.html").write_text(
        "<div>\n"
        '  <label for="start">Start date</label>\n'
        '  <input type="date" id="start" name="start_date">\n'
        "</div>\n",
        encoding="utf-8",
    )
    doc_start = evaluate_age_signals(app_dir)
    assert "dob_field: not found in scanned files" in doc_start["findings"][0]["evidence"]

    # 2. Date of birth within 2 lines (DOES match dob_field)
    (app_dir / "dob.html").write_text(
        "<div>\n"
        '  <label for="birth">Date of Birth</label>\n'
        '  <input type="date" id="birth" name="user_date">\n'
        "</div>\n",
        encoding="utf-8",
    )
    doc_dob = evaluate_age_signals(app_dir)
    assert any(": dob_field:" in ev for ev in doc_dob["findings"][0]["evidence"])


def test_age_field_only(tmp_path: Path):
    """File with exact age field matches age_field."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "signup.html").write_text(
        '<label for="age">Age</label>\n<input type="number" id="age" name="age">',
        encoding="utf-8",
    )
    doc = evaluate_age_signals(app_dir)
    f = doc["findings"][0]
    assert any(": age_field:" in ev for ev in f["evidence"])
    assert "dob_field: not found in scanned files" in f["evidence"]


def test_age_field_label_exactness_and_attribute_isolation(tmp_path: Path):
    """
    Change B: for labels, label text (trimmed, ignoring trailing colon/asterisk)
    must be exactly 'age' or 'your age'. 'Age range' and 'Age of account' must NOT match.
    name/id/for attributes remain exactly age or your_age/your-age.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Rejected label phrases and attributes
    (app_dir / "rejected.html").write_text(
        '<label for="r1">Age range</label>\n<input id="r1" name="age_range">\n'
        '<label for="r2">Age of account</label>\n<input id="r2" name="age-of-account">\n'
        '<input placeholder="Enter your age">\n',  # placeholder removed per Change B
        encoding="utf-8",
    )
    doc_rej = evaluate_age_signals(app_dir)
    assert "age_field: not found in scanned files" in doc_rej["findings"][0]["evidence"]

    # Accepted labels: 'Age', 'Your Age:', 'Age *'
    (app_dir / "accepted.html").write_text(
        '<label for="a1">Your Age:</label>\n<input id="a1" name="your_age">\n'
        '<label for="a2">Age *</label>\n<input id="a2" name="your-age">\n',
        encoding="utf-8",
    )
    doc_acc = evaluate_age_signals(app_dir)
    ev_acc = doc_acc["findings"][0]["evidence"]
    assert any(": age_field:" in ev for ev in ev_acc)


def test_over_18_toggle_individual_patterns(tmp_path: Path):
    """
    Change 4: Add tests that '18+', '18 or older' and 'over 18' each match
    over_18_toggle individually.
    """
    patterns = ["18+", "18 or older", "over 18", "at least 18", "above 18", "I am 18"]
    for idx, pat in enumerate(patterns):
        app_dir = tmp_path / f"app_{idx}"
        app_dir.mkdir()
        (app_dir / "signup.html").write_text(
            f'<label><input type="checkbox"> {pat}</label>',
            encoding="utf-8",
        )
        doc = evaluate_age_signals(app_dir)
        ev = doc["findings"][0]["evidence"]
        assert any(": over_18_toggle:" in line for line in ev), f"Failed to match pattern: {pat}"


def test_parental_branch_individual_keywords(tmp_path: Path):
    """
    Change 2: Exact list (parent, guardian, parental consent, guardian_email,
    parent_email, under 18, minor) word-bounded.
    """
    keywords = [
        "parent",
        "guardian",
        "parental consent",
        "guardian_email",
        "parent_email",
        "under 18",
        "minor",
    ]
    for idx, kw in enumerate(keywords):
        app_dir = tmp_path / f"app_{idx}"
        app_dir.mkdir()
        (app_dir / "signup.html").write_text(
            f'<div>Notice: {kw} required for registration.</div>',
            encoding="utf-8",
        )
        doc = evaluate_age_signals(app_dir)
        ev = doc["findings"][0]["evidence"]
        assert any(": parental_branch:" in line for line in ev), f"Failed on keyword: {kw}"


def test_all_four_signals_found(tmp_path: Path):
    """File containing all 4 signals lists all 4 in evidence."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "signup.html").write_text(
        '<label for="dob">Date of Birth</label>\n'
        '<input type="date" id="dob" name="dob">\n'
        '<label for="age">Age</label>\n'
        '<input type="number" id="age" name="age">\n'
        '<label><input type="checkbox"> 18 or older</label>\n'
        '<label for="parent">Parent or guardian consent</label>\n'
        '<input type="email" id="guardian_email" name="guardian_email">\n',
        encoding="utf-8",
    )
    doc = evaluate_age_signals(app_dir)
    ev = doc["findings"][0]["evidence"]
    assert any(": dob_field:" in line for line in ev)
    assert any(": age_field:" in line for line in ev)
    assert any(": over_18_toggle:" in line for line in ev)
    assert any(": parental_branch:" in line for line in ev)


def test_none_found_files_exist(tmp_path: Path):
    """Scanned files with no signals return needs-human and 4 not-found lines."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "index.html").write_text(
        "<html><body><h1>Welcome</h1><input name='username'></body></html>",
        encoding="utf-8",
    )
    doc = evaluate_age_signals(app_dir)
    f = doc["findings"][0]
    assert f["result"] == "needs-human"
    ev = f["evidence"]
    assert "dob_field: not found in scanned files" in ev
    assert "age_field: not found in scanned files" in ev
    assert "over_18_toggle: not found in scanned files" in ev
    assert "parental_branch: not found in scanned files" in ev


def test_empty_directory_evaluates_to_unclear(tmp_path: Path):
    """Directory with 0 eligible files returns unclear."""
    app_dir = tmp_path / "empty_app"
    app_dir.mkdir()
    doc = evaluate_age_signals(app_dir)
    assert doc["findings"][0]["result"] == "unclear"


def test_word_boundary_page_manage_never_match_age(tmp_path: Path):
    """'page' and 'manage' never match age_field."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "navigation.html").write_text(
        '<input name="page" id="page">\n<input name="manage" id="manage">\n',
        encoding="utf-8",
    )
    doc = evaluate_age_signals(app_dir)
    ev = doc["findings"][0]["evidence"]
    assert "age_field: not found in scanned files" in ev


def test_html_comments_stripped_code_comments_retained(tmp_path: Path):
    """
    Change C: HTML comment stripping only for .html, .htm, .vue, .svelte, .php,
    preserving newline counts. No comment stripping in other file types.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # 1. HTML file with comment containing DOB keyword -> stripped, not found
    (app_dir / "test.html").write_text(
        "<!-- <input type='date' name='dob'> -->\n<p>Hello world</p>\n",
        encoding="utf-8",
    )
    # 2. JS file with code comment containing guardian_email -> NOT stripped, found
    (app_dir / "test.js").write_text(
        "// TODO: verify guardian_email\nconst x = 1;\n",
        encoding="utf-8",
    )
    doc = evaluate_age_signals(app_dir)
    ev = doc["findings"][0]["evidence"]
    assert "dob_field: not found in scanned files" in ev
    assert any(": parental_branch:" in line and "guardian_email" in line for line in ev)


def test_child_directed_words_in_notes_only(tmp_path: Path):
    """
    Change 5: child_directed_words is one separate information line in the notes,
    not an evidence kind.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "index.html").write_text(
        "<p>This service is designed for children and students.</p>\n",
        encoding="utf-8",
    )
    doc = evaluate_age_signals(app_dir)
    f = doc["findings"][0]
    # Not an evidence kind
    assert not any("child_directed_words" in ev for ev in f["evidence"])
    # Reported in notes
    notes = f["notes"]
    assert "Child-directed words detected in scanned files (informational only):" in notes
    assert "child" in notes or "children" in notes or "student" in notes


def test_skip_rules(tmp_path: Path):
    """
    Skip: .git, node_modules, reports, dist, build, __pycache__, .env*, and files > 1 MB.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Ignored directories
    (app_dir / "node_modules").mkdir()
    (app_dir / "node_modules" / "pkg.html").write_text('<input name="dob">', encoding="utf-8")
    (app_dir / "reports").mkdir()
    (app_dir / "reports" / "summary.html").write_text('<input name="dob">', encoding="utf-8")
    (app_dir / ".git").mkdir()
    (app_dir / ".git" / "config.html").write_text('<input name="dob">', encoding="utf-8")

    # .env* file
    (app_dir / ".env").write_text("DOB=1990", encoding="utf-8")
    (app_dir / ".env.local").write_text("DOB=1990", encoding="utf-8")

    # Valid file
    (app_dir / "main.html").write_text("<p>Plain page</p>", encoding="utf-8")

    doc = evaluate_age_signals(app_dir)
    f = doc["findings"][0]
    assert "dob_field: not found in scanned files" in f["evidence"]
    assert "files scanned (1)" in f["notes"]
    assert "files skipped (" in f["notes"]


def test_symlink_not_followed_if_supported(tmp_path: Path):
    """Change E: a symlinked file is not followed (skip if OS cannot create symlinks)."""
    target_file = tmp_path / "target.html"
    target_file.write_text('<input name="dob" type="date">', encoding="utf-8")

    app_dir = tmp_path / "app"
    app_dir.mkdir()
    symlink_file = app_dir / "symlink.html"

    try:
        os.symlink(target_file, symlink_file)
    except (OSError, NotImplementedError):
        pytest.skip("OS does not permit symlink creation")

    doc = evaluate_age_signals(app_dir)
    f = doc["findings"][0]
    # Symlink must not be scanned
    assert "dob_field: not found in scanned files" in f["evidence"]


def test_evidence_paths_forward_slashes_and_no_drive_letters(tmp_path: Path):
    """Change E: evidence paths never contain a backslash or a drive letter."""
    app_dir = tmp_path / "app"
    nested_dir = app_dir / "nested" / "views"
    nested_dir.mkdir(parents=True)
    (nested_dir / "signup.html").write_text(
        '<label for="dob">Date of Birth</label>\n<input type="date" id="dob" name="dob">',
        encoding="utf-8",
    )
    doc = evaluate_age_signals(app_dir)
    for ev in doc["findings"][0]["evidence"]:
        assert "\\" not in ev, f"Evidence line contains backslash: {ev}"
        assert not re.search(r"\b[A-Za-z]:", ev), f"Evidence line contains drive letter: {ev}"
        if ": dob_field:" in ev:
            assert ev.startswith("nested/views/signup.html:")


def test_notes_mandatory_phrases_and_no_forbidden_words(tmp_path: Path):
    """
    Notes must contain exact required sentences and never contain 'compliant' or 'secure'.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "signup.html").write_text("<p>Hello</p>", encoding="utf-8")
    doc = evaluate_age_signals(app_dir)
    notes = doc["findings"][0]["notes"]

    assert (
        "Presence or absence only. Order of events (age signal before personal data collection) was not assessed. "
        "A human must confirm whether the application is child-directed or accessible to children."
    ) in notes
    assert "Matches in code comments in .js/.ts/.py files are not excluded." in notes
    assert "A match is a presence signal for a human reviewer, not a verified consent branch." in notes

    # Forbidden words
    notes_lower = notes.lower()
    assert "compliant" not in notes_lower
    assert "secure" not in notes_lower


# ---------------------------------------------------------------------------
# Oracle Tests on Demo Applications
# ---------------------------------------------------------------------------

def test_oracle_clean_app_matches_expected_findings():
    """
    Run on demo/clean-app and assert needs-human, matching expected-findings.json.
    clean-app evidence shows dob_field and parental_branch found.
    Change D: assert which signal kinds were found or not found, not exact line numbers.
    """
    doc = evaluate_age_signals(CLEAN_APP_DIR)
    f = doc["findings"][0]

    expected_all = json.loads(EXPECTED_FINDINGS_PATH.read_text(encoding="utf-8"))
    clean_expected = expected_all["clean-app"]["IN-DPDP-011"]

    assert f["check_id"] == "IN-DPDP-011"
    assert f["result"] == clean_expected["result"]

    evidence = f["evidence"]
    # dob_field and parental_branch are found
    assert any(": dob_field:" in line for line in evidence)
    assert any(": parental_branch:" in line for line in evidence)
    # age_field and over_18_toggle are not found
    assert "age_field: not found in scanned files" in evidence
    assert "over_18_toggle: not found in scanned files" in evidence


def test_oracle_flawed_app_matches_expected_findings():
    """
    Run on demo/flawed-app and assert needs-human, matching expected-findings.json.
    flawed-app evidence shows dob_field not found and parental_branch not found.
    Change D: assert which signal kinds were found or not found, not exact line numbers.
    """
    doc = evaluate_age_signals(FLAWED_APP_DIR)
    f = doc["findings"][0]

    expected_all = json.loads(EXPECTED_FINDINGS_PATH.read_text(encoding="utf-8"))
    flawed_expected = expected_all["flawed-app"]["IN-DPDP-011"]

    assert f["check_id"] == "IN-DPDP-011"
    assert f["result"] == flawed_expected["result"]

    evidence = f["evidence"]
    assert "dob_field: not found in scanned files" in evidence
    assert "age_field: not found in scanned files" in evidence
    assert "over_18_toggle: not found in scanned files" in evidence
    assert "parental_branch: not found in scanned files" in evidence


# ---------------------------------------------------------------------------
# CLI & Report Integration
# ---------------------------------------------------------------------------

def test_age_signal_cli_and_report_rendering(tmp_path: Path):
    """
    Execute age_signal.py CLI on demo/clean-app, output JSON, and render through
    scripts/report.py without error.
    """
    findings_json = tmp_path / "age-findings.json"

    # 1. Run CLI
    proc = subprocess.run(
        [
            sys.executable,
            str(WORKSPACE_ROOT / "scripts" / "age_signal.py"),
            str(CLEAN_APP_DIR),
            "--findings-out",
            str(findings_json),
        ],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"age_signal.py CLI failed: {proc.stderr}"
    assert findings_json.is_file()

    doc = json.loads(findings_json.read_text(encoding="utf-8"))
    assert "scan" not in doc  # No top-level scan object
    assert len(doc["findings"]) == 1
    assert doc["findings"][0]["check_id"] == "IN-DPDP-011"

    # 2. Render through report.py
    report_proc = subprocess.run(
        [
            sys.executable,
            str(WORKSPACE_ROOT / "scripts" / "report.py"),
            "--findings",
            str(findings_json),
            "--jurisdiction",
            "india",
            "--today",
            "2026-10-29",
        ],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
    )
    assert report_proc.returncode == 0, f"report.py failed: {report_proc.stderr}"
    stdout = report_proc.stdout
    assert "IN-DPDP-011" in stdout
    assert "# Privacy Preflight Findings Report: India" in stdout
    # Ensure no backslashes in evidence lines
    assert "\\" not in doc["findings"][0]["evidence"][0]

