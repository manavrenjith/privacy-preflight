#!/usr/bin/env python3
"""
Privacy Preflight - Merge Runner (Task 9)

Orchestrates available privacy preflight analyzers and merges output into a single
findings JSON adhering to references/findings-schema.md.
- Always runs: age_signal (IN-DPDP-011) and baseline (IN-DPDP-013, IN-BP-003).
- Conditionally runs (if --url is provided): crawl (IN-BP-004, IN-BP-001, IN-DPDP-004, IN-BP-002)
  and pages (IN-DPDP-002, IN-DPDP-008, IN-DPDP-009, IN-DPDP-010, IN-SPDI-001).

Standard library only. Not legal advice.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.age_signal import evaluate_age_signals
from scripts.baseline import evaluate_baseline
from scripts.crawl import crawl_site, generate_findings
from scripts.pages import evaluate_pages
from scripts.report import main as report_main


def check_playwright_ready() -> Tuple[bool, Optional[str]]:
    """Probe if Playwright and Chromium browser binary are ready."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, "Playwright python package is not installed."

    browser = None
    p_cm = None
    try:
        p_cm = sync_playwright()
        p = p_cm.__enter__()
        browser = p.chromium.launch(headless=True)
        return True, None
    except Exception as exc:
        return False, f"Playwright Chromium browser executable is not installed ({exc})."
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if p_cm is not None:
            try:
                p_cm.__exit__(None, None, None)
            except Exception:
                pass


def run_preflight(
    app_dir: str | Path,
    url: Optional[str] = None,
    out_path: str | Path = "reports/findings.json",
    report: bool = False,
    today: Optional[str] = None,
    custom_scanners: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Run preflight analysis on target app_dir and optional site url.
    Returns (exit_code, findings_document).
    """
    target_dir = Path(app_dir).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Error: app directory not found: '{app_dir}'", file=sys.stderr)
        return 1, {}

    if url:
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.scheme.lower() not in ("http", "https") or not parsed_url.netloc:
            print(
                f"Error: invalid URL '{url}'. Only http:// and https:// URLs are supported",
                file=sys.stderr,
            )
            return 1, {}

    scanner_status: Dict[str, Tuple[str, Any]] = {}
    scanner_by_check_id: Dict[str, str] = {}
    findings_list: List[Dict[str, Any]] = []

    # 1. Run age_signal scanner (IN-DPDP-011)
    age_eval = (custom_scanners.get("age_signal") if custom_scanners else None) or evaluate_age_signals
    age_doc = age_eval(target_dir)
    age_findings = age_doc.get("findings", [])
    for f in age_findings:
        cid = f["check_id"]
        if cid in scanner_by_check_id:
            raise RuntimeError(
                f"Duplicate check_id '{cid}' returned by both '{scanner_by_check_id[cid]}' and 'age_signal'"
            )
        scanner_by_check_id[cid] = "age_signal"
        findings_list.append(f)
    scanner_status["age_signal"] = ("ran", len(age_findings))

    # 2. Run baseline scanner (IN-DPDP-013, IN-BP-003)
    base_eval = (custom_scanners.get("baseline") if custom_scanners else None) or evaluate_baseline
    base_doc = base_eval(target_dir)
    base_findings = base_doc.get("findings", [])
    for f in base_findings:
        cid = f["check_id"]
        if cid in scanner_by_check_id:
            raise RuntimeError(
                f"Duplicate check_id '{cid}' returned by both '{scanner_by_check_id[cid]}' and 'baseline'"
            )
        scanner_by_check_id[cid] = "baseline"
        findings_list.append(f)
    scanner_status["baseline"] = ("ran", len(base_findings))

    scan_object: Optional[Dict[str, Any]] = None
    exit_code = 0

    # 3. Dynamic crawl and page scanners (if --url provided)
    if not url:
        scanner_status["crawl"] = ("not run", "no --url provided")
        scanner_status["pages"] = ("not run", "no --url provided")
    else:
        # Run Playwright probe only when --url is given
        pw_ready, pw_reason = check_playwright_ready()
        if not pw_ready:
            print(f"Playwright is not installed or browsers are missing: {pw_reason}")
            print("Run 'pip install playwright' and then 'playwright install chromium' to enable crawling and page analysis.")
            print("Continuing without crawl and page checks.")
            scanner_status["crawl"] = ("not run", "Playwright not installed")
            scanner_status["pages"] = ("not run", "Playwright not installed")
        else:
            # Check reachability before crawling
            is_reachable = True
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "PrivacyPreflight/1.0"})
                with urllib.request.urlopen(req, timeout=3):
                    pass
            except urllib.error.HTTPError:
                # An HTTP response (e.g. 404, 500) still reached a responding server
                pass
            except Exception as exc:
                is_reachable = False
                print(f"crawl failed: {type(exc).__name__}; crawl and pages checks not run")
                scanner_status["crawl"] = ("not run", "crawl failed")
                scanner_status["pages"] = ("not run", "crawl failed")
                scan_object = None
                exit_code = 1

            if is_reachable:
                try:
                    crawl_func = (custom_scanners.get("crawl") if custom_scanners else None) or crawl_site
                    crawl_data = crawl_func(url)

                    pages = crawl_data.get("pages", [])
                    if not pages or all(p.get("status", 200) >= 400 for p in pages):
                        raise ConnectionError(f"Target URL returned error or no response: {url}")

                    gen_findings_func = (
                        custom_scanners.get("generate_findings") if custom_scanners else None
                    ) or generate_findings
                    crawl_findings_doc = gen_findings_func(crawl_data)

                    scan_object = crawl_findings_doc.get("scan")
                    crawl_findings = crawl_findings_doc.get("findings", [])
                    for f in crawl_findings:
                        cid = f["check_id"]
                        if cid in scanner_by_check_id:
                            raise RuntimeError(
                                f"Duplicate check_id '{cid}' returned by both '{scanner_by_check_id[cid]}' and 'crawl'"
                            )
                        scanner_by_check_id[cid] = "crawl"
                        findings_list.append(f)
                    scanner_status["crawl"] = ("ran", len(crawl_findings))

                    pages_eval_func = (custom_scanners.get("pages") if custom_scanners else None) or evaluate_pages
                    pages_findings_doc = pages_eval_func(crawl_data)
                    pages_findings = pages_findings_doc.get("findings", [])
                    for f in pages_findings:
                        cid = f["check_id"]
                        if cid in scanner_by_check_id:
                            raise RuntimeError(
                                f"Duplicate check_id '{cid}' returned by both '{scanner_by_check_id[cid]}' and 'pages'"
                            )
                        scanner_by_check_id[cid] = "pages"
                        findings_list.append(f)
                    scanner_status["pages"] = ("ran", len(pages_findings))

                except Exception as exc:
                    print(f"crawl failed: {type(exc).__name__}; crawl and pages checks not run")
                    scanner_status["crawl"] = ("not run", "crawl failed")
                    scanner_status["pages"] = ("not run", "crawl failed")
                    scan_object = None
                    exit_code = 1

    # Build final findings document
    doc: Dict[str, Any] = {}
    if scan_object is not None:
        doc["scan"] = scan_object
    doc["findings"] = findings_list

    # Write output JSON
    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)

    # Print summary lines (no evidence printed to terminal)
    for name in ["age_signal", "baseline", "crawl", "pages"]:
        st, detail = scanner_status[name]
        if st == "ran":
            suffix = "1 finding" if detail == 1 else f"{detail} findings"
            print(f"{name}: ran ({suffix})")
        else:
            print(f"{name}: not run ({detail})")

    # Optional report rendering
    if report:
        report_argv = ["--findings", str(destination), "--jurisdiction", "india"]
        if today:
            report_argv.extend(["--today", today])
        report_main(report_argv)

    return exit_code, doc


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Privacy Preflight - Merge Runner (runs available analyzers)"
    )
    parser.add_argument("app_directory", help="Path to local application codebase directory")
    parser.add_argument(
        "--url",
        default=None,
        help="URL of running site for dynamic crawl and page checks (e.g. http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--out",
        default="reports/findings.json",
        help="Path to output findings JSON (default: reports/findings.json)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Render the markdown report after writing findings",
    )
    parser.add_argument(
        "--today",
        default=None,
        help="Override evaluation date YYYY-MM-DD passed to report generator",
    )

    args = parser.parse_args(argv)

    exit_code, _ = run_preflight(
        app_dir=args.app_directory,
        url=args.url,
        out_path=args.out,
        report=args.report,
        today=args.today,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
