"""
Tests for Privacy Preflight Merge Script (Task 9)
scripts/preflight.py and end-to-end analyzer orchestration.

Asserts:
1. Run without --url on demo/clean-app and demo/flawed-app:
   - Exactly 3 findings: IN-DPDP-011, IN-DPDP-013, IN-BP-003.
   - Top-level 'scan' object is omitted.
   - Report renders and lists the 9 other active checks under Not Run.
2. Run with --url on local servers:
   - Exactly 12 findings, one per active check.
   - Top-level 'scan' object is present (from crawl.py only).
   - Report renders with 0 Not Run entries.
   - Skips gracefully if Playwright/Chromium is missing.
3. Duplicate check_id raises an error naming both scanners.
4. Custom --out writes exclusively to the specified path without touching repo root.
5. No absolute paths or Windows drive letters in findings JSON output.
6. Error handling for unreachable URL / unused local port:
   - Prints one line 'crawl failed: <exception type>; crawl and pages checks not run'.
   - Still writes static findings.
   - Marks crawl and pages as not run in summary.
   - Exits with code 1.
   - Never prints traceback or evidence.
7. Validation for --url (only http:// and https://) and <app-directory> existence.
8. Terminal output without --report contains only summary lines (zero evidence lines).
9. Terminal output with --report and no --url renders markdown report with 9 Not Run checks.
"""

from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.preflight import main as preflight_main, run_preflight

CLEAN_APP_DIR = WORKSPACE_ROOT / "demo" / "clean-app"
FLAWED_APP_DIR = WORKSPACE_ROOT / "demo" / "flawed-app"


def get_free_port() -> int:
    """Find and return an available TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def wait_for_server(url: str, timeout: float = 5.0) -> None:
    """Poll URL until server responds with 200 OK or timeout expires."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/index.html", timeout=1) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"Server at {url} failed to start within {timeout} seconds")


def is_playwright_available() -> bool:
    """Check if Playwright and Chromium browser can be launched."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def clean_app_server() -> Generator[str, None, None]:
    """Start local HTTP server for demo/clean-app."""
    port = get_free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--directory", str(CLEAN_APP_DIR)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        wait_for_server(url)
        yield url
    finally:
        proc.terminate()
        proc.wait()


@pytest.fixture(scope="module")
def flawed_app_server() -> Generator[str, None, None]:
    """Start local HTTP server for demo/flawed-app."""
    port = get_free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--directory", str(FLAWED_APP_DIR)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        wait_for_server(url)
        yield url
    finally:
        proc.terminate()
        proc.wait()


# ---------------------------------------------------------------------------
# 1. Runs without --url (Static only: 3 findings, no scan object)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("app_path,app_label", [(CLEAN_APP_DIR, "clean"), (FLAWED_APP_DIR, "flawed")])
def test_preflight_without_url(tmp_path: Path, app_path: Path, app_label: str):
    """
    Without --url:
    - Exactly 3 findings (IN-DPDP-011, IN-DPDP-013, IN-BP-003).
    - No 'scan' object.
    - Report renders successfully and lists the other 9 checks under Not Run.
    """
    out_file = tmp_path / f"findings_{app_label}.json"
    exit_code, doc = run_preflight(
        app_dir=app_path,
        url=None,
        out_path=out_file,
        report=False,
    )
    assert exit_code == 0
    assert out_file.is_file()

    # Assert no scan object
    assert "scan" not in doc

    # Assert exactly 3 findings
    findings = doc["findings"]
    assert len(findings) == 3
    check_ids = {f["check_id"] for f in findings}
    assert check_ids == {"IN-DPDP-011", "IN-DPDP-013", "IN-BP-003"}

    # Render report via report.py subprocess to verify Not Run section
    proc = subprocess.run(
        [
            sys.executable,
            str(WORKSPACE_ROOT / "scripts" / "report.py"),
            "--findings",
            str(out_file),
            "--jurisdiction",
            "india",
            "--today",
            "2026-10-29",
        ],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"report.py failed: {proc.stderr}"
    report_output = proc.stdout

    # Must list Not Run section with 9 remaining checks
    assert "## Not Run" in report_output or "Not run" in report_output
    remaining_checks = [
        "IN-BP-001", "IN-BP-002", "IN-BP-004",
        "IN-DPDP-002", "IN-DPDP-004", "IN-DPDP-008",
        "IN-DPDP-009", "IN-DPDP-010", "IN-SPDI-001"
    ]
    for cid in remaining_checks:
        assert cid in report_output, f"Expected {cid} in Not Run report section"


# ---------------------------------------------------------------------------
# 2. Runs with --url (Dynamic + Static: 12 findings, scan object present)
# ---------------------------------------------------------------------------

def test_preflight_with_url_clean(tmp_path: Path, clean_app_server: str):
    """
    Run preflight with --url on clean-app:
    - Exactly 12 findings, one per active check.
    - Top-level 'scan' object present.
    - Report renders with 0 Not Run checks.
    """
    if not is_playwright_available():
        pytest.skip("Playwright Chromium browser executable is not installed.")

    out_file = tmp_path / "findings_clean_url.json"
    exit_code, doc = run_preflight(
        app_dir=CLEAN_APP_DIR,
        url=clean_app_server,
        out_path=out_file,
        report=False,
    )
    assert exit_code == 0
    assert out_file.is_file()

    # Scan object present from crawl
    assert "scan" in doc
    assert isinstance(doc["scan"]["pages_crawled"], int)
    assert doc["scan"]["pages_crawled"] >= 1

    # Exactly 12 findings
    findings = doc["findings"]
    assert len(findings) == 12
    check_ids = {f["check_id"] for f in findings}
    assert len(check_ids) == 12

    # Render report
    proc = subprocess.run(
        [
            sys.executable,
            str(WORKSPACE_ROOT / "scripts" / "report.py"),
            "--findings",
            str(out_file),
            "--jurisdiction",
            "india",
            "--today",
            "2026-10-29",
        ],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    report_output = proc.stdout
    # Should not list any active check under Not Run
    if "## Not Run" in report_output:
        not_run_body = report_output.split("## Not Run")[1].split("##")[0]
        assert "IN-" not in not_run_body


def test_preflight_with_url_flawed(tmp_path: Path, flawed_app_server: str):
    """
    Run preflight with --url on flawed-app:
    - Exactly 12 findings.
    - Top-level 'scan' object present.
    - Zero Not Run active checks.
    """
    if not is_playwright_available():
        pytest.skip("Playwright Chromium browser executable is not installed.")

    out_file = tmp_path / "findings_flawed_url.json"
    exit_code, doc = run_preflight(
        app_dir=FLAWED_APP_DIR,
        url=flawed_app_server,
        out_path=out_file,
        report=False,
    )
    assert exit_code == 0
    assert "scan" in doc
    assert len(doc["findings"]) == 12


# ---------------------------------------------------------------------------
# 3. Duplicate check_id detection
# ---------------------------------------------------------------------------

def test_duplicate_check_id_raises_error(tmp_path: Path):
    """If two scanners return the same check_id, preflight must raise and name both."""
    fake_scanners = {
        "age_signal": lambda d: {"findings": [{"check_id": "IN-DPDP-011", "result": "needs-human", "evidence": ["fake"]}]},
        "baseline": lambda d: {"findings": [{"check_id": "IN-DPDP-011", "result": "needs-human", "evidence": ["fake_dup"]}]},
    }
    with pytest.raises(RuntimeError) as exc_info:
        run_preflight(
            app_dir=CLEAN_APP_DIR,
            url=None,
            out_path=tmp_path / "dup.json",
            custom_scanners=fake_scanners,
        )
    err_msg = str(exc_info.value)
    assert "Duplicate check_id 'IN-DPDP-011'" in err_msg
    assert "age_signal" in err_msg
    assert "baseline" in err_msg


# ---------------------------------------------------------------------------
# 4. Out path writes strictly to specified location
# ---------------------------------------------------------------------------

def test_custom_out_path_outside_repo(tmp_path: Path):
    """Verify preflight writes only to specified out path, creating parents as needed."""
    custom_out = tmp_path / "deep" / "nested" / "output.json"
    exit_code, doc = run_preflight(
        app_dir=CLEAN_APP_DIR,
        url=None,
        out_path=custom_out,
    )
    assert exit_code == 0
    assert custom_out.is_file()
    # Confirm default reports/ was not created in tmp_path
    assert not (tmp_path / "reports").exists()


# ---------------------------------------------------------------------------
# 5. No absolute paths in output JSON
# ---------------------------------------------------------------------------

def test_no_absolute_paths_in_output_json(tmp_path: Path):
    """Ensure JSON output contains no absolute Windows file paths or drive letters."""
    out_file = tmp_path / "paths_check.json"
    run_preflight(app_dir=CLEAN_APP_DIR, url=None, out_path=out_file)
    text = out_file.read_text(encoding="utf-8")

    # Check for drive letters like C:\ or D:\
    assert not re.search(r'"[A-Za-z]:\\', text)
    assert not re.search(r'"[A-Za-z]:/', text)
    # Check for Windows backslashes in paths
    for f in json.loads(text)["findings"]:
        for ev in f["evidence"]:
            assert "\\" not in ev


# ---------------------------------------------------------------------------
# 6. Unreachable URL handling (Change 1)
# ---------------------------------------------------------------------------

def test_unreachable_url_unused_port(tmp_path: Path, capsys: pytest.CaptureFixture):
    """
    If URL is unreachable:
    - Print one line: 'crawl failed: <exception type>; crawl and pages checks not run'.
    - Still write static findings.
    - Mark crawl and pages as not run in summary.
    - Exit code 1.
    - Never print traceback or evidence.
    """
    unused_port = get_free_port()
    unreachable_url = f"http://127.0.0.1:{unused_port}"
    out_file = tmp_path / "unreachable.json"

    exit_code, doc = run_preflight(
        app_dir=CLEAN_APP_DIR,
        url=unreachable_url,
        out_path=out_file,
    )
    captured = capsys.readouterr()
    combined_output = captured.out + captured.err

    assert exit_code == 1
    # Check exact failure line format
    assert re.search(r"crawl failed: \w+; crawl and pages checks not run", combined_output)
    # Tracebacks must not be printed
    assert "Traceback" not in combined_output

    # Static findings must still be written
    assert out_file.is_file()
    assert "scan" not in doc
    assert len(doc["findings"]) == 3

    # Summary lines assert
    assert "crawl: not run (crawl failed)" in combined_output
    assert "pages: not run (crawl failed)" in combined_output


# ---------------------------------------------------------------------------
# 7. URL and App Directory Validation (Change 2)
# ---------------------------------------------------------------------------

def test_validation_invalid_url_scheme(tmp_path: Path, capsys: pytest.CaptureFixture):
    """Only http:// and https:// URLs are supported. Anything else exits 1."""
    # file:// scheme
    code_file, _ = run_preflight(app_dir=CLEAN_APP_DIR, url="file:///etc/passwd", out_path=tmp_path / "f.json")
    assert code_file == 1
    out_file = capsys.readouterr().err
    assert "Only http:// and https:// URLs are supported" in out_file

    # ftp:// scheme
    code_ftp, _ = run_preflight(app_dir=CLEAN_APP_DIR, url="ftp://example.com/test", out_path=tmp_path / "f.json")
    assert code_ftp == 1
    out_ftp = capsys.readouterr().err
    assert "Only http:// and https:// URLs are supported" in out_ftp


def test_validation_missing_app_directory(tmp_path: Path, capsys: pytest.CaptureFixture):
    """Non-existent app directory exits 1 before running scanners."""
    missing_dir = tmp_path / "non_existent_folder"
    code, _ = run_preflight(app_dir=missing_dir, url=None, out_path=tmp_path / "f.json")
    assert code == 1
    err = capsys.readouterr().err
    assert "Error: app directory not found" in err


# ---------------------------------------------------------------------------
# 8. Terminal output without --report contains no evidence (Change 4)
# ---------------------------------------------------------------------------

def test_terminal_output_without_report_has_no_evidence(tmp_path: Path, capsys: pytest.CaptureFixture):
    """
    Running without --report prints one summary line per scanner and ZERO evidence.
    """
    out_file = tmp_path / "summary_test.json"
    preflight_main([str(CLEAN_APP_DIR), "--out", str(out_file)])

    captured = capsys.readouterr().out
    lines = [line.strip() for line in captured.strip().splitlines() if line.strip()]

    # Exactly 4 scanner summary lines
    assert len(lines) == 4
    assert any(line.startswith("age_signal: ran") for line in lines)
    assert any(line.startswith("baseline: ran") for line in lines)
    assert any(line.startswith("crawl: not run") for line in lines)
    assert any(line.startswith("pages: not run") for line in lines)

    # No evidence snippets or file contents
    assert "encryption/transport:" not in captured
    assert "Strict-Transport-Security" not in captured
    assert "argon2" not in captured
    assert "dob_field:" not in captured


# ---------------------------------------------------------------------------
# 9. Terminal output with --report and no --url renders report with Not Run
# ---------------------------------------------------------------------------

def test_with_report_and_no_url_renders_not_run_section(tmp_path: Path, capsys: pytest.CaptureFixture):
    """
    Running with --report and no --url renders the report on stdout with 9 Not Run checks.
    """
    out_file = tmp_path / "report_test.json"
    preflight_main([str(CLEAN_APP_DIR), "--out", str(out_file), "--report", "--today", "2026-10-29"])

    captured = capsys.readouterr().out

    # Contains report markdown heading
    assert "# Privacy Preflight Findings Report" in captured
    # Contains Not Run section listing the 9 unrun checks
    assert "## Not Run" in captured or "Not run" in captured
    assert "IN-BP-001" in captured
    assert "IN-SPDI-001" in captured
    assert "IN-DPDP-002" in captured

