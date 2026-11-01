"""
Tests for Technical Security Baseline and Safeguards Analyzer (Task 8)
scripts/baseline.py, IN-DPDP-013, and IN-BP-003.

Asserts:
- Synthetic tests with tmp_path covering each signal kind individually and in combination.
- Boundary conditions:
  * Committed secrets redaction and non-leakage of secret values.
  * .env* files never print line text snippets.
  * Non-env files redact lines with KEY/SECRET/TOKEN/PASSWORD/PASS = non-empty value.
  * .env.example / .env.sample templates are not flagged as committed secrets.
  * Password hashing proximity rule (flag md5/sha1/sha256 within 3 lines of password/passwd/pwd).
  * Checksum usage (createHash('sha256') without password keyword) is NOT flagged.
  * Modern hashing (argon2, argon2id, bcrypt, scrypt, pbkdf2) recorded as recommended.
  * HSTS header present vs "no Strict-Transport-Security header found in <file>".
  * Storage rules public write vs restricted access conditions.
  * Logging retention extraction (days reported without verdict words).
  * Backup encryption detection (encrypted vs unencrypted).
  * Line caps: IN-DPDP-013 max 5 lines per category + overflow line; IN-BP-003 advisories never capped.
  * Empty directory / 0 recognised files: IN-DPDP-013 is unclear; IN-BP-003 is informational with
    'no recognised files found; nothing assessed' and no 'no advisory findings' line.
  * Suggested fix on IN-BP-003 lists only fixes for detected advisories; None if 0 advisories.
  * Skip rules (.git, node_modules, reports, dist, build, __pycache__, files > 1 MB, symlinks).
  * Paths use forward slashes and no drive letters.
  * Prohibited words ('compliant', 'secure') never appear in findings output.
- Oracle tests on demo/clean-app and demo/flawed-app:
  * IN-DPDP-013 result is always needs-human.
  * IN-BP-003 result is always informational.
  * Planted fake secrets never leak into findings JSON.
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

from scripts.baseline import MAX_FILE_SIZE, evaluate_baseline

CLEAN_APP_DIR = WORKSPACE_ROOT / "demo" / "clean-app"
FLAWED_APP_DIR = WORKSPACE_ROOT / "demo" / "flawed-app"
EXPECTED_FINDINGS_PATH = WORKSPACE_ROOT / "tests" / "expected-findings.json"

PROHIBITED_WORDS = [
    re.compile(r"\bcompliant\b", re.IGNORECASE),
    re.compile(r"\bsecure\b", re.IGNORECASE),
]


def assert_no_prohibited_words(text: str) -> None:
    """Assert that prohibited words do not appear in output text."""
    for pattern in PROHIBITED_WORDS:
        m = pattern.search(text)
        assert m is None, f"Prohibited word '{m.group(0)}' found in output"


# ---------------------------------------------------------------------------
# Synthetic Unit Tests
# ---------------------------------------------------------------------------

def test_empty_directory_or_unrecognised_files(tmp_path: Path):
    """
    When no recognised files are scanned:
    - IN-DPDP-013 is unclear.
    - IN-BP-003 is informational with evidence 'no recognised files found; nothing assessed'.
    - No 'no advisory findings' line in IN-BP-003.
    - suggested_fix is None or not present.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "index.html").write_text("<html><body>Hello</body></html>", encoding="utf-8")
    (app_dir / "styles.css").write_text("body { color: red; }", encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    # IN-DPDP-013
    dpdp = findings["IN-DPDP-013"]
    assert dpdp["result"] == "unclear"
    assert dpdp["evidence"] == ["no recognised files found; nothing assessed"]
    assert "This is not an assessment of the application's security." in dpdp["notes"]

    # IN-BP-003
    bp = findings["IN-BP-003"]
    assert bp["result"] == "informational"
    assert bp["evidence"] == ["no recognised files found; nothing assessed"]
    assert not any("no advisory findings" in ev for ev in bp["evidence"])
    assert "suggested_fix" not in bp
    assert "This is not an assessment of the application's security." in bp["notes"]


def test_committed_secrets_redaction_and_leak_prevention(tmp_path: Path):
    """
    Secrets rule 1:
    - Never print snippets from .env* files.
    - Elsewhere, replace any snippet from a line having KEY, SECRET, TOKEN, PASSWORD or PASS
      followed by = or : and a non-empty value with '<line redacted: possible secret>'.
    - Never put a secret value in output, notes, errors or tracebacks.
    - Planted values never appear in findings JSON or assertion messages.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    secret_env_val = "SECRET_VAL_ENV_987654321"
    secret_js_val = "SECRET_VAL_JS_123456789"

    # .env file with planted secret
    (app_dir / ".env").write_text(
        f"# Env config\nAPI_SECRET_KEY={secret_env_val}\nPORT=3000\n",
        encoding="utf-8",
    )

    # auth.js file with hardcoded token
    (app_dir / "auth.js").write_text(
        f'const AUTH_TOKEN = "{secret_js_val}";\nfunction getAuth() {{ return AUTH_TOKEN; }}\n',
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    json_output = json.dumps(doc)

    # Leak checks without embedding secrets in failure messages
    if secret_env_val in json_output:
        pytest.fail("Planted .env secret value leaked into findings output")
    if secret_js_val in json_output:
        pytest.fail("Planted auth.js secret value leaked into findings output")

    findings = {f["check_id"]: f for f in doc["findings"]}
    dpdp = findings["IN-DPDP-013"]
    assert dpdp["result"] == "needs-human"

    evidence = dpdp["evidence"]
    # Check that .env key line is redacted and snippet is not printed
    env_matches = [ev for ev in evidence if ".env" in ev]
    assert len(env_matches) >= 1
    assert any("<line redacted: possible secret>" in ev for ev in env_matches)
    # Check that auth.js secret line is redacted
    auth_matches = [ev for ev in evidence if "auth.js" in ev and "committed secrets" in ev]
    assert len(auth_matches) >= 1
    assert any("<line redacted: possible secret>" in ev for ev in auth_matches)


def test_env_templates_not_flagged(tmp_path: Path):
    """
    Files matching .env.example, .env.sample, .env.template are templates,
    not committed secrets, and should not be flagged.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    (app_dir / ".env.example").write_text("API_KEY=\nDB_URL=\n", encoding="utf-8")
    (app_dir / ".env.sample").write_text("API_KEY=\n", encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    dpdp = findings["IN-DPDP-013"]
    assert dpdp["result"] == "unclear"  # No recognised files scanned
    assert dpdp["evidence"] == ["no recognised files found; nothing assessed"]


def test_weak_hashing_password_proximity_rules(tmp_path: Path):
    """
    Weak hashing rule 3:
    Flag md5/sha1/sha256 only when password|passwd|pwd appears on the same line or within 3 lines.
    Auth code files = filename contains auth, login, password, user, account, signup, or session.
    IN-DPDP-013 label: 'access control (authentication): password hashing found: <alg>'.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # 1. md5 with password on same line
    (app_dir / "user_auth.js").write_text(
        "const md5 = require('md5');\n"
        "function hash(password) { return md5(password); }\n",
        encoding="utf-8",
    )

    # 2. sha1 with passwd 2 lines earlier
    (app_dir / "login.py").write_text(
        "def check_user(user, passwd):\n"
        "    salt = 'fixed_salt'\n"
        "    h = hashlib.sha1((passwd + salt).encode()).hexdigest()\n"
        "    return h\n",
        encoding="utf-8",
    )

    # 3. sha256 with pwd 3 lines later
    (app_dir / "password_util.ts").write_text(
        "function hashToken() {\n"
        "  const h = crypto.createHash('sha256');\n"
        "  // helper comment\n"
        "  // another line\n"
        "  const pwd = getUserInput();\n"
        "  return h.update(pwd).digest('hex');\n"
        "}\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    dpdp = findings["IN-DPDP-013"]
    bp = findings["IN-BP-003"]

    # IN-DPDP-013: no verdict words, exact format
    dpdp_evidence = dpdp["evidence"]
    assert any("access control (authentication): password hashing found: md5" in ev for ev in dpdp_evidence)
    assert any("access control (authentication): password hashing found: sha1" in ev for ev in dpdp_evidence)
    assert any("access control (authentication): password hashing found: sha256" in ev for ev in dpdp_evidence)
    for ev in dpdp_evidence:
        if "password hashing found:" in ev:
            assert "weak" not in ev.lower()
            assert "strong" not in ev.lower()

    # IN-BP-003: advisories for weak hashing
    bp_evidence = bp["evidence"]
    assert any("advisory: weak password hashing algorithm 'md5' detected in user_auth.js" in ev for ev in bp_evidence)
    assert any("advisory: weak password hashing algorithm 'sha1' detected in login.py" in ev for ev in bp_evidence)
    assert any("advisory: weak password hashing algorithm 'sha256' detected in password_util.ts" in ev for ev in bp_evidence)


def test_sha256_checksum_not_flagged(tmp_path: Path):
    """
    Test that createHash('sha256') for a file checksum is NOT flagged when
    no password keyword is within 3 lines.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    (app_dir / "auth_upload.js").write_text(
        "const crypto = require('crypto');\n"
        "function computeFileDigest(fileData) {\n"
        "  const hash = crypto.createHash('sha256');\n"
        "  hash.update(fileData);\n"
        "  return hash.digest('hex');\n"
        "}\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp = findings["IN-BP-003"]
    # Should NOT have any advisory for sha256
    assert not any("weak password hashing" in ev for ev in bp["evidence"])
    assert any("no advisory findings across 1 scanned files" in ev for ev in bp["evidence"])


def test_strong_hashing_algorithms(tmp_path: Path):
    """
    Test that modern hashing baselines (argon2, argon2id, bcrypt, scrypt, pbkdf2)
    are reported as informational in IN-BP-003 and access control in IN-DPDP-013.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    (app_dir / "user_auth.js").write_text(
        "const argon2 = require('argon2');\n"
        "async function hashPassword(password) {\n"
        "  return await argon2.hash(password, { type: argon2.argon2id });\n"
        "}\n",
        encoding="utf-8",
    )

    (app_dir / "login_service.py").write_text(
        "import bcrypt\n"
        "def hash_pwd(password):\n"
        "    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    # IN-DPDP-013
    dpdp_evidence = findings["IN-DPDP-013"]["evidence"]
    assert any("access control (authentication): password hashing found: argon2" in ev for ev in dpdp_evidence)
    assert any("access control (authentication): password hashing found: bcrypt" in ev for ev in dpdp_evidence)

    # IN-BP-003: 0 advisories, informational lines present
    bp = findings["IN-BP-003"]
    assert not any(ev.startswith("advisory:") for ev in bp["evidence"])
    assert any("informational: recommended password hashing algorithm 'argon2" in ev for ev in bp["evidence"])
    assert any("informational: recommended password hashing algorithm 'bcrypt' configured in login_service.py" in ev for ev in bp["evidence"])
    assert "suggested_fix" not in bp


def test_hsts_presence_and_absence(tmp_path: Path):
    """
    Wording rule 4:
    - 'no Strict-Transport-Security header found in <file>' (not 'missing').
    - Notes: 'HSTS may be set elsewhere (included files, CDN, load balancer).'
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Nginx config lacking HSTS
    (app_dir / "nginx.conf").write_text(
        "server {\n"
        "    listen 443 ssl;\n"
        "    server_name example.test;\n"
        "    ssl_protocols TLSv1.3;\n"
        "}\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    dpdp = findings["IN-DPDP-013"]
    bp = findings["IN-BP-003"]

    expected_line = "no Strict-Transport-Security header found in nginx.conf"
    assert any(expected_line in ev for ev in dpdp["evidence"])
    assert any(f"advisory: {expected_line}" in ev for ev in bp["evidence"])
    # Ensure forbidden word 'missing' was not used for HSTS
    assert not any("missing Strict-Transport-Security" in ev.lower() for ev in bp["evidence"])

    assert "HSTS may be set elsewhere (included files, CDN, load balancer)." in dpdp["notes"]
    assert "HSTS may be set elsewhere (included files, CDN, load balancer)." in bp["notes"]


def test_storage_rules_public_write_vs_restricted(tmp_path: Path):
    """
    Storage rules:
    - Public write matches allow write: if true;
    - Restricted rules match request.auth != null or if false;
    """
    # 1. Permissive storage rules
    app_dir_bad = tmp_path / "app_bad"
    app_dir_bad.mkdir()
    (app_dir_bad / "storage.rules").write_text(
        "rules_version = '2';\n"
        "service firebase.storage {\n"
        "  match /b/{bucket}/o {\n"
        "    match /{allPaths=**} {\n"
        "      allow read, write: if true;\n"
        "    }\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    doc_bad = evaluate_baseline(app_dir_bad)
    bp_bad = doc_bad["findings"][1]
    assert any("advisory: public write access permitted in storage rules: storage.rules:5" in ev for ev in bp_bad["evidence"])

    # 2. Restricted storage rules
    app_dir_good = tmp_path / "app_good"
    app_dir_good.mkdir()
    (app_dir_good / "storage.rules").write_text(
        "rules_version = '2';\n"
        "service firebase.storage {\n"
        "  match /b/{bucket}/o {\n"
        "    match /users/{userId}/{allPaths=**} {\n"
        "      allow read, write: if request.auth != null;\n"
        "    }\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    doc_good = evaluate_baseline(app_dir_good)
    bp_good = doc_good["findings"][1]
    assert not any(ev.startswith("advisory:") for ev in bp_good["evidence"])
    assert any("informational: storage access restricted by authorization conditions in storage.rules:5" in ev for ev in bp_good["evidence"])


def test_log_retention_extraction(tmp_path: Path):
    """
    Log retention:
    - IN-DPDP-013 reports detected retention days under retention settings without pass/fail judgment.
    - Notes state r.6(1)(e) exception and r.8(3) scope.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "logging.json").write_text(
        '{\n  "retention_days": 180,\n  "level": "info"\n}\n',
        encoding="utf-8",
    )
    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    dpdp = findings["IN-DPDP-013"]
    assert any("retention settings: log retention configured for 180 days (logging.json:2)" in ev for ev in dpdp["evidence"])
    assert "r.6(1)(e) exception" in dpdp["notes"]
    assert "r.8(3) scope" in dpdp["notes"]


def test_backup_continuity_detection(tmp_path: Path):
    """
    Backup configuration:
    - Encrypted backup -> informational in IN-BP-003, backups/continuity in IN-DPDP-013.
    - Unencrypted backup -> advisory in IN-BP-003, backups/continuity in IN-DPDP-013.
    """
    # 1. Encrypted backup
    app_enc = tmp_path / "app_enc"
    app_enc.mkdir()
    (app_enc / "backup.sh").write_text(
        "tar -czf - /data | gpg --encrypt --recipient admin@example.com > /backup/data.tar.gz.gpg\n",
        encoding="utf-8",
    )
    doc_enc = evaluate_baseline(app_enc)
    assert any("backups/continuity: encrypted backup configuration found (backup.sh:1)" in ev for ev in doc_enc["findings"][0]["evidence"])
    assert any("informational: encrypted backup configuration detected in backup.sh:1" in ev for ev in doc_enc["findings"][1]["evidence"])

    # 2. Unencrypted backup
    app_plain = tmp_path / "app_plain"
    app_plain.mkdir()
    (app_plain / "backup.sh").write_text(
        "tar -czf /backup/data.tar.gz /data\n",
        encoding="utf-8",
    )
    doc_plain = evaluate_baseline(app_plain)
    assert any("backups/continuity: unencrypted backup configuration found (backup.sh)" in ev for ev in doc_plain["findings"][0]["evidence"])
    assert any("advisory: unencrypted backup configuration detected in backup.sh" in ev for ev in doc_plain["findings"][1]["evidence"])


def test_line_caps_rule(tmp_path: Path):
    """
    Line caps rule 6:
    - IN-BP-003 advisory lines are never capped.
    - IN-DPDP-013: max 5 lines per category; if more, append '<N> more matches not shown (total <N>)'.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Generate an auth.js with 8 weak hashing lines
    lines = ["const crypto = require('crypto');\nfunction hashStuff(password) {\n"]
    for i in range(8):
        lines.append(f"  const h{i} = crypto.createHash('md5').update(password).digest('hex');\n")
    lines.append("}\n")
    (app_dir / "auth.js").write_text("".join(lines), encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    # IN-DPDP-013 access control has 8 matches -> exactly 5 lines + 1 overflow line
    dpdp_evidence = findings["IN-DPDP-013"]["evidence"]
    ac_lines = [ev for ev in dpdp_evidence if ev.startswith("access control")]
    assert len(ac_lines) == 6
    assert "access control: 3 more matches not shown (total 8)" in ac_lines[-1]

    # IN-BP-003 advisory lines are NEVER capped -> all 8 lines present
    bp_evidence = findings["IN-BP-003"]["evidence"]
    adv_lines = [ev for ev in bp_evidence if ev.startswith("advisory:")]
    assert len(adv_lines) == 8


def test_suggested_fix_conditional_rule(tmp_path: Path):
    """
    Suggested fix rule 7:
    suggested_fix on IN-BP-003 lists only fixes for advisories actually detected.
    None / omitted if 0 advisories detected.
    """
    # 1. Zero advisories
    app_clean = tmp_path / "app_clean"
    app_clean.mkdir()
    (app_clean / "auth.js").write_text(
        "const argon2 = require('argon2');\n"
        "async function hash(password) { return await argon2.hash(password, { type: argon2.argon2id }); }\n",
        encoding="utf-8",
    )
    doc_clean = evaluate_baseline(app_clean)
    assert "suggested_fix" not in doc_clean["findings"][1]

    # 2. Only weak hashing advisory
    app_hash = tmp_path / "app_hash"
    app_hash.mkdir()
    (app_hash / "auth.js").write_text(
        "const crypto = require('crypto');\n"
        "function hash(password) { return crypto.createHash('md5').update(password).digest('hex'); }\n",
        encoding="utf-8",
    )
    doc_hash = evaluate_baseline(app_hash)
    fix_text = doc_hash["findings"][1]["suggested_fix"]
    assert "Argon2id or bcrypt" in fix_text
    assert "Strict-Transport-Security" not in fix_text
    assert "storage rules" not in fix_text
    assert "backup" not in fix_text


def test_skip_rules_and_symlinks(tmp_path: Path):
    """
    Scanner skip rules:
    - Skips .git, node_modules, reports, dist, build, __pycache__.
    - Skips files > 1 MB.
    - Skips symlinked files.
    - Dynamic counts of files_scanned and files_skipped.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Ignored directory
    nm_dir = app_dir / "node_modules"
    nm_dir.mkdir()
    (nm_dir / "auth.js").write_text("const crypto = require('crypto');", encoding="utf-8")

    # Large file (> 1 MB)
    large_file = app_dir / "large_auth.js"
    large_file.write_text("x" * (MAX_FILE_SIZE + 100), encoding="utf-8")

    # Regular file
    (app_dir / "auth.js").write_text(
        "const argon2 = require('argon2');\n"
        "async function hash(password) { return await argon2.hash(password, { type: argon2.argon2id }); }\n",
        encoding="utf-8",
    )

    # Symlinked file
    symlink_file = app_dir / "sym_auth.js"
    try:
        symlink_file.symlink_to(app_dir / "auth.js")
    except (OSError, NotImplementedError):
        pass  # On Windows without developer mode symlink creation may require privilege

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}
    notes = findings["IN-DPDP-013"]["notes"]

    assert "files scanned (1)" in notes
    # Large file was skipped, symlink was skipped if created
    assert "files skipped" in notes


def test_forward_slashes_and_no_drive_letters(tmp_path: Path):
    """Evidence paths must always use forward slashes and never include drive letters."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    sub = app_dir / "nested" / "deep"
    sub.mkdir(parents=True)
    (sub / "auth.js").write_text(
        "const crypto = require('crypto');\n"
        "function hash(password) { return crypto.createHash('md5').update(password).digest('hex'); }\n",
        encoding="utf-8",
    )
    doc = evaluate_baseline(app_dir)
    for f in doc["findings"]:
        for ev in f["evidence"]:
            assert "\\" not in ev
            assert not re.search(r"^[A-Za-z]:", ev)


def test_prohibited_words_across_findings(tmp_path: Path):
    """Neither 'compliant' nor 'secure' may appear in findings output."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "auth.js").write_text(
        "const argon2 = require('argon2');\n"
        "async function hash(password) { return await argon2.hash(password, { type: argon2.argon2id }); }\n",
        encoding="utf-8",
    )
    (app_dir / "nginx.conf").write_text(
        "server { listen 443 ssl; add_header Strict-Transport-Security 'max-age=31536000'; }\n",
        encoding="utf-8",
    )
    doc = evaluate_baseline(app_dir)
    json_text = json.dumps(doc)
    assert_no_prohibited_words(json_text)


# ---------------------------------------------------------------------------
# Oracle Tests on Demo Applications
# ---------------------------------------------------------------------------

def test_oracle_demo_clean_app():
    """
    Evaluate demo/clean-app:
    - IN-DPDP-013: result is needs-human (ALWAYS).
    - IN-BP-003: result is informational (ALWAYS), 0 advisory findings, suggested_fix is omitted.
    - Prohibited words absent.
    """
    assert CLEAN_APP_DIR.is_dir()
    doc = evaluate_baseline(CLEAN_APP_DIR)
    json_text = json.dumps(doc, indent=2)

    assert_no_prohibited_words(json_text)

    findings = {f["check_id"]: f for f in doc["findings"]}

    # IN-DPDP-013
    dpdp = findings["IN-DPDP-013"]
    assert dpdp["result"] == "needs-human"
    dpdp_ev = dpdp["evidence"]
    assert any("encryption/transport: Strict-Transport-Security header configured" in ev for ev in dpdp_ev)
    assert any("access control (authentication): password hashing found: argon2" in ev for ev in dpdp_ev)
    assert any("retention settings: log retention configured for 365 days" in ev for ev in dpdp_ev)
    assert "committed secrets: no committed secrets detected in scanned files" in dpdp_ev

    # IN-BP-003
    bp = findings["IN-BP-003"]
    assert bp["result"] == "informational"
    assert "suggested_fix" not in bp
    bp_ev = bp["evidence"]
    assert not any(ev.startswith("advisory:") for ev in bp_ev)
    assert any("no advisory findings across 4 scanned files" in ev for ev in bp_ev)
    assert any("informational: recommended password hashing algorithm 'argon2" in ev for ev in bp_ev)
    assert any("informational: Strict-Transport-Security header configured" in ev for ev in bp_ev)
    assert any("informational: log retention configured for 365 days" in ev for ev in bp_ev)


def test_oracle_demo_flawed_app():
    """
    Evaluate demo/flawed-app:
    - IN-DPDP-013: result is needs-human (ALWAYS).
    - IN-BP-003: result is informational (ALWAYS), contains advisories for md5, no HSTS, public write.
    - Planted fake secrets never leak into output or assertion messages.
    - Prohibited words absent.
    """
    assert FLAWED_APP_DIR.is_dir()
    doc = evaluate_baseline(FLAWED_APP_DIR)
    json_text = json.dumps(doc, indent=2)

    assert_no_prohibited_words(json_text)

    # Read planted secret to test leak prevention
    planted_env = (FLAWED_APP_DIR / ".env").read_text(encoding="utf-8")
    m = re.search(r"API_SECRET_KEY=([^\r\n]+)", planted_env)
    assert m is not None
    planted_val = m.group(1).strip()

    if planted_val in json_text:
        pytest.fail("Planted demo fake secret leaked into findings output")

    findings = {f["check_id"]: f for f in doc["findings"]}

    # IN-DPDP-013
    dpdp = findings["IN-DPDP-013"]
    assert dpdp["result"] == "needs-human"
    dpdp_ev = dpdp["evidence"]
    assert any("no Strict-Transport-Security header found in nginx.conf" in ev for ev in dpdp_ev)
    assert any("access control (authentication): password hashing found: md5" in ev for ev in dpdp_ev)
    assert any("access control: storage rules permit public write access" in ev for ev in dpdp_ev)
    assert any("retention settings: log retention configured for 7 days" in ev for ev in dpdp_ev)
    assert any(".env:" in ev and "<line redacted: possible secret>" in ev for ev in dpdp_ev)

    # IN-BP-003
    bp = findings["IN-BP-003"]
    assert bp["result"] == "informational"
    assert "suggested_fix" in bp
    bp_ev = bp["evidence"]
    assert any("advisory: weak password hashing algorithm 'md5'" in ev for ev in bp_ev)
    assert any("advisory: no Strict-Transport-Security header found in nginx.conf" in ev for ev in bp_ev)
    assert any("advisory: public write access permitted in storage rules" in ev for ev in bp_ev)

    fix = bp["suggested_fix"]
    assert "Argon2id or bcrypt" in fix
    assert "Strict-Transport-Security" in fix
    assert "storage rules" in fix


# ---------------------------------------------------------------------------
# CLI & Report Integration
# ---------------------------------------------------------------------------

def test_baseline_cli_and_report_rendering(tmp_path: Path):
    """
    Execute baseline.py CLI on demo/clean-app, output JSON, and render through
    scripts/report.py without error.
    """
    findings_json = tmp_path / "baseline-findings.json"

    # 1. Run CLI on clean-app
    proc = subprocess.run(
        [
            sys.executable,
            str(WORKSPACE_ROOT / "scripts" / "baseline.py"),
            str(CLEAN_APP_DIR),
            "--findings-out",
            str(findings_json),
        ],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"baseline.py CLI failed: {proc.stderr}"
    assert findings_json.is_file()

    doc = json.loads(findings_json.read_text(encoding="utf-8"))
    assert "scan" not in doc  # No top-level scan object
    assert len(doc["findings"]) == 2
    check_ids = [f["check_id"] for f in doc["findings"]]
    assert "IN-DPDP-013" in check_ids
    assert "IN-BP-003" in check_ids

    # 2. Render clean-app findings through report.py
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
    assert report_proc.returncode == 0, f"report.py failed on clean baseline findings: {report_proc.stderr}"

    # 3. Run CLI on flawed-app
    flawed_findings_json = tmp_path / "flawed-baseline-findings.json"
    proc_flawed = subprocess.run(
        [
            sys.executable,
            str(WORKSPACE_ROOT / "scripts" / "baseline.py"),
            str(FLAWED_APP_DIR),
            "--findings-out",
            str(flawed_findings_json),
        ],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc_flawed.returncode == 0, f"baseline.py CLI failed on flawed app: {proc_flawed.stderr}"

    # 4. Render flawed-app findings through report.py
    report_proc_flawed = subprocess.run(
        [
            sys.executable,
            str(WORKSPACE_ROOT / "scripts" / "report.py"),
            "--findings",
            str(flawed_findings_json),
            "--jurisdiction",
            "india",
            "--today",
            "2026-10-29",
        ],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
    )
    assert report_proc_flawed.returncode == 0, f"report.py failed on flawed baseline findings: {report_proc_flawed.stderr}"
