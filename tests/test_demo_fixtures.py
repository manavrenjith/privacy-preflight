"""
Tests for Privacy Preflight Demo Fixtures (Task 5a).

Asserts:
1. Both apps exist and contain the required file layout.
2. No real-looking secrets or personal data appear across any demo files.
3. The flawed app contains each planted marker, and the clean app contains none of them.
4. expected-findings.json lists every active check ID from references/jurisdictions/india.md
   for both apps, with correct result enums and causal file references.
5. demo/README.md documents local serving and includes compliance warnings.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
DEMO_DIR = WORKSPACE_ROOT / "demo"
FLAWED_APP_DIR = DEMO_DIR / "flawed-app"
CLEAN_APP_DIR = DEMO_DIR / "clean-app"
INDIA_MD_PATH = WORKSPACE_ROOT / "references" / "jurisdictions" / "india.md"
EXPECTED_FINDINGS_PATH = WORKSPACE_ROOT / "tests" / "expected-findings.json"

# Regexes for secret detection
SECRET_PATTERNS = [
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                     # AWS Access Key
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,}\b"),          # GitHub Token
    re.compile(r"\bxox[baprs]-[0-9]{10,}\b"),                # Slack Token
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), # Private Keys
    re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),               # Google API Key
    re.compile(r"\b(?:sk|pk)_(?:live|test)_[0-9a-zA-Z]{24,}\b"), # Stripe Keys
]

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b")
PHONE_PATTERN = re.compile(r"(?:\+91[-\s]?)?[6-9]\d{9}\b")


def get_demo_text_files() -> List[Path]:
    """Return all non-binary files across demo/."""
    text_files: List[Path] = []
    binary_suffixes = {".woff", ".woff2", ".ttf", ".eot", ".png", ".jpg", ".jpeg", ".ico"}
    for p in DEMO_DIR.rglob("*"):
        if p.is_file() and p.suffix.lower() not in binary_suffixes:
            text_files.append(p)
    return text_files


def extract_active_india_check_ids() -> List[str]:
    """Parse references/jurisdictions/india.md and return active check IDs."""
    from scripts.validate_checks import extract_fenced_yaml_checks

    checks = extract_fenced_yaml_checks(INDIA_MD_PATH)
    active_ids = [c["id"] for c in checks if c.get("status", "active") == "active"]
    return active_ids


def test_apps_exist():
    """Assert both demo apps and their expected directories and core files exist."""
    assert DEMO_DIR.is_dir(), "demo/ directory must exist"
    assert FLAWED_APP_DIR.is_dir(), "demo/flawed-app/ directory must exist"
    assert CLEAN_APP_DIR.is_dir(), "demo/clean-app/ directory must exist"

    # Core files that must exist in flawed-app
    flawed_expected = [
        "index.html",
        "signup.html",
        "contact.html",
        "auth.js",
        "nginx.conf",
        "storage.rules",
        "logging.json",
        ".env",
        "nav/step1.html",
        "nav/step2.html",
        "nav/step3.html",
        "css/style.css",
    ]
    for rel_path in flawed_expected:
        assert (FLAWED_APP_DIR / rel_path).is_file(), f"demo/flawed-app/{rel_path} must exist"

    # Pages that must NOT exist in flawed-app (deliberately omitted planted flaws)
    flawed_prohibited = ["privacy.html", "rights.html", "grievance.html", "notice.html"]
    for rel_path in flawed_prohibited:
        assert not (FLAWED_APP_DIR / rel_path).exists(), f"demo/flawed-app/{rel_path} must not exist (planted omission)"

    # Core files that must exist in clean-app
    clean_expected = [
        "index.html",
        "signup.html",
        "contact.html",
        "notice.html",
        "rights.html",
        "grievance.html",
        "privacy.html",
        "auth.js",
        "nginx.conf",
        "storage.rules",
        "logging.json",
        ".env.example",
        ".gitignore",
        "css/style.css",
        "fonts/roboto.woff2",
    ]
    for rel_path in clean_expected:
        assert (CLEAN_APP_DIR / rel_path).is_file(), f"demo/clean-app/{rel_path} must exist"

    # Clean app must NOT have committed .env
    assert not (CLEAN_APP_DIR / ".env").exists(), "demo/clean-app/.env must not exist (must be ignored)"


def test_no_real_looking_secrets_or_personal_data():
    """Assert no real secrets, credentials, or emails outside example.com/example.test appear."""
    allowed_domains = {"example.com", "example.test"}
    text_files = get_demo_text_files()
    assert len(text_files) >= 15, f"Expected at least 15 demo files, found {len(text_files)}"

    for file_path in text_files:
        content = file_path.read_text(encoding="utf-8", errors="replace")

        # 1. Verify secrets
        for pat in SECRET_PATTERNS:
            match = pat.search(content)
            assert match is None, f"Real-looking secret matching {pat.pattern} found in {file_path}"

        # If a fake key is present, verify it is explicitly fake and commented as fixture
        if "FAKE_KEY" in content:
            assert "FAKE_KEY_DO_NOT_USE_0000" in content, f"Unexpected fake secret in {file_path}"
            assert "FIXTURE" in content.upper() or "FIXTURE" in file_path.name.upper(), (
                f"Fake secret in {file_path} must carry a fixture comment"
            )

        # 2. Verify emails
        for match in EMAIL_PATTERN.finditer(content):
            domain = match.group(1).lower()
            # Allowed: example.com, example.test, or *.test subdomains
            is_allowed = (
                domain in allowed_domains
                or domain.endswith(".example.com")
                or domain.endswith(".example.test")
                or domain.endswith(".test")
            )
            assert is_allowed, f"Disallowed email domain '{domain}' found in {file_path}: {match.group(0)}"

        # 3. Verify phone numbers
        phone_match = PHONE_PATTERN.search(content)
        assert phone_match is None, f"Real-looking phone number found in {file_path}: {phone_match.group(0)}"


def test_planted_markers_in_flawed_and_clean_apps():
    """
    Verify each planted flaw exists in flawed-app and is fixed in clean-app:
    - IN-BP-004 & IN-BP-001: fonts.googleapis.com and cdn.analytics.example.test
    - IN-DPDP-004: bundled pre-ticked consent
    - IN-DPDP-002: notice link and withdrawal/rights/complaints routes
    - IN-DPDP-008 & IN-BP-002: footer contact details and nested click distance
    - IN-DPDP-009: data principal rights mechanisms
    - IN-DPDP-010: grievance route and 30-day response time
    - IN-DPDP-011: date-of-birth and parental consent branch
    - IN-DPDP-013 & IN-BP-003: .env committed vs ignored, MD5 vs argon2id, HSTS, storage.rules, log retention
    - IN-SPDI-001: privacy policy and named Grievance Officer
    """
    flawed_index = (FLAWED_APP_DIR / "index.html").read_text(encoding="utf-8")
    flawed_signup = (FLAWED_APP_DIR / "signup.html").read_text(encoding="utf-8")
    flawed_auth = (FLAWED_APP_DIR / "auth.js").read_text(encoding="utf-8")
    flawed_nginx = (FLAWED_APP_DIR / "nginx.conf").read_text(encoding="utf-8")
    flawed_storage = (FLAWED_APP_DIR / "storage.rules").read_text(encoding="utf-8")
    flawed_logging = json.loads((FLAWED_APP_DIR / "logging.json").read_text(encoding="utf-8"))

    clean_index = (CLEAN_APP_DIR / "index.html").read_text(encoding="utf-8")
    clean_signup = (CLEAN_APP_DIR / "signup.html").read_text(encoding="utf-8")
    clean_notice = (CLEAN_APP_DIR / "notice.html").read_text(encoding="utf-8")
    clean_rights = (CLEAN_APP_DIR / "rights.html").read_text(encoding="utf-8")
    clean_grievance = (CLEAN_APP_DIR / "grievance.html").read_text(encoding="utf-8")
    clean_privacy = (CLEAN_APP_DIR / "privacy.html").read_text(encoding="utf-8")
    clean_auth = (CLEAN_APP_DIR / "auth.js").read_text(encoding="utf-8")
    clean_nginx = (CLEAN_APP_DIR / "nginx.conf").read_text(encoding="utf-8")
    clean_storage = (CLEAN_APP_DIR / "storage.rules").read_text(encoding="utf-8")
    clean_logging = json.loads((CLEAN_APP_DIR / "logging.json").read_text(encoding="utf-8"))

    # Marker 1 (IN-BP-004 & IN-BP-001): Remote fonts & analytics script
    assert "fonts.googleapis.com" in flawed_index
    assert "cdn.analytics.example.test/track.js" in flawed_index

    clean_all_text = "".join(f.read_text(encoding="utf-8", errors="replace") for f in get_demo_text_files() if "clean-app" in str(f))
    assert "fonts.googleapis.com" not in clean_all_text
    assert "cdn.analytics.example.test" not in clean_all_text
    assert "@font-face" in (CLEAN_APP_DIR / "css" / "style.css").read_text(encoding="utf-8")

    # Marker 2 (IN-DPDP-004): Pre-ticked bundled consent
    # Flawed has a checkbox with checked attribute bundling marketing and analytics
    assert re.search(r"<input[^>]*type=['\"]checkbox['\"][^>]*checked", flawed_signup, re.IGNORECASE)
    assert "marketing" in flawed_signup.lower() and "analytics" in flawed_signup.lower()

    # Clean has separate, unchecked checkboxes
    consent_checkboxes = re.findall(r"<input[^>]*type=['\"]checkbox['\"][^>]*>", clean_signup, re.IGNORECASE)
    assert len(consent_checkboxes) >= 2
    for cb in consent_checkboxes:
        assert "checked" not in cb.lower(), f"Consent checkbox in clean-app must not be pre-ticked: {cb}"
    assert "consent_marketing" in clean_signup
    assert "consent_analytics" in clean_signup

    # Marker 3 (IN-DPDP-002): Notice link and routes
    assert "notice.html" not in flawed_signup
    assert "notice.html" in clean_signup
    assert "index.html" in clean_notice  # Communication link
    assert "withdraw" in clean_notice.lower()  # Withdrawal route
    assert "rights" in clean_notice.lower() and "rights.html" in clean_notice  # Rights route
    assert "Data Protection Board of India" in clean_notice  # Complaints route

    # Marker 4 (IN-DPDP-008 & IN-BP-002): Contact details & nested click distance
    assert "dpo@example.com" not in flawed_index
    assert "dpo@example.com" not in flawed_signup
    # In flawed app, reaching contact.html requires navigating through 4 nested steps
    assert "nav/step1.html" in flawed_index
    step1_text = (FLAWED_APP_DIR / "nav" / "step1.html").read_text(encoding="utf-8")
    assert "step2.html" in step1_text
    step2_text = (FLAWED_APP_DIR / "nav" / "step2.html").read_text(encoding="utf-8")
    assert "step3.html" in step2_text
    step3_text = (FLAWED_APP_DIR / "nav" / "step3.html").read_text(encoding="utf-8")
    assert "contact.html" in step3_text

    # In clean app, contact details and link are in footer (<= 2 clicks)
    assert "dpo@example.com" in clean_index
    assert "contact.html" in clean_index
    assert "Data Protection Officer" in clean_index

    # Marker 5 (IN-DPDP-009): Rights mechanisms
    assert not (FLAWED_APP_DIR / "rights.html").exists()
    assert (CLEAN_APP_DIR / "rights.html").is_file()
    assert "access" in clean_rights.lower()
    assert "correction" in clean_rights.lower()
    assert "erasure" in clean_rights.lower()
    assert "nomination" in clean_rights.lower()
    assert "authentication" in clean_rights.lower()

    # Marker 6 (IN-DPDP-010): Grievance redressal and 30-day response time
    assert not (FLAWED_APP_DIR / "grievance.html").exists()
    assert (CLEAN_APP_DIR / "grievance.html").is_file()
    assert "30 days" in clean_grievance or "30-day" in clean_grievance
    assert "grievance@example.com" in clean_grievance

    # Marker 7 (IN-DPDP-011): Date-of-birth and parental branch
    assert "dob" not in flawed_signup and "date of birth" not in flawed_signup.lower()
    assert "guardian" not in flawed_signup.lower()
    assert 'type="date"' in clean_signup
    assert "dob" in clean_signup
    assert "parental-branch" in clean_signup or "guardian" in clean_signup.lower()

    # Marker 8 (IN-DPDP-013 & IN-BP-003): Security configurations
    assert (FLAWED_APP_DIR / ".env").is_file()
    assert not (CLEAN_APP_DIR / ".env").exists()
    assert (CLEAN_APP_DIR / ".env.example").is_file()
    assert ".env" in (CLEAN_APP_DIR / ".gitignore").read_text(encoding="utf-8")

    # Verify git-ignore rules: clean-app/.env ignored, flawed-app/.env trackable
    import subprocess
    try:
        clean_res = subprocess.run(
            ["git", "check-ignore", "demo/clean-app/.env"],
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
        )
        assert clean_res.returncode == 0, "demo/clean-app/.env must be ignored by git"

        flawed_res = subprocess.run(
            ["git", "check-ignore", "demo/flawed-app/.env"],
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
        )
        assert flawed_res.returncode != 0, "demo/flawed-app/.env must be trackable (not ignored)"
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    assert "md5" in flawed_auth.lower()
    assert "argon2id" in clean_auth.lower()
    assert "md5" not in clean_auth.lower()

    assert "strict-transport-security" not in flawed_nginx.lower()
    assert "add_header strict-transport-security" in clean_nginx.lower()

    assert "allow read, write: if true;" in flawed_storage
    assert "allow read, write: if true;" not in clean_storage

    assert flawed_logging["logging"]["retention_days"] == 7
    assert clean_logging["logging"]["retention_days"] == 365

    # Marker 9 (IN-SPDI-001): Privacy policy and named Grievance Officer
    assert not (FLAWED_APP_DIR / "privacy.html").exists()
    assert (CLEAN_APP_DIR / "privacy.html").is_file()
    assert "Grievance Officer" in clean_privacy
    assert "grievance-officer@example.com" in clean_privacy
    assert "disclosure" in clean_privacy.lower()
    assert "security" in clean_privacy.lower()


def test_expected_findings_format_and_coverage():
    """Assert expected-findings.json contains all active check IDs for both apps with valid results."""
    assert EXPECTED_FINDINGS_PATH.is_file(), f"{EXPECTED_FINDINGS_PATH} must exist"

    data = json.loads(EXPECTED_FINDINGS_PATH.read_text(encoding="utf-8"))
    assert "flawed-app" in data, "expected-findings.json must contain 'flawed-app'"
    assert "clean-app" in data, "expected-findings.json must contain 'clean-app'"

    active_ids = extract_active_india_check_ids()
    assert len(active_ids) == 12, f"Expected 12 active check IDs, found {len(active_ids)}"

    allowed_results = {"met", "not-met", "informational", "needs-human"}

    for app_name in ("flawed-app", "clean-app"):
        app_findings: Dict[str, Dict[str, str]] = data[app_name]
        assert set(app_findings.keys()) == set(active_ids), (
            f"Findings for {app_name} do not match active checks exactly. "
            f"Missing: {set(active_ids) - set(app_findings.keys())}, "
            f"Extra: {set(app_findings.keys()) - set(active_ids)}"
        )

        for cid, finding in app_findings.items():
            assert "result" in finding, f"Finding for {app_name}/{cid} must specify 'result'"
            assert finding["result"] in allowed_results, (
                f"Result '{finding['result']}' for {app_name}/{cid} not in {allowed_results}"
            )
            assert "reason" in finding and len(finding["reason"].strip()) > 0, (
                f"Finding for {app_name}/{cid} must have a non-empty reason"
            )
            # Reason must point to the file that causes it
            reason = finding["reason"]
            assert any(ext in reason for ext in [".html", ".js", ".conf", ".rules", ".json", ".env"]), (
                f"Reason for {app_name}/{cid} must point to a file: '{reason}'"
            )

        # Specific constraints from prompt
        assert app_findings["IN-BP-004"]["result"] == "informational", (
            f"IN-BP-004 must be 'informational' for {app_name}"
        )
        assert app_findings["IN-DPDP-011"]["result"] == "needs-human", (
            f"IN-DPDP-011 must be 'needs-human' for {app_name}"
        )

    # Flawed app checks (other than IN-BP-004 and IN-DPDP-011) should be not-met
    for cid, finding in data["flawed-app"].items():
        if cid not in ("IN-BP-004", "IN-DPDP-011"):
            assert finding["result"] == "not-met", f"Flawed app check {cid} expected 'not-met', got '{finding['result']}'"

    # Clean app checks (other than IN-BP-004 and IN-DPDP-011) should be met
    for cid, finding in data["clean-app"].items():
        if cid not in ("IN-BP-004", "IN-DPDP-011"):
            assert finding["result"] == "met", f"Clean app check {cid} expected 'met', got '{finding['result']}'"


def test_demo_readme():
    """Assert demo/README.md documents fixtures, local serving, and compliance warnings."""
    readme_path = DEMO_DIR / "README.md"
    assert readme_path.is_file(), "demo/README.md must exist"

    content = readme_path.read_text(encoding="utf-8")
    assert "python -m http.server" in content, "README must mention 'python -m http.server'"
    assert "not legal advice" in content.lower(), "README must state not legal advice"
    assert "not" in content.lower() and "compliant" in content.lower(), (
        "README must warn that fixtures are not examples of compliant software"
    )
