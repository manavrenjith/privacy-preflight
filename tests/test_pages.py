"""
Tests for Page Content Analyzer (scripts/pages.py - Task 6).

Asserts:
- Unit tests with synthetic crawl dictionaries covering met, unclear, and not-met for each check.
- Boundary tests:
  * 4/5 Rule 4 policy elements -> unclear
  * Role-only officer ('Grievance Officer (Fictional Role)') -> unclear
  * Webform-only contact -> not-met
  * Stated timeline in unrelated sentence -> unclear
  * Empty crawl -> not-met / unclear
  * Incomplete / truncated crawl -> missing pages evaluate to unclear instead of not-met
  * Timeline > 1 month (e.g. 90 days) -> met with warning note in notes
  * Multi-kind page (single page matching multiple kinds)
- Oracle test: Crawls both demo apps and asserts exact match against tests/expected-findings.json.
- Output renders through scripts/report.py without error.
- All test artifacts written to tmp_path (zero writes to repo root).
"""

from __future__ import annotations

import functools
import http.server
import json
import socket
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.crawl import crawl_site
from scripts.pages import evaluate_pages, extract_named_grievance_officer

DEMO_DIR = WORKSPACE_ROOT / "demo"
FLAWED_APP_DIR = DEMO_DIR / "flawed-app"
CLEAN_APP_DIR = DEMO_DIR / "clean-app"
EXPECTED_FINDINGS_PATH = WORKSPACE_ROOT / "tests" / "expected-findings.json"


def get_free_port() -> int:
    """Find and return an available TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture(scope="module")
def flawed_server() -> Generator[str, None, None]:
    """Start local HTTP server for demo/flawed-app in a daemon thread."""
    port = get_free_port()
    handler = functools.partial(SilentHandler, directory=str(FLAWED_APP_DIR))
    httpd = http.server.HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture(scope="module")
def clean_server() -> Generator[str, None, None]:
    """Start local HTTP server for demo/clean-app in a daemon thread."""
    port = get_free_port()
    handler = functools.partial(SilentHandler, directory=str(CLEAN_APP_DIR))
    httpd = http.server.HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


# ---------------------------------------------------------------------------
# Unit tests: Synthetic crawl dicts for each of the five checks
# ---------------------------------------------------------------------------

def test_dpdp_002_notice_met():
    """IN-DPDP-002: Notice linked from consent, covers withdraw/rights/complaint, has contact."""
    crawl_data = {
        "metadata": {"pages_crawled": 3, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/signup.html",
                "title": "Signup",
                "text": "Sign up form",
                "links": [{"href": "http://127.0.0.1/notice.html", "text": "Notice"}],
                "consent_controls": [{"is_pre_checked": False, "is_bundled": False}],
            },
            {
                "url": "http://127.0.0.1/notice.html",
                "title": "Data Protection Notice",
                "text": "You may withdraw consent at any time. Exercise your rights here. File a complaint to the Board. Email dpo@example.test for contact.",
                "links": [],
                "consent_controls": [],
            },
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-DPDP-002"]
    assert f["result"] == "met"
    assert any("/notice.html" in ev for ev in f["evidence"])
    assert f["notes"].endswith("(pages crawled: 3)")


def test_dpdp_002_notice_unclear_missing_link():
    """IN-DPDP-002: Notice page exists but no consent page links to it -> unclear."""
    crawl_data = {
        "metadata": {"pages_crawled": 2, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/signup.html",
                "title": "Signup",
                "text": "Sign up form",
                "links": [],  # does not link to notice
                "consent_controls": [{"is_pre_checked": False, "is_bundled": False}],
            },
            {
                "url": "http://127.0.0.1/notice.html",
                "title": "Data Protection Notice",
                "text": "You may withdraw consent at any time. Exercise your rights here. File a complaint to the Board. Email dpo@example.test.",
                "links": [],
                "consent_controls": [],
            },
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-DPDP-002"]
    assert f["result"] == "unclear"


def test_dpdp_002_notice_not_met_no_page():
    """IN-DPDP-002: Notice page not found in complete crawl -> not-met."""
    crawl_data = {
        "metadata": {"pages_crawled": 2, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/index.html",
                "title": "Home",
                "text": "Home page",
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-DPDP-002"]
    assert f["result"] == "not-met"
    assert "not found among the crawled pages" in f["evidence"][0]


def test_dpdp_008_contact_met():
    """IN-DPDP-008: Consent page has DPO role and email -> met."""
    crawl_data = {
        "metadata": {"pages_crawled": 2, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/signup.html",
                "title": "Signup",
                "text": "Contact Data Protection Officer at dpo@example.test",
                "links": [],
                "consent_controls": [{"is_pre_checked": False, "is_bundled": False}],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-DPDP-008"]
    assert f["result"] == "met"
    assert "covers consent pages only" in f["notes"]


def test_dpdp_008_contact_unclear_no_consent_pages():
    """IN-DPDP-008: App has no consent pages -> unclear."""
    crawl_data = {
        "metadata": {"pages_crawled": 2, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/index.html",
                "title": "Home",
                "text": "No forms here",
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-DPDP-008"]
    assert f["result"] == "unclear"


def test_dpdp_008_contact_not_met_failing_page():
    """IN-DPDP-008: Consent page has no contact info or direct link -> not-met."""
    crawl_data = {
        "metadata": {"pages_crawled": 2, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/signup.html",
                "title": "Signup",
                "text": "Signup form with no contact info",
                "links": [],
                "consent_controls": [{"is_pre_checked": False, "is_bundled": False}],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-DPDP-008"]
    assert f["result"] == "not-met"


def test_dpdp_009_rights_met():
    """IN-DPDP-009: Rights page covers access, correction, erasure, nomination, authentication."""
    crawl_data = {
        "metadata": {"pages_crawled": 1, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/rights.html",
                "title": "Data Principal Rights",
                "text": "Submit identity verification. Rights to access data summary, correction of details, erasure of records, nomination of representative.",
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-DPDP-009"]
    assert f["result"] == "met"
    assert "pass threshold: 5/5 groups present" in f["notes"]


def test_dpdp_009_rights_unclear_missing_nomination():
    """IN-DPDP-009: Rights page missing nomination -> unclear."""
    crawl_data = {
        "metadata": {"pages_crawled": 1, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/rights.html",
                "title": "Data Principal Rights",
                "text": "Submit identity verification. Rights to access, correction, and erasure.",
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-DPDP-009"]
    assert f["result"] == "unclear"
    assert "missing" in f["evidence"][0]


def test_dpdp_010_grievance_met():
    """IN-DPDP-010: Grievance page with stated response timeline -> met."""
    crawl_data = {
        "metadata": {"pages_crawled": 1, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/grievance.html",
                "title": "Grievance Redressal",
                "text": "Submit your grievance. Our team will respond within 30 days of receipt.",
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-DPDP-010"]
    assert f["result"] == "met"
    assert "30 days" in f["evidence"][0]
    assert "SPDI r.5(9)" in f["notes"]
    assert "DPDP r.14(3)" in f["notes"]


def test_dpdp_010_grievance_timeline_exceeds_one_month():
    """IN-DPDP-010: Timeline > 30 days (e.g. 90 days) -> met, with note on SPDI 1-month clock."""
    crawl_data = {
        "metadata": {"pages_crawled": 1, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/grievance.html",
                "title": "Grievance Redressal",
                "text": "Submit your grievance. Our team will respond within 90 days of receipt.",
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-DPDP-010"]
    assert f["result"] == "met"
    assert "exceeds the SPDI r.5(9) one-month clock" in f["notes"]


def test_spdi_001_privacy_policy_met():
    """IN-SPDI-001: Privacy policy with 5 elements + named officer with contact."""
    crawl_data = {
        "metadata": {"pages_crawled": 1, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/privacy.html",
                "title": "Privacy Policy",
                "text": (
                    "Privacy Policy\n"
                    "1. Information We Collect (What is Collected)\n"
                    "We collect personal information.\n"
                    "2. Purpose of Collection and Usage\n"
                    "Purposes of processing.\n"
                    "3. Disclosure of Personal Information\n"
                    "Disclosure of data.\n"
                    "4. Reasonable Security Practices\n"
                    "Security safeguards.\n"
                    "5. Grievance Officer\n"
                    "Designated Grievance Officer: Name: Alex Sharma\n"
                    "Email: grievance@example.test\n"
                ),
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-SPDI-001"]
    assert f["result"] == "met"
    assert "Alex Sharma" in f["evidence"][1]


# ---------------------------------------------------------------------------
# Boundary tests
# ---------------------------------------------------------------------------

def test_boundary_spdi_001_four_out_of_five_elements_unclear():
    """Boundary: Privacy policy with 4/5 elements (missing disclosure) -> unclear."""
    crawl_data = {
        "metadata": {"pages_crawled": 1, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/privacy.html",
                "title": "Privacy Policy",
                "text": (
                    "Privacy Policy\n"
                    "1. Information We Collect\n"
                    "2. Purpose of Collection\n"
                    "3. Security Practices\n"
                    # Disclosure missing
                    "Designated Grievance Officer: Name: Jane Doe\n"
                    "Email: dpo@example.test\n"
                ),
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-SPDI-001"]
    assert f["result"] == "unclear"
    assert "disclosure" in f["evidence"][0]


def test_boundary_spdi_001_role_only_officer_unclear():
    """Boundary: Officer has role title only without personal name -> unclear."""
    crawl_data = {
        "metadata": {"pages_crawled": 1, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/privacy.html",
                "title": "Privacy Policy",
                "text": (
                    "Privacy Policy\n"
                    "1. Information We Collect\n"
                    "2. Purpose of Collection and Usage\n"
                    "3. Disclosure of Information\n"
                    "4. Security Practices and Procedures\n"
                    "Designated Grievance Officer: Grievance Officer (Fictional Role)\n"
                    "Contact Email: grievance@example.test\n"
                ),
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-SPDI-001"]
    assert f["result"] == "unclear"
    assert "lacks explicit name" in f["evidence"][0]


def test_boundary_webform_only_contact_not_met():
    """Boundary: Consent page has an inquiry webform but no email, phone, or named role -> not-met."""
    crawl_data = {
        "metadata": {"pages_crawled": 1, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/signup.html",
                "title": "Sign Up",
                "text": "Please enter your message in the feedback form below. Submit Message.",
                "links": [],
                "consent_controls": [{"is_pre_checked": False, "is_bundled": False}],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-DPDP-008"]
    assert f["result"] == "not-met"


def test_boundary_timeline_unrelated_sentence_unclear():
    """Boundary: Timeline phrase appears in an unrelated context window -> unclear."""
    crawl_data = {
        "metadata": {"pages_crawled": 1, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/grievance.html",
                "title": "Grievance Redressal",
                "text": "Submit your grievance. Our annual holiday sale has been running for 30 days.",
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-DPDP-010"]
    assert f["result"] == "unclear"
    assert "no stated response timeline found within context window" in f["evidence"][0]


def test_boundary_empty_crawl():
    """Boundary: Crawl with zero pages."""
    crawl_data = {
        "metadata": {"pages_crawled": 0, "pages_failed": 0, "max_pages": 30},
        "pages": [],
    }
    res = evaluate_pages(crawl_data)
    findings_map = {f["check_id"]: f for f in res["findings"]}
    assert findings_map["IN-DPDP-008"]["result"] == "unclear"
    assert findings_map["IN-DPDP-002"]["result"] == "not-met"
    assert findings_map["IN-DPDP-009"]["result"] == "not-met"
    assert findings_map["IN-DPDP-010"]["result"] == "not-met"
    assert findings_map["IN-SPDI-001"]["result"] == "not-met"


def test_incomplete_crawl_downgrades_missing_pages_to_unclear():
    """Crawl metadata with pages_failed > 0 downgrades missing pages to unclear."""
    crawl_data = {
        "metadata": {"pages_crawled": 5, "pages_failed": 2, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/index.html",
                "title": "Home",
                "text": "Home page",
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    findings_map = {f["check_id"]: f for f in res["findings"]}
    assert findings_map["IN-DPDP-002"]["result"] == "unclear"
    assert findings_map["IN-DPDP-009"]["result"] == "unclear"
    assert findings_map["IN-DPDP-010"]["result"] == "unclear"
    assert findings_map["IN-SPDI-001"]["result"] == "unclear"
    assert "crawl incomplete" in findings_map["IN-DPDP-002"]["evidence"][0]


def test_multi_kind_page_evaluated_for_multiple_checks():
    """A single page matching multiple kinds is assigned all matching kinds."""
    crawl_data = {
        "metadata": {"pages_crawled": 1, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/legal.html",
                "title": "Notice, Rights, Grievance, and Privacy Policy",
                "text": (
                    "Data Protection Notice: Withdraw consent, statutory rights, complaint to Board. Email dpo@example.test\n"
                    "Rights Portal: Verify identity. Access, correction, erasure, nomination.\n"
                    "Grievance Redressal: We respond within 30 days.\n"
                    "Privacy Policy\n"
                    "1. Information We Collect\n"
                    "2. Purpose of Collection and Usage\n"
                    "3. Disclosure of Data\n"
                    "4. Security Practices\n"
                    "Grievance Officer Name: Jane Doe\n"
                    "Email: dpo@example.test\n"
                ),
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    findings_map = {f["check_id"]: f for f in res["findings"]}
    assert findings_map["IN-DPDP-009"]["result"] == "met"
    assert findings_map["IN-DPDP-010"]["result"] == "met"
    assert findings_map["IN-SPDI-001"]["result"] == "met"


def test_boundary_spdi_001_title_only_privacy_policy_does_not_count_practices():
    """Boundary: A policy page whose only match for practices is the title 'Privacy Policy' must NOT count practices."""
    crawl_data = {
        "metadata": {"pages_crawled": 1, "pages_failed": 0, "max_pages": 30},
        "pages": [
            {
                "url": "http://127.0.0.1/privacy.html",
                "title": "Privacy Policy",
                "text": (
                    "Privacy Policy\n"
                    "1. Information We Collect\n"
                    "2. Purpose of Collection\n"
                    "3. Disclosure of Data\n"
                    "4. Security Safeguards\n"
                    "Designated Grievance Officer: Name: Jane Doe\n"
                    "Email: dpo@example.test\n"
                ),
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    f = {item["check_id"]: item for item in res["findings"]}["IN-SPDI-001"]
    assert f["result"] == "unclear"
    assert "practices" in f["evidence"][0]


def test_name_placeholders_rejected():
    """'Name:' path rejects placeholders case-insensitively (tbd, tba, n/a, etc.)."""
    for placeholder in ["Name: TBD", "Name: N/A", "Name: TBA"]:
        text = f"Designated Grievance Officer: {placeholder}\nEmail: grievance@example.test"
        res = extract_named_grievance_officer(text)
        assert res is None, f"Expected '{placeholder}' to be rejected, but got {res}"


def test_name_alex_sharma_accepted():
    """'Name:' path accepts valid personal name 'Name: Alex Sharma'."""
    text = "Designated Grievance Officer: Name: Alex Sharma\nEmail: grievance@example.test"
    res = extract_named_grievance_officer(text)
    assert res is not None
    name, contact = res
    assert name == "Alex Sharma"
    assert contact == "grievance@example.test"


def test_incomplete_crawl_pages_skipped_downgrades_to_unclear():
    """Crawl metadata with pages_skipped > 0 downgrades missing pages to unclear."""
    crawl_data = {
        "metadata": {
            "pages_crawled": 5,
            "pages_failed": 0,
            "pages_skipped": 1,
            "max_pages": 30,
            "max_depth": 4,
            "max_depth_reached": 2,
        },
        "pages": [
            {
                "url": "http://127.0.0.1/index.html",
                "title": "Home",
                "text": "Home page",
                "links": [],
                "consent_controls": [],
            }
        ],
    }
    res = evaluate_pages(crawl_data)
    findings_map = {f["check_id"]: f for f in res["findings"]}
    assert findings_map["IN-DPDP-002"]["result"] == "unclear"
    assert findings_map["IN-DPDP-009"]["result"] == "unclear"
    assert findings_map["IN-DPDP-010"]["result"] == "unclear"
    assert findings_map["IN-SPDI-001"]["result"] == "unclear"
    assert "crawl incomplete" in findings_map["IN-DPDP-002"]["evidence"][0]


def test_incomplete_crawl_depth_limit_with_uncrawled_link_downgrades_to_unclear():
    """(a) A not-found check with a page at the depth limit that links to an uncrawled URL -> unclear."""
    crawl_data = {
        "metadata": {
            "pages_crawled": 2,
            "pages_failed": 0,
            "pages_skipped": 0,
            "max_pages": 30,
            "max_depth": 2,
        },
        "pages": [
            {
                "url": "http://127.0.0.1/index.html",
                "depth": 0,
                "title": "Home",
                "text": "Home page",
                "links": [{"href": "http://127.0.0.1/page.html", "text": "Page"}],
                "consent_controls": [],
            },
            {
                "url": "http://127.0.0.1/page.html",
                "depth": 2,
                "title": "Page at limit",
                "text": "Deep page",
                "links": [{"href": "http://127.0.0.1/uncrawled.html", "text": "Uncrawled"}],
                "consent_controls": [],
            },
        ],
    }
    res = evaluate_pages(crawl_data)
    findings_map = {f["check_id"]: f for f in res["findings"]}
    assert findings_map["IN-DPDP-002"]["result"] == "unclear"
    assert findings_map["IN-DPDP-009"]["result"] == "unclear"
    assert findings_map["IN-DPDP-010"]["result"] == "unclear"
    assert findings_map["IN-SPDI-001"]["result"] == "unclear"
    assert "crawl incomplete" in findings_map["IN-DPDP-002"]["evidence"][0]
    expected_note_phrase = (
        "the crawl may not have reached every page (links beyond the depth limit, "
        "skipped or failed pages, or the page limit)"
    )
    assert expected_note_phrase in findings_map["IN-DPDP-002"]["notes"]


def test_incomplete_crawl_depth_limit_with_crawled_link_evaluates_to_not_met():
    """(b) The same crawl where that link points to an already crawled page -> not-met."""
    crawl_data = {
        "metadata": {
            "pages_crawled": 2,
            "pages_failed": 0,
            "pages_skipped": 0,
            "max_pages": 30,
            "max_depth": 2,
        },
        "pages": [
            {
                "url": "http://127.0.0.1/index.html",
                "depth": 0,
                "title": "Home",
                "text": "Home page",
                "links": [{"href": "http://127.0.0.1/page.html", "text": "Page"}],
                "consent_controls": [],
            },
            {
                "url": "http://127.0.0.1/page.html",
                "depth": 2,
                "title": "Page at limit",
                "text": "Deep page",
                "links": [{"href": "http://127.0.0.1/index.html", "text": "Home"}],
                "consent_controls": [],
            },
        ],
    }
    res = evaluate_pages(crawl_data)
    findings_map = {f["check_id"]: f for f in res["findings"]}
    assert findings_map["IN-DPDP-002"]["result"] == "not-met"
    assert findings_map["IN-DPDP-009"]["result"] == "not-met"
    assert findings_map["IN-DPDP-010"]["result"] == "not-met"
    assert findings_map["IN-SPDI-001"]["result"] == "not-met"


def test_incomplete_crawl_depth_limit_link_differing_by_fragment_or_slash_counts_as_crawled():
    """(c) A link differing only by #fragment or trailing slash counts as crawled."""
    crawl_data = {
        "metadata": {
            "pages_crawled": 2,
            "pages_failed": 0,
            "pages_skipped": 0,
            "max_pages": 30,
            "max_depth": 2,
        },
        "pages": [
            {
                "url": "http://127.0.0.1/index.html",
                "depth": 0,
                "title": "Home",
                "text": "Home page",
                "links": [{"href": "http://127.0.0.1/page.html", "text": "Page"}],
                "consent_controls": [],
            },
            {
                "url": "http://127.0.0.1/page.html",
                "depth": 2,
                "title": "Page at limit",
                "text": "Deep page",
                # Links differ by fragment and trailing slash from crawled URLs
                "links": [
                    {"href": "http://127.0.0.1/index.html#content", "text": "Home with fragment"},
                    {"href": "http://127.0.0.1/page.html/", "text": "Self with trailing slash"},
                ],
                "consent_controls": [],
            },
        ],
    }
    res = evaluate_pages(crawl_data)
    findings_map = {f["check_id"]: f for f in res["findings"]}
    assert findings_map["IN-DPDP-002"]["result"] == "not-met"
    assert findings_map["IN-DPDP-009"]["result"] == "not-met"
    assert findings_map["IN-DPDP-010"]["result"] == "not-met"
    assert findings_map["IN-SPDI-001"]["result"] == "not-met"


# ---------------------------------------------------------------------------
# Oracle test: Crawl demo apps and compare against tests/expected-findings.json
# ---------------------------------------------------------------------------

def test_oracle_flawed_app_matches_expected_findings(flawed_server: str):
    """Crawl flawed app and assert every check matches tests/expected-findings.json."""
    crawl_res = crawl_site(start_url=f"{flawed_server}/index.html", max_pages=30, max_depth=4)
    pages_doc = evaluate_pages(crawl_res)

    expected_all = json.loads(EXPECTED_FINDINGS_PATH.read_text(encoding="utf-8"))
    flawed_expected = expected_all["flawed-app"]

    findings_map = {f["check_id"]: f for f in pages_doc["findings"]}
    target_checks = ["IN-DPDP-002", "IN-DPDP-008", "IN-DPDP-009", "IN-DPDP-010", "IN-SPDI-001"]

    for cid in target_checks:
        actual_res = findings_map[cid]["result"]
        expected_res = flawed_expected[cid]["result"]
        assert actual_res == expected_res, (
            f"Flawed app {cid} result mismatch: got {actual_res}, expected {expected_res}. "
            f"Evidence: {findings_map[cid]['evidence']}"
        )


def test_oracle_clean_app_matches_expected_findings(clean_server: str):
    """Crawl clean app and assert every check matches tests/expected-findings.json."""
    crawl_res = crawl_site(start_url=f"{clean_server}/index.html", max_pages=30, max_depth=4)
    pages_doc = evaluate_pages(crawl_res)

    expected_all = json.loads(EXPECTED_FINDINGS_PATH.read_text(encoding="utf-8"))
    clean_expected = expected_all["clean-app"]

    findings_map = {f["check_id"]: f for f in pages_doc["findings"]}
    target_checks = ["IN-DPDP-002", "IN-DPDP-008", "IN-DPDP-009", "IN-DPDP-010", "IN-SPDI-001"]

    for cid in target_checks:
        actual_res = findings_map[cid]["result"]
        expected_res = clean_expected[cid]["result"]
        assert actual_res == expected_res, (
            f"Clean app {cid} result mismatch: got {actual_res}, expected {expected_res}. "
            f"Evidence: {findings_map[cid]['evidence']}"
        )


# ---------------------------------------------------------------------------
# CLI & Report.py integration tests
# ---------------------------------------------------------------------------

def test_pages_cli_and_report_rendering(clean_server: str, tmp_path: Path):
    """Execute pages.py CLI on crawl output and render through scripts/report.py."""
    crawl_json = tmp_path / "clean_crawl.json"
    findings_json = tmp_path / "pages_findings.json"

    crawl_res = crawl_site(start_url=f"{clean_server}/index.html", max_pages=30, max_depth=4)
    crawl_json.write_text(json.dumps(crawl_res), encoding="utf-8")

    # Run pages.py CLI
    proc = subprocess.run(
        [
            sys.executable,
            str(WORKSPACE_ROOT / "scripts" / "pages.py"),
            str(crawl_json),
            "--findings-out",
            str(findings_json),
        ],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"pages.py CLI failed: {proc.stderr}"
    assert findings_json.is_file()

    doc = json.loads(findings_json.read_text(encoding="utf-8"))
    assert "scan" in doc
    assert len(doc["findings"]) == 5

    # Render through report.py
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
    assert report_proc.returncode == 0, f"report.py failed on pages findings: {report_proc.stderr}"
    stdout = report_proc.stdout
    assert "# Privacy Preflight Findings Report: India" in stdout
    assert "IN-DPDP-002" in stdout
    assert "IN-DPDP-008" in stdout
    assert "IN-DPDP-009" in stdout
    assert "IN-DPDP-010" in stdout
    assert "IN-SPDI-001" in stdout
