"""
Tests for Age Signal and Child-Directed Verification Analyzer (Task 7 & 10)
scripts/age_signal.py and IN-DPDP-011.

Asserts:
- Synthetic tests with tmp_path covering each signal kind individually and in combination.
- Boundary conditions:
  * Proximity rule for type="date" (within 2 lines of a DOB keyword).
  * Strict label text matching for age_field ("age" and "your age" only).
  * HTML comment stripping on .html/.htm/.vue/.svelte/.php preserving line counts.
  * Retention of code comments in .js/.ts/.py.
  * Word boundary isolation (e.g. 'page', 'manage', 'package', 'storage' never match 'age').
  * Skip rules for .env*, node_modules, reports, dist, build, __pycache__, and files > 1 MB.
  * Symlinked files are not followed.
  * child_directed_words reported in notes only, never as an evidence kind.
  * Preferred file stem matching (signup, onboard, onboarding, register, registration, auth, checkout; author must NOT match).
  * Preferred files prioritized when choosing 3 evidence lines per kind.
  * Notes list number of files with at least one match per kind and relative paths (max 5 per kind).
  * Paths use forward slashes and no drive letters.
  * Notes mandatory phrases and absence of forbidden words ('compliant', 'secure').
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

from scripts.age_signal import evaluate_age_signals, is_preferred_file

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


def test_age_field_label_strict_matching(tmp_path: Path):
    """
    Change B: for labels, label text (trimmed, case-insensitive, ignoring trailing :/*)
    must be exactly 'age' or 'your age'. 'Message', 'Language', 'Coverage' do NOT match.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Should NOT match: labels with words containing 'age'
    (app_dir / "false_positives.html").write_text(
        "<label>Message</label>\n"
        "<label>Language</label>\n"
        "<label>Coverage</label>\n"
        "<label>Page Number</label>\n"
        "<label>Manage account</label>\n",
        encoding="utf-8",
    )
    doc_fp = evaluate_age_signals(app_dir)
    assert "age_field: not found in scanned files" in doc_fp["findings"][0]["evidence"]

    # DOES match: exact 'Age' and 'Your Age:'
    (app_dir / "true_positives.html").write_text(
        "<label>Age:</label>\n"
        "<label>Your Age *</label>\n",
        encoding="utf-8",
    )
    doc_tp = evaluate_age_signals(app_dir)
    assert any(": age_field:" in ev for ev in doc_tp["findings"][0]["evidence"])


def test_word_boundary_page_manage_package_storage_never_match_age(tmp_path: Path):
    """'page', 'manage', 'package', 'storage' never match age_field."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "navigation.html").write_text(
        '<input name="page" id="page">\n'
        '<input name="manage" id="manage">\n'
        '<input name="package" id="package">\n'
        '<input name="storage" id="storage">\n',
        encoding="utf-8",
    )
    doc = evaluate_age_signals(app_dir)
    ev = doc["findings"][0]["evidence"]
    assert "age_field: not found in scanned files" in ev


def test_over_18_toggle_individual_variations(tmp_path: Path):
    """
    Change 4: '18+', '18 or older', and 'over 18' each match individually.
    """
    for phrase in ["18+", "18 or older", "over 18"]:
        app_dir = tmp_path / f"app_{phrase.replace(' ', '_').replace('+', '_plus')}"
        app_dir.mkdir()
        (app_dir / "terms.html").write_text(
            f'<input type="checkbox"> I confirm I am {phrase}.\n',
            encoding="utf-8",
        )
        doc = evaluate_age_signals(app_dir)
        ev = doc["findings"][0]["evidence"]
        assert any(": over_18_toggle:" in line for line in ev), f"Failed to match phrase: {phrase}"


def test_parental_branch_exact_list(tmp_path: Path):
    """
    Change 2: matches exact parental branch keywords:
    parent, guardian, parental consent, guardian_email, parent_email, under 18, minor.
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
    for kw in keywords:
        app_dir = tmp_path / f"app_{kw.replace(' ', '_')}"
        app_dir.mkdir()
        (app_dir / "consent.html").write_text(
            f"<div>Please provide {kw} before registering.</div>\n",
            encoding="utf-8",
        )
        doc = evaluate_age_signals(app_dir)
        ev = doc["findings"][0]["evidence"]
        assert any(": parental_branch:" in line for line in ev), f"Failed for keyword: {kw}"


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


def test_html_comment_stripping_only_html_extensions(tmp_path: Path):
    """
    Change 1: HTML comments (<!-- -->) are stripped only from HTML-like extensions
    (.html, .htm, .vue, .svelte, .php), preserving line count.
    Code comments (//, /* */, #) in .js/.ts/.py are NOT stripped.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # 1. HTML file with match in comment -> stripped (NOT flagged)
    (app_dir / "comment.html").write_text(
        "<!-- <label>Age</label> -->\n"
        "<p>Welcome</p>\n",
        encoding="utf-8",
    )
    doc_html = evaluate_age_signals(app_dir)
    assert "age_field: not found in scanned files" in doc_html["findings"][0]["evidence"]

    # 2. JS file with match in code comment -> preserved (FLAGGED)
    (app_dir / "script.js").write_text(
        "// Check if user is over 18\n"
        "function verify() { return true; }\n",
        encoding="utf-8",
    )
    doc_js = evaluate_age_signals(app_dir)
    assert any(": over_18_toggle:" in line for line in doc_js["findings"][0]["evidence"])


def test_child_directed_words_in_notes_only(tmp_path: Path):
    """
    Change 5: child_directed_words is one separate information line in notes,
    never an evidence kind.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "kids.html").write_text(
        "<h1>App for kids and students</h1>\n",
        encoding="utf-8",
    )
    doc = evaluate_age_signals(app_dir)
    f = doc["findings"][0]

    # Must NOT be in evidence
    assert not any("child_directed" in line for line in f["evidence"])
    # Must be in notes
    assert "Child-directed words detected in scanned files (informational only): kids, students." in f["notes"]


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
    (app_dir / "dist").mkdir()
    (app_dir / "dist" / "dist.html").write_text('<input name="dob">', encoding="utf-8")
    (app_dir / "build").mkdir()
    (app_dir / "build" / "build.html").write_text('<input name="dob">', encoding="utf-8")
    (app_dir / "__pycache__").mkdir()
    (app_dir / "__pycache__" / "cache.html").write_text('<input name="dob">', encoding="utf-8")

    # .env* file
    (app_dir / ".env").write_text("DOB=1990", encoding="utf-8")
    (app_dir / ".env.local").write_text("DOB=1990", encoding="utf-8")

    # Large file (> 1 MB)
    large_file = app_dir / "large.html"
    large_file.write_text("x" * (1024 * 1024 + 100), encoding="utf-8")

    # Valid file
    (app_dir / "main.html").write_text("<p>Plain page</p>", encoding="utf-8")

    doc = evaluate_age_signals(app_dir)
    f = doc["findings"][0]
    assert "dob_field: not found in scanned files" in f["evidence"]
    assert "files scanned (1)" in f["notes"]
    assert "files skipped (" in f["notes"]


def test_symlink_not_followed_if_supported(tmp_path: Path):
    """A symlinked file is not followed (skip if OS cannot create symlinks)."""
    target_file = tmp_path / "target.html"
    target_file.write_text('<label for="dob">Date of Birth</label>\n<input name="dob" id="dob" type="date">', encoding="utf-8")

    app_dir = tmp_path / "app"
    app_dir.mkdir()
    symlink_file = app_dir / "symlink.html"

    try:
        os.symlink(target_file, symlink_file)
    except (OSError, NotImplementedError):
        pytest.skip("OS does not permit symlink creation")

    doc = evaluate_age_signals(app_dir)
    f = doc["findings"][0]
    assert "dob_field: not found in scanned files" in f["evidence"]


def test_evidence_paths_forward_slashes_and_no_drive_letters(tmp_path: Path):
    """Evidence paths never contain a backslash or a drive letter."""
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
        assert not re.search(r"^[A-Za-z]:", ev), f"Evidence line contains drive letter: {ev}"
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


def test_preferred_file_stem_matching():
    """
    Task 10 Change 5:
    Split file stem on non-letters and match whole parts:
    signup, onboard, onboarding, register, registration, auth, checkout.
    'author' must NOT match.
    """
    assert is_preferred_file("signup.html")
    assert is_preferred_file("user-signup.html")
    assert is_preferred_file("onboard.html")
    assert is_preferred_file("user_onboard.js")
    assert is_preferred_file("onboarding-flow.vue")
    assert is_preferred_file("register.html")
    assert is_preferred_file("user_register.php")
    assert is_preferred_file("registration.py")
    assert is_preferred_file("registration_form.svelte")
    assert is_preferred_file("auth.js")
    assert is_preferred_file("auth-service.ts")
    assert is_preferred_file("checkout.html")
    assert is_preferred_file("cart_checkout.html")

    # Counterexamples: author, authority, about, authentic must NOT match
    assert not is_preferred_file("author.html")
    assert not is_preferred_file("author_bio.html")
    assert not is_preferred_file("authority.js")
    assert not is_preferred_file("about.html")
    assert not is_preferred_file("authentic_data.json")


def test_preferred_files_evidence_selection_order(tmp_path: Path):
    """
    Task 10 Change 2d:
    When choosing which 3 evidence lines to show per kind, prefer files whose name
    contains signup, onboard, register, auth, checkout; otherwise walk order.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Create non-preferred file with matches (comes first alphabetically: "a_about.html")
    (app_dir / "a_about.html").write_text(
        "<div>minor consent needed line 1</div>\n"
        "<div>minor consent needed line 2</div>\n"
        "<div>minor consent needed line 3</div>\n",
        encoding="utf-8",
    )

    # Create preferred file with a match (comes later: "z_signup.html")
    (app_dir / "z_signup.html").write_text(
        "<div>minor consent needed in signup</div>\n",
        encoding="utf-8",
    )

    doc = evaluate_age_signals(app_dir)
    ev_lines = doc["findings"][0]["evidence"]
    parental_lines = [line for line in ev_lines if ": parental_branch:" in line]

    assert len(parental_lines) == 3
    # Preferred file z_signup.html must appear in the 3 evidence lines
    assert any("z_signup.html" in line for line in parental_lines)


def test_notes_file_summary_and_capping(tmp_path: Path):
    """
    Task 10 Change 2d:
    Notes must list the number of files with at least one match per kind and
    their relative paths (max 5 per kind).
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Create 7 distinct files with parental_branch matches
    for i in range(7):
        (app_dir / f"page_{i}.html").write_text(
            f"<div>Contact parent for approval {i}</div>\n",
            encoding="utf-8",
        )

    doc = evaluate_age_signals(app_dir)
    notes = doc["findings"][0]["notes"]

    assert "Files with matches per kind:" in notes
    # 7 files matched, capped at 5 with (and 2 more)
    assert "parental_branch: 7 files with matches" in notes
    assert "(and 2 more)" in notes


# ---------------------------------------------------------------------------
# Oracle Tests on Demo Applications
# ---------------------------------------------------------------------------

def test_oracle_clean_app_matches_expected_findings():
    """
    Run on demo/clean-app and assert needs-human, matching expected-findings.json.
    clean-app evidence shows dob_field found and parental_branch found.
    """
    doc = evaluate_age_signals(CLEAN_APP_DIR)
    f = doc["findings"][0]

    expected_all = json.loads(EXPECTED_FINDINGS_PATH.read_text(encoding="utf-8"))
    clean_expected = expected_all["clean-app"]["IN-DPDP-011"]

    assert f["check_id"] == "IN-DPDP-011"
    assert f["result"] == clean_expected["result"]

    evidence = f["evidence"]
    assert any(": dob_field:" in line for line in evidence)
    assert any(": parental_branch:" in line for line in evidence)
    assert "age_field: not found in scanned files" in evidence
    assert "over_18_toggle: not found in scanned files" in evidence

    # Verify notes file summary
    assert "Files with matches per kind:" in f["notes"]
    assert "signup.html" in f["notes"]


def test_oracle_flawed_app_matches_expected_findings():
    """
    Run on demo/flawed-app and assert needs-human, matching expected-findings.json.
    flawed-app evidence shows dob_field not found and parental_branch not found.
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
    assert "\\" not in doc["findings"][0]["evidence"][0]
