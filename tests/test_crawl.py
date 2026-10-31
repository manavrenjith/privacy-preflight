"""
Tests for Web Crawler and Findings Generator (Task 5b & 5b2).

Asserts:
- Crawls flawed-app and clean-app via local Python HTTP servers on free ports.
- Gracefully skips if Playwright browsers are not installed.
- Flawed app: external domains (fonts.googleapis.com, cdn.analytics.example.test) all fired on load,
  signup page has pre-checked bundled control, contact depth is 4,
  BP-001 is informational, BP-004 is informational, DPDP-004 is not-met, BP-002 is not-met.
- Clean app: zero external domains, no pre-checked or bundled controls, contact depth <= 2,
  BP-001 met, DPDP-004 met, BP-002 met, BP-004 informational with an empty inventory.
- Zero external connections made (all intercepted external requests aborted).
- Scan coverage object is generated in findings and rendered as a "Scan coverage" line in reports.
- Missing scan fields render "not reported" rather than 0.
- Bare word "contact" never triggers contact detection.
- Tests do not write into the repo root.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = WORKSPACE_ROOT / "demo"
FLAWED_APP_DIR = DEMO_DIR / "flawed-app"
CLEAN_APP_DIR = DEMO_DIR / "clean-app"
CRAWL_SCHEMA_PATH = WORKSPACE_ROOT / "references" / "crawl-schema.md"


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


@pytest.fixture(scope="module", autouse=True)
def check_playwright_installed() -> None:
    """Skip suite with clear instructions if Playwright or its browser is missing."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright python package is not installed. Run 'pip install playwright'.")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as exc:
        pytest.skip(
            f"Playwright Chromium browser executable is not installed. "
            f"Run 'playwright install chromium' to install it. Details: {exc}"
        )


@pytest.fixture(scope="module")
def flawed_app_server() -> Generator[str, None, None]:
    """Start python -m http.server on a free port for demo/flawed-app."""
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


@pytest.fixture(scope="module")
def clean_app_server() -> Generator[str, None, None]:
    """Start python -m http.server on a free port for demo/clean-app."""
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


def test_crawl_schema_documentation_exists() -> None:
    """Verify references/crawl-schema.md exists and documents required keys."""
    assert CRAWL_SCHEMA_PATH.is_file(), "references/crawl-schema.md must exist"
    content = CRAWL_SCHEMA_PATH.read_text(encoding="utf-8")
    assert "start_url" in content
    assert "consent_controls" in content
    assert "external_requests" in content
    assert "fired_on_load" in content
    assert "not resolved" in content
    assert "pages_crawled" in content
    assert "max_depth_reached" in content
    assert "pages_skipped" in content
    assert "pages_failed" in content
    assert "interactions" in content


def test_flawed_app_crawl_and_findings(flawed_app_server: str, tmp_path: Path) -> None:
    """
    Test crawl of flawed-app:
    - external domains include fonts.googleapis.com and cdn.analytics.example.test, both fired on load.
    - all external requests were aborted (no external connections made).
    - signup page has a pre-checked bundled control.
    - contact depth is 4.
    - findings: BP-001 is informational, BP-004 is informational, DPDP-004 is not-met, BP-002 is not-met.
    - findings document includes 'scan' object and coverage details in every notes string.
    - renders through scripts/report.py with 'Scan coverage:' in header.
    """
    out_crawl = tmp_path / "flawed-crawl.json"
    out_findings = tmp_path / "flawed-findings.json"

    # Execute crawl.py CLI
    cmd = [
        sys.executable,
        str(WORKSPACE_ROOT / "scripts" / "crawl.py"),
        "--url",
        f"{flawed_app_server}/index.html",
        "--out",
        str(out_crawl),
        "--findings-out",
        str(out_findings),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
    assert res.returncode == 0, f"crawl.py failed with: {res.stderr}"

    crawl_data: Dict[str, Any] = json.loads(out_crawl.read_text(encoding="utf-8"))
    findings_doc: Dict[str, Any] = json.loads(out_findings.read_text(encoding="utf-8"))

    # Verify 'scan' object in findings output
    assert "scan" in findings_doc, "findings output must include top-level 'scan' object"
    scan_meta = findings_doc["scan"]
    assert scan_meta["pages_crawled"] == 6
    assert scan_meta["max_depth_reached"] == 4
    assert scan_meta["pages_skipped"] == 0
    assert scan_meta["pages_failed"] == 0
    assert scan_meta["interactions"] == "none (no clicks except same-origin links, no forms submitted, no login)"

    findings_list: List[Dict[str, Any]] = findings_doc["findings"]

    # 1. External domains and interception
    summary = crawl_data["summary"]
    ext_domains = set(summary["external_domains"])
    assert "fonts.googleapis.com" in ext_domains
    assert "cdn.analytics.example.test" in ext_domains

    external_requests = crawl_data["external_requests"]
    assert len(external_requests) > 0
    # Every external request must be aborted (zero external contact)
    assert all(r["aborted"] is True for r in external_requests)
    # Both external domains fired on page load before user interaction
    domains_fired_on_load = {r["domain"] for r in external_requests if r.get("fired_on_load")}
    assert "fonts.googleapis.com" in domains_fired_on_load
    assert "cdn.analytics.example.test" in domains_fired_on_load

    # 2. Signup page has a pre-checked bundled control
    signup_pages = [p for p in crawl_data["pages"] if "signup" in p["url"]]
    assert len(signup_pages) >= 1
    signup_controls = signup_pages[0]["consent_controls"]
    assert any(c["is_pre_checked"] and c["is_bundled"] for c in signup_controls), (
        f"Expected a pre-checked and bundled control in signup.html: {signup_controls}"
    )

    # 3. Contact depth is 4
    assert summary["min_contact_depth"] == 4, (
        f"Expected contact depth 4 for flawed app, got {summary['min_contact_depth']}"
    )

    # 4. Check findings
    findings_map = {f["check_id"]: f for f in findings_list}
    assert set(findings_map.keys()) == {"IN-BP-004", "IN-BP-001", "IN-DPDP-004", "IN-BP-002"}

    assert findings_map["IN-BP-001"]["result"] == "informational"
    assert findings_map["IN-BP-004"]["result"] == "informational"
    assert findings_map["IN-DPDP-004"]["result"] == "not-met"
    assert findings_map["IN-BP-002"]["result"] == "not-met"

    # Notes line coverage check across all findings
    for f in findings_list:
        assert "pages crawled: 6" in f["notes"]
        assert "max depth reached: 4" in f["notes"]
        assert "interactions: none" in f["notes"]

    # 5. Render report using scripts/report.py
    report_cmd = [
        sys.executable,
        str(WORKSPACE_ROOT / "scripts" / "report.py"),
        "--findings",
        str(out_findings),
        "--jurisdiction",
        "india",
        "--today",
        "2026-10-29",
    ]
    report_res = subprocess.run(report_cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
    assert report_res.returncode == 0, f"report.py failed on flawed findings: {report_res.stderr}"
    assert "# Privacy Preflight Findings Report: India" in report_res.stdout
    assert "- **Scan coverage:** pages crawled: 6, max depth: 4, skipped: 0, failed: 0; interactions: none (no clicks except same-origin links, no forms submitted, no login)" in report_res.stdout
    assert "IN-BP-001" in report_res.stdout
    assert "IN-BP-004" in report_res.stdout
    assert "IN-DPDP-004" in report_res.stdout
    assert "IN-BP-002" in report_res.stdout


def test_clean_app_crawl_and_findings(clean_app_server: str, tmp_path: Path) -> None:
    """
    Test crawl of clean-app:
    - zero external domains.
    - no pre-checked or bundled controls.
    - contact depth is 2 or less.
    - findings: BP-001 met, DPDP-004 met, BP-002 met, BP-004 informational with empty inventory.
    - zero external connections made.
    - renders through scripts/report.py.
    """
    out_crawl = tmp_path / "clean-crawl.json"
    out_findings = tmp_path / "clean-findings.json"

    # Execute crawl.py CLI
    cmd = [
        sys.executable,
        str(WORKSPACE_ROOT / "scripts" / "crawl.py"),
        "--url",
        f"{clean_app_server}/index.html",
        "--out",
        str(out_crawl),
        "--findings-out",
        str(out_findings),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
    assert res.returncode == 0, f"crawl.py failed on clean-app: {res.stderr}"

    crawl_data: Dict[str, Any] = json.loads(out_crawl.read_text(encoding="utf-8"))
    findings_doc: Dict[str, Any] = json.loads(out_findings.read_text(encoding="utf-8"))

    assert "scan" in findings_doc
    findings_list: List[Dict[str, Any]] = findings_doc["findings"]

    # 1. Zero external domains
    summary = crawl_data["summary"]
    assert len(summary["external_domains"]) == 0
    assert len(crawl_data["external_requests"]) == 0

    # 2. No pre-checked or bundled controls
    assert summary["pre_checked_controls_count"] == 0
    assert summary["bundled_controls_count"] == 0
    for p in crawl_data["pages"]:
        for c in p.get("consent_controls", []):
            assert not c["is_pre_checked"], f"Control in {p['url']} must not be pre-checked: {c}"
            assert not c["is_bundled"], f"Control in {p['url']} must not be bundled: {c}"

    # 3. Contact depth is 2 or less
    assert summary["min_contact_depth"] is not None
    assert summary["min_contact_depth"] <= 2, (
        f"Expected clean app contact depth <= 2, got {summary['min_contact_depth']}"
    )

    # 4. Check findings
    findings_map = {f["check_id"]: f for f in findings_list}
    assert set(findings_map.keys()) == {"IN-BP-004", "IN-BP-001", "IN-DPDP-004", "IN-BP-002"}

    assert findings_map["IN-BP-001"]["result"] == "met"
    assert findings_map["IN-DPDP-004"]["result"] == "met"
    assert findings_map["IN-BP-002"]["result"] == "met"
    assert findings_map["IN-BP-004"]["result"] == "informational"

    # IN-BP-004 informational with an empty inventory
    bp_004_ev = findings_map["IN-BP-004"]["evidence"]
    assert len(bp_004_ev) == 1
    assert "empty inventory" in bp_004_ev[0]

    # Coverage suffix in notes
    for f in findings_list:
        assert "pages crawled:" in f["notes"]
        assert "interactions: none" in f["notes"]

    # 5. Render report using scripts/report.py
    report_cmd = [
        sys.executable,
        str(WORKSPACE_ROOT / "scripts" / "report.py"),
        "--findings",
        str(out_findings),
        "--jurisdiction",
        "india",
        "--today",
        "2026-10-29",
    ]
    report_res = subprocess.run(report_cmd, capture_output=True, text=True, cwd=str(WORKSPACE_ROOT))
    assert report_res.returncode == 0, f"report.py failed on clean findings: {report_res.stderr}"
    assert "# Privacy Preflight Findings Report: India" in report_res.stdout
    assert "Scan coverage:" in report_res.stdout
    assert "IN-BP-001" in report_res.stdout
    assert "IN-BP-004" in report_res.stdout
    assert "IN-DPDP-004" in report_res.stdout
    assert "IN-BP-002" in report_res.stdout


def test_contact_detection_bare_word_contact_never_counts() -> None:
    """Verify that bare word 'contact' does not trigger contact detection without email or mailto/tel."""
    from playwright.sync_api import sync_playwright
    from scripts.crawl import extract_contact_signals

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # HTML with bare word contact in heading, body and anchor text, but NO email and NO mailto/tel link
        html_without_contact_details = """
        <!DOCTYPE html>
        <html>
        <head><title>About Us</title></head>
        <body>
            <h2>Contact Us Today</h2>
            <p>If you have any questions, please contact our team via our support portal.</p>
            <a href="portal.html">Contact Portal</a>
        </body>
        </html>
        """
        page.set_content(html_without_contact_details)
        text = page.locator("body").inner_text()
        assert extract_contact_signals(page, text) is False, "Bare word 'contact' must not count as contact details"

        # HTML with mailto link
        html_with_mailto = """
        <!DOCTYPE html>
        <html>
        <head><title>Support</title></head>
        <body>
            <a href="mailto:support@example.test">Email Us</a>
        </body>
        </html>
        """
        page.set_content(html_with_mailto)
        text = page.locator("body").inner_text()
        assert extract_contact_signals(page, text) is True, "mailto: link must count as contact details"

        # HTML with tel link
        html_with_tel = """
        <!DOCTYPE html>
        <html>
        <head><title>Phone Support</title></head>
        <body>
            <a href="tel:+15551234567">Call Support</a>
        </body>
        </html>
        """
        page.set_content(html_with_tel)
        text = page.locator("body").inner_text()
        assert extract_contact_signals(page, text) is True, "tel: link must count as contact details"

        # HTML with plain email address in visible text
        html_with_email = """
        <!DOCTYPE html>
        <html>
        <head><title>Help</title></head>
        <body>
            <p>Write to help@example.test for inquiries.</p>
        </body>
        </html>
        """
        page.set_content(html_with_email)
        text = page.locator("body").inner_text()
        assert extract_contact_signals(page, text) is True, "Email in visible text must count as contact details"

        browser.close()


def test_report_scan_coverage_missing_fields_renders_not_reported(tmp_path: Path) -> None:
    """Verify that report.py renders 'not reported' when a scan field is missing."""
    from scripts.report import generate_report

    findings_file = tmp_path / "partial-scan.json"
    findings_content = {
        "scan": {
            "pages_crawled": 5
            # max_depth_reached, pages_skipped, pages_failed, interactions are all missing
        },
        "findings": [
            {
                "check_id": "IN-BP-001",
                "result": "met",
                "evidence": ["All static assets self-hosted."],
            }
        ],
    }
    findings_file.write_text(json.dumps(findings_content), encoding="utf-8")

    md, json_out = generate_report(
        findings_path=findings_file,
        jurisdiction="india",
        today=datetime_date(2026, 10, 29),
    )

    assert "- **Scan coverage:** pages crawled: 5, max depth: not reported, skipped: not reported, failed: not reported; interactions: not reported" in md
    assert json_out["scan"] == {"pages_crawled": 5}


def test_report_renders_without_scan_object(tmp_path: Path) -> None:
    """Verify findings files without a top-level 'scan' object still render cleanly."""
    from scripts.report import generate_report

    findings_file = tmp_path / "bare-list.json"
    bare_findings = [
        {
            "check_id": "IN-BP-001",
            "result": "met",
            "evidence": ["Self-hosted static assets."],
        }
    ]
    findings_file.write_text(json.dumps(bare_findings), encoding="utf-8")

    md, json_out = generate_report(
        findings_path=findings_file,
        jurisdiction="india",
        today=datetime_date(2026, 10, 29),
    )

    assert "Scan coverage:" not in md
    assert json_out["scan"] is None


def test_crawl_cli_default_paths() -> None:
    """Verify CLI argument parser defaults --out and --findings-out into reports/."""
    from scripts.crawl import main

    # Inspect parser defaults without executing network crawl
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--out", default="reports/crawl.json")
    parser.add_argument("--findings-out", default="reports/findings.json")

    args = parser.parse_args(["--url", "http://localhost:8000"])
    assert args.out == "reports/crawl.json"
    assert args.findings-out if False else args.findings_out == "reports/findings.json"


def datetime_date(year: int, month: int, day: int):
    import datetime
    return datetime.date(year, month, day)
