"""
Tests for Technical Security Baseline and Safeguards Analyzer (Task 8 & 10)
scripts/baseline.py, IN-DPDP-013, and IN-BP-003.

Asserts:
- Synthetic tests with tmp_path covering each signal kind individually and in combination.
- Boundary conditions:
  * Committed secrets redaction and non-leakage of secret values.
  * .env* files never print line text snippets.
  * .env handling: key name with non-placeholder, connection strings, other assignments count.
  * Placeholder values (changeme, your-token, xxx, <placeholder>, example) not flagged.
  * .env.example / templates excluded from scanning.
  * Non-secret code assignments (e.g. const password = req.body.password) not flagged.
  * Connection string key names extracted (DB_URI), fallback to 'connection string' (never 'SECRET').
  * Password hashing proximity rule and collapsed per-file format (lines X, Y, Z).
  * Checksum usage (createHash('sha256') without password keyword) is NOT flagged.
  * Modern hashing (argon2, argon2id, bcrypt, scrypt, pbkdf2) recorded as recommended.
  * HSTS header present vs "no Strict-Transport-Security header found" (no redundant "in <file>").
  * Storage rules public write vs restricted access conditions.
  * Logging retention extraction (days reported without verdict words).
  * Backup encryption detection (encrypted vs unencrypted).
  * Line caps: IN-DPDP-013 max 5 lines per category + overflow line; IN-BP-003 advisories never capped.
  * Empty directory / 0 recognised files: IN-DPDP-013 is unclear; IN-BP-003 is informational with
    'no recognised files found; nothing assessed' and no 'no advisory findings' line.
  * Suggested fix on IN-BP-003 is ONE line separated by '; ', listing only detected advisories.
  * Skip rules (.git, node_modules, reports, dist, build, __pycache__, files > 1 MB, symlinks).
  * Paths use forward slashes, line numbers where applicable, and no drive letters.
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

from scripts.baseline import (
    MAX_FILE_SIZE,
    evaluate_baseline,
    extract_secret_info,
    is_placeholder_value,
    is_secret_assignment,
)

CLEAN_APP_DIR = WORKSPACE_ROOT / "demo" / "clean-app"
FLAWED_APP_DIR = WORKSPACE_ROOT / "demo" / "flawed-app"
EXPECTED_FINDINGS_PATH = WORKSPACE_ROOT / "tests" / "expected-findings.json"

PROHIBITED_WORDS = [
    re.compile(r"\bcompliant\b", re.IGNORECASE),
    re.compile(r"\bsecure\b", re.IGNORECASE),
]

PATH_FIRST_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9_./-]+(?::\d+)?: (?:encryption/transport|access control(?: \(authentication\))?|access logging and monitoring|backups/continuity|retention settings|committed secrets|advisory|informational): .+"
    r"|no recognised files found; nothing assessed"
    r"|no advisory findings among the patterns checked \(\d+ scanned files\)"
    r"|[a-z/ ]+: (?:no (?:matching configuration|backup or continuity configuration|committed secrets) detected in scanned files|\d+ more matches not shown \(total \d+\)))$"
)


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


def test_is_secret_assignment_exclusions():
    """
    Verify is_secret_assignment correctly distinguishes variable assignments
    from hardcoded secret literals.
    """
    assert not is_secret_assignment("const password = req.body.password")
    assert not is_secret_assignment("password = input()")
    assert not is_secret_assignment("const token = getAuthToken();")
    assert not is_secret_assignment("let user_secret = session.secret;")
    assert not is_secret_assignment("// API_KEY = 'commented_out'")

    # Hardcoded secrets with quotes
    assert is_secret_assignment('const API_KEY = "my_planted_secret_12345"')
    assert is_secret_assignment("DATABASE_URL = 'postgres://user:pass@localhost:5432/db'")


def test_placeholder_values():
    """Verify is_placeholder_value recognises common development placeholders."""
    # Placeholders: must return True
    assert is_placeholder_value("")
    assert is_placeholder_value("null")
    assert is_placeholder_value("none")
    assert is_placeholder_value("true")
    assert is_placeholder_value("false")
    assert is_placeholder_value("undefined")
    assert is_placeholder_value("changeme")
    assert is_placeholder_value("change-me")
    assert is_placeholder_value("todo")
    assert is_placeholder_value("example")
    assert is_placeholder_value("your-token-here")
    assert is_placeholder_value("your_api_key")
    assert is_placeholder_value("<placeholder>")
    assert is_placeholder_value("<INSERT_KEY_HERE>")
    assert is_placeholder_value("xxx")
    assert is_placeholder_value("XXXXXX")

    # Real-looking secrets: must return False
    assert not is_placeholder_value("FAKE_KEY_DO_NOT_USE_0000")
    assert not is_placeholder_value("sk-live-9876543210abcdef")
    assert not is_placeholder_value("prod_db_secret_pass_123")


def test_env_placeholders_and_committed_secrets(tmp_path: Path):
    """
    Tests:
    - SECRET=changeme, TOKEN=your-token, PASS=xxx, PASSWORD=<placeholder>, KEY=example
      are NOT flagged as committed secrets.
    - API_SECRET_KEY=FAKE_KEY_DO_NOT_USE_0000 IS flagged.
    - DATABASE_URL=postgres://user:password@localhost:5432/db IS flagged with credential.
    - Other non-secret assignments summarized as 'N other assignments (keys and values not shown)'.
    - Planted values never appear in output JSON or assertion messages.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    secret_key_val = "FAKE_KEY_DO_NOT_USE_0000"
    db_pass_val = "SECRET_DB_PASS_456"

    env_content = (
        "# Configuration\n"
        "SECRET=changeme\n"
        "TOKEN=your-token\n"
        "PASS=xxx\n"
        "PASSWORD=<placeholder>\n"
        "KEY=example\n"
        f"API_SECRET_KEY={secret_key_val}\n"
        f"DATABASE_URL=postgres://appuser:{db_pass_val}@localhost:5432/appdb\n"
        "PORT=3000\n"
    )
    (app_dir / ".env").write_text(env_content, encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    json_output = json.dumps(doc)

    # Secret non-leakage
    assert secret_key_val not in json_output
    assert db_pass_val not in json_output

    findings = {f["check_id"]: f for f in doc["findings"]}
    dpdp = findings["IN-DPDP-013"]
    assert dpdp["result"] == "needs-human"

    evidence = dpdp["evidence"]
    # API_SECRET_KEY flagged
    assert any(".env:7: committed secrets: committed secret in API_SECRET_KEY (value not shown)" in ev for ev in evidence)
    # DATABASE_URL connection string flagged
    assert any(".env:8: committed secrets: committed credential in connection string for DATABASE_URL (value not shown)" in ev for ev in evidence)
    # 6 other assignments: SECRET, TOKEN, PASS, PASSWORD, KEY, PORT
    assert any(".env: committed secrets: committed environment file with 6 other assignments (keys and values not shown)" in ev for ev in evidence)


def test_env_example_with_assignments_produces_no_committed_secrets(tmp_path: Path):
    """
    Verify .env.example with assignments produces no committed-secrets evidence
    other than the 'nothing found' line.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    planted_secret = "SECRET_KEY_NOT_COMMITTED_888"
    (app_dir / ".env.example").write_text(
        f"API_SECRET_KEY={planted_secret}\nDATABASE_URL=postgres://admin:pass@db:5432/test\n",
        encoding="utf-8",
    )
    # Include another recognised file so files_scanned > 0
    (app_dir / "nginx.conf").write_text(
        "server {\n    listen 443 ssl;\n    add_header Strict-Transport-Security 'max-age=31536000';\n}\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    json_output = json.dumps(doc)

    # Secret non-leakage
    assert planted_secret not in json_output

    findings = {f["check_id"]: f for f in doc["findings"]}
    dpdp = findings["IN-DPDP-013"]

    # committed secrets category must report nothing found
    assert "committed secrets: no committed secrets detected in scanned files" in dpdp["evidence"]
    assert not any(".env.example" in ev for ev in dpdp["evidence"])


def test_code_connection_string_key_name(tmp_path: Path):
    """
    Key name in auth code:
    - Assignment: const DB_URI = "postgres://..." -> take DB_URI.
    - Assignment: const connection_string = "mongodb://..." -> take connection_string (never 'SECRET').
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    planted_conn = "SECRET_PASS_CONN_999"
    (app_dir / "auth.js").write_text(
        f'const DB_URI = "postgres://appuser:{planted_conn}@localhost:5432/mydb";\n'
        f'const connection_string = "mongodb://root:{planted_conn}@127.0.0.1:27017/admin";\n',
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    json_output = json.dumps(doc)

    # Leak check
    assert planted_conn not in json_output

    dpdp = doc["findings"][0]
    evidence = dpdp["evidence"]

    # 1. Takes key name from assignment
    assert any("auth.js:1: committed secrets: committed credential in connection string for DB_URI (value not shown)" in ev for ev in evidence)
    # 2. Takes key name connection_string
    assert any("auth.js:2: committed secrets: committed credential in connection string for connection_string (value not shown)" in ev for ev in evidence)
    # Never falls back to 'SECRET'
    assert not any("for SECRET" in ev for ev in evidence)


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


def test_planted_value_non_leakage_across_code_and_web_config(tmp_path: Path):
    """
    Planted fake secret values in auth code, web config, and container config
    never leak into findings JSON, notes, or assertion messages.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    auth_sec_val = "SECRET_VAL_AUTH_CODE_123456"
    auth_conn_pass = "SECRET_VAL_CONN_PASS_654321"
    nginx_sec_val = "SECRET_VAL_NGINX_CONF_789012"
    compose_sec_val = "SECRET_VAL_DOCKER_778899"

    # auth.js file with hardcoded token and connection string
    (app_dir / "auth.js").write_text(
        f'const AUTH_TOKEN = "{auth_sec_val}";\n'
        f'const DB_URI = "postgres://appuser:{auth_conn_pass}@localhost:5432/mydb";\n',
        encoding="utf-8",
    )
    # web config
    (app_dir / "nginx.conf").write_text(
        f'# Server config\nSECRET_KEY = "{nginx_sec_val}";\n',
        encoding="utf-8",
    )
    # container config
    (app_dir / "docker-compose.yml").write_text(
        f'version: "3"\nservices:\n  web:\n    API_KEY: "{compose_sec_val}"\n',
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    json_output = json.dumps(doc)

    # Leak checks without embedding secrets in failure messages
    if auth_sec_val in json_output:
        pytest.fail("Planted auth.js secret value leaked into findings output")
    if auth_conn_pass in json_output:
        pytest.fail("Planted auth.js connection string password leaked into findings output")
    if nginx_sec_val in json_output:
        pytest.fail("Planted nginx.conf secret value leaked into findings output")
    if compose_sec_val in json_output:
        pytest.fail("Planted docker-compose.yml secret value leaked into findings output")

    findings = {f["check_id"]: f for f in doc["findings"]}
    dpdp = findings["IN-DPDP-013"]
    assert dpdp["result"] == "needs-human"

    evidence = dpdp["evidence"]
    assert any("auth.js:1: committed secrets: committed secret in AUTH_TOKEN (value not shown)" in ev for ev in evidence)
    assert any("auth.js:2: committed secrets: committed credential in connection string for DB_URI (value not shown)" in ev for ev in evidence)
    assert any("nginx.conf:2: committed secrets: committed secret in SECRET_KEY (value not shown)" in ev for ev in evidence)
    assert any("docker-compose.yml:4: committed secrets: committed secret in API_KEY (value not shown)" in ev for ev in evidence)


def test_weak_hashing_password_proximity_and_collapsed_lines(tmp_path: Path):
    """
    Weak hashing rule 3 & collapsed format:
    - Flag md5/sha1/sha256 only when password|passwd|pwd appears on same line or within 3 lines.
    - Format IN-DPDP-013: '<path>: access control (authentication): password hashing found: <alg> (lines X, Y, Z)'.
    - Format IN-BP-003: '<path>: advisory: weak password hashing algorithm '<alg>' detected (lines X, Y, Z)'.
    - Sorted ascending line numbers.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # user_auth.js: md5 on line 2, password on line 2
    (app_dir / "user_auth.js").write_text(
        "const md5 = require('md5');\n"
        "function hash(password) { return md5(password); }\n",
        encoding="utf-8",
    )

    # login.py: sha1 on line 4, passwd on line 1
    (app_dir / "login.py").write_text(
        "def check_user(user, passwd):\n"
        "    salt = 'fixed_salt'\n"
        "    # line 3\n"
        "    return hashlib.sha1((passwd + salt).encode()).hexdigest()\n",
        encoding="utf-8",
    )

    # Multi-line weak hashing: auth_multi.js with md5 on lines 3 and 7
    (app_dir / "auth_multi.js").write_text(
        "// Multi-hashing module\n"
        "function hashPassword(password) {\n"
        "  const h1 = crypto.createHash('md5').update(password).digest('hex');\n"
        "  return h1;\n"
        "}\n"
        "function verifyPassword(password) {\n"
        "  const h2 = crypto.createHash('md5').update(password).digest('hex');\n"
        "  return h2;\n"
        "}\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    dpdp = findings["IN-DPDP-013"]
    bp = findings["IN-BP-003"]

    dpdp_evidence = dpdp["evidence"]
    assert any("user_auth.js: access control (authentication): password hashing found: md5 (lines 1, 2)" in ev for ev in dpdp_evidence)
    assert any("login.py: access control (authentication): password hashing found: sha1 (line 4)" in ev for ev in dpdp_evidence)
    assert any("auth_multi.js: access control (authentication): password hashing found: md5 (lines 3, 7)" in ev for ev in dpdp_evidence)

    bp_evidence = bp["evidence"]
    assert any("user_auth.js: advisory: weak password hashing algorithm 'md5' detected (lines 1, 2)" in ev for ev in bp_evidence)
    assert any("login.py: advisory: weak password hashing algorithm 'sha1' detected (line 4)" in ev for ev in bp_evidence)
    assert any("auth_multi.js: advisory: weak password hashing algorithm 'md5' detected (lines 3, 7)" in ev for ev in bp_evidence)


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
    assert not any("weak password hashing" in ev for ev in bp["evidence"])
    assert any("no advisory findings among the patterns checked (1 scanned files)" in ev for ev in bp["evidence"])


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

    dpdp_evidence = findings["IN-DPDP-013"]["evidence"]
    assert any("user_auth.js: access control (authentication): password hashing found: argon2" in ev for ev in dpdp_evidence)
    assert any("login_service.py: access control (authentication): password hashing found: bcrypt (lines 1, 3)" in ev for ev in dpdp_evidence)

    bp = findings["IN-BP-003"]
    assert not any(ev.startswith("advisory:") for ev in bp["evidence"])
    assert any("user_auth.js: informational: recommended password hashing algorithm 'argon2" in ev for ev in bp["evidence"])
    assert any("login_service.py: informational: recommended password hashing algorithm 'bcrypt' configured (lines 1, 3)" in ev for ev in bp["evidence"])
    assert "suggested_fix" not in bp


def test_hsts_presence_and_absence(tmp_path: Path):
    """
    HSTS wording:
    - 'nginx.conf: advisory: no Strict-Transport-Security header found' (no trailing 'in <file>').
    - 'nginx.conf: encryption/transport: no Strict-Transport-Security header found'.
    - Notes: 'HSTS may be set elsewhere (included files, CDN, load balancer).'
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

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

    assert any("nginx.conf: encryption/transport: no Strict-Transport-Security header found" in ev for ev in dpdp["evidence"])
    assert any("nginx.conf: advisory: no Strict-Transport-Security header found" in ev for ev in bp["evidence"])
    assert not any("in nginx.conf" in ev for ev in bp["evidence"] if "no Strict-Transport-Security" in ev)

    assert "HSTS may be set elsewhere (included files, CDN, load balancer)." in dpdp["notes"]
    assert "HSTS may be set elsewhere (included files, CDN, load balancer)." in bp["notes"]


def test_storage_rules_public_write_vs_restricted(tmp_path: Path):
    """Storage rules: public write vs restricted access conditions."""
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
    assert any("storage.rules:5: advisory: public write access permitted in storage rules" in ev for ev in bp_bad["evidence"])

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
    assert any("storage.rules:5: informational: storage access restricted by authorization conditions" in ev for ev in bp_good["evidence"])


def test_log_retention_extraction(tmp_path: Path):
    """Log retention extraction with line-first format."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "logging.json").write_text(
        '{\n  "retention_days": 180,\n  "level": "info"\n}\n',
        encoding="utf-8",
    )
    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    dpdp = findings["IN-DPDP-013"]
    assert any("logging.json:2: retention settings: log retention configured for 180 days" in ev for ev in dpdp["evidence"])
    assert "r.6(1)(e) exception" in dpdp["notes"]
    assert "r.8(3) scope" in dpdp["notes"]


def test_backup_continuity_detection(tmp_path: Path):
    """Backup configuration: encrypted vs unencrypted."""
    # 1. Encrypted backup
    app_enc = tmp_path / "app_enc"
    app_enc.mkdir()
    (app_enc / "backup.sh").write_text(
        "tar -czf - /data | gpg --encrypt --recipient admin@example.com > /backup/data.tar.gz.gpg\n",
        encoding="utf-8",
    )
    doc_enc = evaluate_baseline(app_enc)
    assert any("backup.sh:1: backups/continuity: encrypted backup configuration found" in ev for ev in doc_enc["findings"][0]["evidence"])
    assert any("backup.sh:1: informational: encrypted backup configuration detected" in ev for ev in doc_enc["findings"][1]["evidence"])

    # 2. Unencrypted backup
    app_plain = tmp_path / "app_plain"
    app_plain.mkdir()
    (app_plain / "backup.sh").write_text(
        "tar -czf /backup/data.tar.gz /data\n",
        encoding="utf-8",
    )
    doc_plain = evaluate_baseline(app_plain)
    assert any("backup.sh: backups/continuity: unencrypted backup configuration found" in ev for ev in doc_plain["findings"][0]["evidence"])
    assert any("backup.sh: advisory: unencrypted backup configuration detected" in ev for ev in doc_plain["findings"][1]["evidence"])


def test_line_caps_rule(tmp_path: Path):
    """
    Line caps rule:
    - IN-BP-003 advisory lines are never capped.
    - IN-DPDP-013: max 5 lines per category; if more, append '<N> more matches not shown (total <N>)'.
    """
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Generate 6 auth files each with 1 weak hashing line
    for i in range(1, 7):
        (app_dir / f"auth_{i}.js").write_text(
            f"const crypto = require('crypto');\n"
            f"function hash(password) {{ return crypto.createHash('md5').update(password).digest('hex'); }}\n",
            encoding="utf-8",
        )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    # IN-DPDP-013 access control has 6 matches -> exactly 5 lines + 1 overflow line
    dpdp_evidence = findings["IN-DPDP-013"]["evidence"]
    ac_lines = [ev for ev in dpdp_evidence if "access control" in ev]
    assert len(ac_lines) == 6
    assert "access control: 1 more matches not shown (total 6)" in ac_lines[-1]

    # IN-BP-003 advisory lines are NEVER capped -> all 6 lines present
    bp_evidence = findings["IN-BP-003"]["evidence"]
    adv_lines = [ev for ev in bp_evidence if ev.startswith("auth_")]
    assert len(adv_lines) == 6


def test_suggested_fix_conditional_rule(tmp_path: Path):
    """
    Suggested fix:
    - ONE line separated by '; ', no numbering, no newlines.
    - Lists only detected advisories.
    - None / omitted if 0 advisories detected.
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

    # 2. Both weak hashing and missing HSTS
    app_both = tmp_path / "app_both"
    app_both.mkdir()
    (app_both / "auth.js").write_text(
        "const crypto = require('crypto');\n"
        "function hash(password) { return crypto.createHash('md5').update(password).digest('hex'); }\n",
        encoding="utf-8",
    )
    (app_both / "nginx.conf").write_text(
        "server { listen 443 ssl; server_name test.local; }\n",
        encoding="utf-8",
    )
    doc_both = evaluate_baseline(app_both)
    fix_text = doc_both["findings"][1]["suggested_fix"]
    assert "\n" not in fix_text
    assert "1." not in fix_text
    assert "2." not in fix_text
    assert "; " in fix_text
    assert "Argon2id or bcrypt" in fix_text
    assert "Strict-Transport-Security" in fix_text
    assert "storage rules" not in fix_text


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
        pass

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}
    notes = findings["IN-DPDP-013"]["notes"]

    assert "files scanned (1)" in notes
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


def test_evidence_format_path_first():
    """
    Assert all evidence lines across clean-app and flawed-app adhere to path-first
    or standard summary formats.
    """
    for app_dir in (CLEAN_APP_DIR, FLAWED_APP_DIR):
        assert app_dir.is_dir()
        doc = evaluate_baseline(app_dir)
        for f in doc["findings"]:
            for ev in f["evidence"]:
                assert PATH_FIRST_REGEX.match(ev), f"Evidence line does not match path-first pattern: {ev}"


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
    assert any("nginx.conf:21: encryption/transport: Strict-Transport-Security header configured" in ev for ev in dpdp_ev)
    assert any("auth.js: access control (authentication): password hashing found: argon2" in ev for ev in dpdp_ev)
    assert any("storage.rules:8: access control: storage rules restrict access with authorization conditions" in ev for ev in dpdp_ev)
    assert any("logging.json:5: retention settings: log retention configured for 365 days" in ev for ev in dpdp_ev)
    assert "committed secrets: no committed secrets detected in scanned files" in dpdp_ev

    # IN-BP-003
    bp = findings["IN-BP-003"]
    assert bp["result"] == "informational"
    assert "suggested_fix" not in bp
    bp_ev = bp["evidence"]
    assert not any(ev.startswith("advisory:") for ev in bp_ev)
    assert any("no advisory findings among the patterns checked (4 scanned files)" in ev for ev in bp_ev)
    assert any("auth.js: informational: recommended password hashing algorithm 'argon2" in ev for ev in bp_ev)
    assert any("nginx.conf:21: informational: Strict-Transport-Security header configured" in ev for ev in bp_ev)
    assert any("logging.json:5: informational: log retention configured for 365 days" in ev for ev in bp_ev)


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
    assert any("nginx.conf: encryption/transport: no Strict-Transport-Security header found" in ev for ev in dpdp_ev)
    assert any("auth.js: access control (authentication): password hashing found: md5 (lines 1, 6, 7, 11)" in ev for ev in dpdp_ev)
    assert any("storage.rules:8: access control: storage rules permit public write access" in ev for ev in dpdp_ev)
    assert any("logging.json:5: retention settings: log retention configured for 7 days" in ev for ev in dpdp_ev)
    assert any(".env:3: committed secrets: committed secret in API_SECRET_KEY (value not shown)" in ev for ev in dpdp_ev)
    assert any(".env: committed secrets: committed environment file with 1 other assignment (keys and values not shown)" in ev for ev in dpdp_ev)

    # IN-BP-003
    bp = findings["IN-BP-003"]
    assert bp["result"] == "informational"
    assert "suggested_fix" in bp
    bp_ev = bp["evidence"]
    assert any("auth.js: advisory: weak password hashing algorithm 'md5' detected (lines 1, 6, 7, 11)" in ev for ev in bp_ev)
    assert any("nginx.conf: advisory: no Strict-Transport-Security header found" in ev for ev in bp_ev)
    assert any("storage.rules:8: advisory: public write access permitted in storage rules" in ev for ev in bp_ev)

    fix = bp["suggested_fix"]
    assert "Argon2id or bcrypt" in fix
    assert "Strict-Transport-Security" in fix
    assert "storage rules" in fix
    assert "; " in fix
    assert "\n" not in fix


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


# ---------------------------------------------------------------------------
# Task 12: Fast Keyed Hash / HMAC Detection & All-Clear Tests
# ---------------------------------------------------------------------------

def test_auth_create_hmac_synthetic_case(tmp_path: Path):
    """Synthetic JS createHmac('sha1', salt).update(password) -> hmac-sha1 advisory and authentication finding."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    models_dir = app_dir / "models"
    models_dir.mkdir()
    js_content = (
        "const crypto = require('crypto');\n"
        "\n"
        "function hashPassword(password, salt) {\n"
        "  return crypto.createHmac('sha1', salt).update(password).digest('hex');\n"
        "}\n"
    )
    (models_dir / "user.js").write_text(js_content, encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    # IN-BP-003
    bp = findings["IN-BP-003"]
    assert bp["result"] == "informational"
    assert "models/user.js: advisory: fast keyed hash used with password data (hmac-sha1); no work factor (line 4)" in bp["evidence"]
    assert "suggested_fix" in bp
    assert bp["suggested_fix"] == "Upgrade password hashing to Argon2id or bcrypt with appropriate work factor"

    # IN-DPDP-013
    dpdp = findings["IN-DPDP-013"]
    assert dpdp["result"] == "needs-human"
    assert "models/user.js: access control (authentication): password hashing found: hmac-sha1 (line 4)" in dpdp["evidence"]


def test_auth_python_and_php_hmac_flagged(tmp_path: Path):
    """Python hmac.new -> hmac-sha256; PHP hash_hmac -> hmac-sha1."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    py_content = (
        "import hmac\n"
        "\n"
        "def hash_pw(key, password):\n"
        "    return hmac.new(key, password.encode(), 'sha256').hexdigest()\n"
    )
    (app_dir / "auth_helper.py").write_text(py_content, encoding="utf-8")

    php_content = (
        "<?php\n"
        "function hash_user_password($password, $key) {\n"
        "    return hash_hmac('sha1', $password, $key);\n"
        "}\n"
    )
    (app_dir / "user_service.php").write_text(php_content, encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp_ev = findings["IN-BP-003"]["evidence"]
    assert "auth_helper.py: advisory: fast keyed hash used with password data (hmac-sha256); no work factor (line 4)" in bp_ev
    assert "user_service.php: advisory: fast keyed hash used with password data (hmac-sha1); no work factor (line 3)" in bp_ev

    dpdp_ev = findings["IN-DPDP-013"]["evidence"]
    assert "auth_helper.py: access control (authentication): password hashing found: hmac-sha256 (line 4)" in dpdp_ev
    assert "user_service.php: access control (authentication): password hashing found: hmac-sha1 (line 3)" in dpdp_ev


def test_auth_hmac_without_password_keyword_not_flagged(tmp_path: Path):
    """createHmac('sha256', secret).update(sessionId) with no password word within 3 lines -> not flagged."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    js_content = (
        "const crypto = require('crypto');\n"
        "\n"
        "function signSession(sessionId, secret) {\n"
        "  return crypto.createHmac('sha256', secret).update(sessionId).digest('hex');\n"
        "}\n"
    )
    (app_dir / "auth_tokens.js").write_text(js_content, encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp = findings["IN-BP-003"]
    assert not any("advisory:" in ev for ev in bp["evidence"])
    assert "no advisory findings among the patterns checked (1 scanned files)" in bp["evidence"]

    dpdp = findings["IN-DPDP-013"]
    assert not any("password hashing found" in ev for ev in dpdp["evidence"])


def test_hash_without_password_nearby_not_flagged(tmp_path: Path):
    """A hash line with no password word within 3 lines of it, plus an active hashing function elsewhere in the file."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    js_content = (
        "const crypto = require('crypto');\n"
        "\n"
        "const sessionToken = crypto.createHmac('sha1', key).update(token).digest('hex');\n"
        "const spacer1 = 1;\n"
        "const spacer2 = 2;\n"
        "const spacer3 = 3;\n"
        "const spacer4 = 4;\n"
        "\n"
        "function hashUserPassword(password, salt) {\n"
        "  return crypto.createHmac('sha1', salt).update(password).digest('hex');\n"
        "}\n"
    )
    (app_dir / "user_auth.js").write_text(js_content, encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp_ev = findings["IN-BP-003"]["evidence"]
    assert "user_auth.js: advisory: fast keyed hash used with password data (hmac-sha1); no work factor (line 10)" in bp_ev
    assert not any("line 3" in ev or "lines 3" in ev for ev in bp_ev)

    dpdp_ev = findings["IN-DPDP-013"]["evidence"]
    assert "user_auth.js: access control (authentication): password hashing found: hmac-sha1 (line 10)" in dpdp_ev
    assert not any("line 3" in ev or "lines 3" in ev for ev in dpdp_ev)


def test_baseline_all_clear_wording_and_notes(tmp_path: Path):
    """All-clear wording and notes sentence in IN-BP-003."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "nginx.conf").write_text(
        "server {\n"
        "  add_header Strict-Transport-Security 'max-age=31536000';\n"
        "  ssl_protocols TLSv1.3;\n"
        "}\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp = findings["IN-BP-003"]
    assert any("no advisory findings among the patterns checked (1 scanned files)" in ev for ev in bp["evidence"])
    assert "Only the listed patterns are checked; other password hashing code may not be detected. Calls split across several lines may not be detected." in bp["notes"]


# ---------------------------------------------------------------------------
# Task 12b: Expanded Auth Code Recognition, Accounting & Notes Tests
# ---------------------------------------------------------------------------

def test_auth_code_parent_folder_rule_relative_to_root(tmp_path: Path):
    """Parent folder keyword matches only below scan root; host folder names cannot trigger it."""
    host_dir = tmp_path / "user_auth_env"
    host_dir.mkdir()
    app_dir = host_dir / "app"
    app_dir.mkdir()

    # Rule 2 matches below scan root
    (app_dir / "routes" / "api" / "auth").mkdir(parents=True)
    (app_dir / "routes" / "api" / "auth" / "index.js").write_text(
        "const crypto = require('crypto');\n"
        "function hashPassword(password) { return crypto.createHash('md5').update(password).digest('hex'); }\n",
        encoding="utf-8",
    )
    (app_dir / "routes" / "api" / "user").mkdir(parents=True)
    (app_dir / "routes" / "api" / "user" / "index.js").write_text(
        "const crypto = require('crypto');\n"
        "function hashUser(password) { return crypto.createHash('sha256').update(password).digest('hex'); }\n",
        encoding="utf-8",
    )

    # Standalone file directly in app: basename 'standalone.js', no auth words in parent parts below app_dir
    (app_dir / "standalone.js").write_text(
        "const greeting = 'hello world';\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp_ev = findings["IN-BP-003"]["evidence"]
    assert any("routes/api/auth/index.js: advisory: weak password hashing algorithm 'md5' detected" in ev for ev in bp_ev)
    assert not any("standalone.js" in ev for ev in bp_ev)

    dpdp_ev = findings["IN-DPDP-013"]["evidence"]
    assert any("routes/api/auth/index.js: access control (authentication): password hashing found: md5" in ev for ev in dpdp_ev)
    assert any("routes/api/user/index.js: access control (authentication): password hashing found: sha256" in ev for ev in dpdp_ev)
    assert not any("standalone.js" in ev for ev in dpdp_ev)


def test_auth_code_content_rule_compound_password(tmp_path: Path):
    """Content mentions compound identifier 'passwordHash' without word boundary plus 'bcrypt'."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    services_dir = app_dir / "services"
    services_dir.mkdir()

    (services_dir / "tokens.js").write_text(
        "const bcrypt = require('bcrypt');\n"
        "async function storeToken(rawInput) {\n"
        "  const passwordHash = await bcrypt.hash(rawInput, 10);\n"
        "  return passwordHash;\n"
        "}\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    dpdp_ev = findings["IN-DPDP-013"]["evidence"]
    assert any("services/tokens.js: access control (authentication): password hashing found: bcrypt" in ev for ev in dpdp_ev)

    bp_ev = findings["IN-BP-003"]["evidence"]
    assert any("services/tokens.js: informational: recommended password hashing algorithm 'bcrypt' configured" in ev for ev in bp_ev)


def test_location_hash_plus_password_not_classified(tmp_path: Path):
    """Bare word 'hash' (e.g. location.hash) with 'password' must not classify non-auth files."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    handlers_dir = app_dir / "handlers"
    handlers_dir.mkdir()

    (handlers_dir / "navigation.js").write_text(
        "function handleNav() {\n"
        "  const hash = window.location.hash;\n"
        "  const password = getQueryParam('password');\n"
        "  if (hash === '#reset') showReset(password);\n"
        "}\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    dpdp_ev = findings["IN-DPDP-013"]["evidence"]
    assert not any("handlers/navigation.js" in ev for ev in dpdp_ev)
    bp_ev = findings["IN-BP-003"]["evidence"]
    assert not any("handlers/navigation.js" in ev for ev in bp_ev)


def test_file_with_password_but_no_hash_not_classified(tmp_path: Path):
    """File with bare word 'password' but no hashing word is not classified; singular N asserted."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    cfg_dir = app_dir / "config"
    cfg_dir.mkdir()

    (cfg_dir / "credentials.js").write_text(
        "const password = 'my_database_password';\n"
        "module.exports = { password };\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp = findings["IN-BP-003"]
    assert not any("credentials.js" in ev for ev in bp["evidence"])
    assert "1 code file (.js .jsx .ts .tsx .py .php) in recognised extensions was not analysed because no auth or password-hashing signal was found." in bp["notes"]

    dpdp = findings["IN-DPDP-013"]
    assert not any("credentials.js" in ev for ev in dpdp["evidence"])
    assert "1 code file (.js .jsx .ts .tsx .py .php) in recognised extensions was not analysed because no auth or password-hashing signal was found." in dpdp["notes"]


def test_auth_code_node_modules_and_vendor_skipped(tmp_path: Path):
    """node_modules and vendor directories are pruned and not counted in N or M."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    nm = app_dir / "node_modules" / "auth-pkg"
    nm.mkdir(parents=True)
    (nm / "index.js").write_text("const bcrypt = require('bcrypt'); bcrypt.hash(password, 10);", encoding="utf-8")

    vendor = app_dir / "vendor" / "laravel"
    vendor.mkdir(parents=True)
    (vendor / "login.php").write_text("<?php password_hash($password, PASSWORD_BCRYPT);", encoding="utf-8")

    (app_dir / "auth.js").write_text(
        "const argon2 = require('argon2');\n"
        "async function hash(password) { return await argon2.hash(password); }\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp = findings["IN-BP-003"]
    assert not any("node_modules" in ev for ev in bp["evidence"])
    assert not any("vendor" in ev for ev in bp["evidence"])
    # N is 0, so N sentence is omitted entirely
    assert "was not analysed because no auth" not in bp["notes"]
    assert "were not analysed because no auth" not in bp["notes"]
    assert "exceeded 1 MB or could not be read" not in bp["notes"]


def test_auth_code_minified_file_skipped(tmp_path: Path):
    """.min.js file is skipped in scan loop without incrementing N or M."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    (app_dir / "bundle.min.js").write_text(
        "function hash(password){return crypto.createHash('md5').update(password).digest('hex');}",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp = findings["IN-BP-003"]
    assert not any("bundle.min.js" in ev for ev in bp["evidence"])
    # N is 0, so N sentence is omitted
    assert "not analysed because no auth" not in bp["notes"]
    assert "exceeded 1 MB or could not be read" not in bp["notes"]


def test_tsx_file_with_hashing_signal_classified(tmp_path: Path):
    """.tsx file with hashing signal is classified; asserts exact line 1 and 3 matches."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    comp_dir = app_dir / "components"
    comp_dir.mkdir()

    tsx_content = (
        "import argon2 from 'argon2';\n"
        "export async function register(password: string) {\n"
        "  return await argon2.hash(password);\n"
        "}\n"
    )
    (comp_dir / "Register.tsx").write_text(tsx_content, encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    dpdp_ev = findings["IN-DPDP-013"]["evidence"]
    assert "components/Register.tsx: access control (authentication): password hashing found: argon2 (lines 1, 3)" in dpdp_ev

    bp_ev = findings["IN-BP-003"]["evidence"]
    assert "components/Register.tsx: informational: recommended password hashing algorithm 'argon2' configured (lines 1, 3)" in bp_ev


def test_unanalysed_and_multiple_oversize_code_files_accounting(tmp_path: Path):
    """Multiple oversize code files assert plural M; multiple candidate code files assert plural N."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # Scanned code files
    (app_dir / "auth.js").write_text(
        "const argon2 = require('argon2');\n"
        "async function hash(password) { return await argon2.hash(password); }\n",
        encoding="utf-8",
    )
    (app_dir / "routes" / "auth").mkdir(parents=True)
    (app_dir / "routes" / "auth" / "index.js").write_text(
        "const crypto = require('crypto');\n"
        "function hash(password) { return crypto.createHash('sha256').update(password).digest('hex'); }\n",
        encoding="utf-8",
    )

    # 2 unanalysed code files in recognised extensions (.js, .ts)
    (app_dir / "utils").mkdir()
    (app_dir / "utils" / "math.js").write_text("export function add(a, b) { return a + b; }\n", encoding="utf-8")
    (app_dir / "helpers").mkdir()
    (app_dir / "helpers" / "format.ts").write_text("export function fmt(s: string) { return s.trim(); }\n", encoding="utf-8")

    # 2 oversize code files in recognised extensions (.py, .ts)
    (app_dir / "large1.py").write_text("#" + "x" * (MAX_FILE_SIZE + 10), encoding="utf-8")
    (app_dir / "large2.ts").write_text("//" + "y" * (MAX_FILE_SIZE + 10), encoding="utf-8")

    # Directories that should be pruned without incrementing N or M
    (app_dir / "vendor" / "pkg").mkdir(parents=True)
    (app_dir / "vendor" / "pkg" / "lib.js").write_text("console.log('vendor');", encoding="utf-8")
    (app_dir / "dist").mkdir()
    (app_dir / "dist" / "app.js").write_text("console.log('dist');", encoding="utf-8")

    # Minified file skipped without incrementing N or M
    (app_dir / "main.min.js").write_text("console.log('min');", encoding="utf-8")

    # Non-code file
    (app_dir / "index.html").write_text("<h1>Hello</h1>", encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp_notes = findings["IN-BP-003"]["notes"]
    dpdp_notes = findings["IN-DPDP-013"]["notes"]

    expected_n = "2 code files (.js .jsx .ts .tsx .py .php) in recognised extensions were not analysed because no auth or password-hashing signal was found."
    expected_m = "2 code files were skipped because they exceeded 1 MB or could not be read."

    assert expected_n in bp_notes
    assert expected_m in bp_notes
    assert expected_n in dpdp_notes
    assert expected_m in dpdp_notes


def test_single_oversize_code_file_singular_m(tmp_path: Path):
    """Single oversize code file asserts singular M sentence."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    (app_dir / "large.py").write_text("#" + "x" * (MAX_FILE_SIZE + 10), encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    expected_m = "1 code file was skipped because it exceeded 1 MB or could not be read."
    assert expected_m in findings["IN-BP-003"]["notes"]
    assert expected_m in findings["IN-DPDP-013"]["notes"]


def test_unreadable_code_file_counted_in_m(tmp_path: Path):
    """Code file that raises OSError on read is classified unreadable and counted in M, not N."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    unreadable_file = app_dir / "broken.js"
    unreadable_file.write_text("some code", encoding="utf-8")

    # Simulate OSError during is_recognised_file Rule 3 open
    original_open = Path.open

    def failing_open(self, *args, **kwargs):
        if self.name == "broken.js":
            raise PermissionError("Simulated unreadable file")
        return original_open(self, *args, **kwargs)

    Path.open = failing_open
    try:
        doc = evaluate_baseline(app_dir)
    finally:
        Path.open = original_open

    findings = {f["check_id"]: f for f in doc["findings"]}
    bp_notes = findings["IN-BP-003"]["notes"]

    expected_m = "1 code file was skipped because it exceeded 1 MB or could not be read."
    assert expected_m in bp_notes
    assert "was not analysed because no auth" not in bp_notes


# -------------------------------------------------------------------------
# Other Source Files Accounting Tests
# -------------------------------------------------------------------------

def test_other_source_files_singular(tmp_path: Path):
    """Single unanalysed other source file asserts singular sentence."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    (app_dir / "auth.js").write_text(
        "const argon2 = require('argon2');\nasync function hash(p) { return await argon2.hash(p); }\n",
        encoding="utf-8",
    )
    (app_dir / "Calculator.java").write_text(
        "public class Calculator { public int add(int a, int b) { return a + b; } }\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    expected_singular = "Other source file not analysed: 1 .java."
    assert expected_singular in findings["IN-BP-003"]["notes"]
    assert expected_singular in findings["IN-DPDP-013"]["notes"]
    assert "Other source files not analysed" not in findings["IN-BP-003"]["notes"]


def test_other_source_files_plural_and_ordering(tmp_path: Path):
    """Multiple other source files assert plural sentence ordered by count desc, then extension asc."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    (app_dir / "auth.js").write_text("console.log('auth');", encoding="utf-8")

    # 3 .java files
    for i in range(3):
        (app_dir / f"App{i}.java").write_text("public class App {}", encoding="utf-8")

    # 2 .go files
    for i in range(2):
        (app_dir / f"worker{i}.go").write_text("package main", encoding="utf-8")

    # 1 .rs file
    (app_dir / "lib.rs").write_text("pub fn run() {}", encoding="utf-8")

    # Tie breaker: 1 .cs and 1 .kt (both count 1, .cs should precede .kt, .rs before or after)
    (app_dir / "Program.cs").write_text("class Program {}", encoding="utf-8")
    (app_dir / "Service.kt").write_text("class Service", encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    # Ordering: 3 .java, 2 .go, 1 .cs, 1 .kt, 1 .rs
    expected_plural = "Other source files not analysed: 3 .java, 2 .go, 1 .cs, 1 .kt, 1 .rs."
    assert expected_plural in findings["IN-BP-003"]["notes"]
    assert expected_plural in findings["IN-DPDP-013"]["notes"]


def test_other_source_files_no_double_counting(tmp_path: Path):
    """UserAuth.java recognised by basename rule is scanned; Service.java is unanalysed and counted."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # UserAuth.java has "auth" in filename and bcrypt hash -> recognised as auth_code
    (app_dir / "UserAuth.java").write_text(
        "import org.mindrot.jbcrypt.BCrypt;\n"
        "public class UserAuth {\n"
        "    public String hash(String password) {\n"
        "        return BCrypt.hashpw(password, BCrypt.gensalt());\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    # Service.java has no auth keyword in filename -> unrecognised
    (app_dir / "Service.java").write_text(
        "public class Service { public void doWork() {} }\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    dpdp = findings["IN-DPDP-013"]
    bp = findings["IN-BP-003"]

    # UserAuth.java is scanned, not unanalysed
    assert any("UserAuth.java" in ev for ev in dpdp["evidence"])
    assert "files scanned (1)" in dpdp["notes"]

    # Only Service.java is unanalysed (count is 1 .java, NOT 2 .java)
    expected_singular = "Other source file not analysed: 1 .java."
    assert expected_singular in bp["notes"]
    assert expected_singular in dpdp["notes"]
    assert "2 .java" not in bp["notes"]


def test_other_source_files_omitted_when_zero(tmp_path: Path):
    """When no other source files are present, the sentence is omitted."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    (app_dir / "auth.js").write_text("const x = 1;", encoding="utf-8")
    (app_dir / "helper.js").write_text("const y = 2;", encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp_notes = findings["IN-BP-003"]["notes"]
    dpdp_notes = findings["IN-DPDP-013"]["notes"]

    assert "Other source file not analysed" not in bp_notes
    assert "Other source files not analysed" not in bp_notes
    assert "Other source file not analysed" not in dpdp_notes
    assert "Other source files not analysed" not in dpdp_notes


def test_other_source_files_vendor_and_node_modules_pruned(tmp_path: Path):
    """Other source files inside vendor or node_modules are pruned and not counted."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    (app_dir / "auth.js").write_text("const x = 1;", encoding="utf-8")

    vendor = app_dir / "vendor" / "java_lib"
    vendor.mkdir(parents=True)
    (vendor / "Lib.java").write_text("class Lib {}", encoding="utf-8")

    nm = app_dir / "node_modules" / "go_tool"
    nm.mkdir(parents=True)
    (nm / "tool.go").write_text("package tool", encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp_notes = findings["IN-BP-003"]["notes"]
    assert "Other source file not analysed" not in bp_notes
    assert "Other source files not analysed" not in bp_notes


def test_other_source_files_over_1mb_java_counted(tmp_path: Path):
    """A .java file over 1 MB is counted in other source files not analysed."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    (app_dir / "auth.js").write_text("const x = 1;", encoding="utf-8")
    (app_dir / "Big.java").write_text("//" + "z" * (MAX_FILE_SIZE + 10), encoding="utf-8")

    doc = evaluate_baseline(app_dir)
    findings = {f["check_id"]: f for f in doc["findings"]}

    bp_notes = findings["IN-BP-003"]["notes"]
    dpdp_notes = findings["IN-DPDP-013"]["notes"]

    expected_singular = "Other source file not analysed: 1 .java."
    assert expected_singular in bp_notes
    assert expected_singular in dpdp_notes

    # M sentence applies only to CODE_EXTENSIONS (.js .jsx .ts .tsx .py .php)
    assert "code file was skipped because it exceeded 1 MB" not in bp_notes
    assert "code files were skipped because they exceeded 1 MB" not in bp_notes


def test_other_source_files_mutation_drops_java(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Mutation test: monkeypatch removing .java from OTHER_SOURCE_EXTENSIONS causes sentence to disappear."""
    import scripts.baseline

    app_dir = tmp_path / "app"
    app_dir.mkdir()

    (app_dir / "auth.js").write_text("const x = 1;", encoding="utf-8")
    (app_dir / "Calculator.java").write_text("class Calculator {}", encoding="utf-8")

    # Baseline run with original set
    doc_normal = evaluate_baseline(app_dir)
    normal_notes = doc_normal["findings"][1]["notes"]
    assert "Other source file not analysed: 1 .java." in normal_notes

    # Mutated run with .java removed from OTHER_SOURCE_EXTENSIONS
    mutated_set = set(scripts.baseline.OTHER_SOURCE_EXTENSIONS) - {".java"}
    assert mutated_set != scripts.baseline.OTHER_SOURCE_EXTENSIONS, "Mutated set must differ from original"

    monkeypatch.setattr(scripts.baseline, "OTHER_SOURCE_EXTENSIONS", mutated_set)
    doc_mutated = evaluate_baseline(app_dir)
    mutated_notes = doc_mutated["findings"][1]["notes"]

    assert mutated_notes != normal_notes, "Mutated notes must differ from normal notes"
    assert "Other source file not analysed" not in mutated_notes
    assert "Other source files not analysed" not in mutated_notes


def test_committed_secrets_eight_lines_table():
    """Verify extract_secret_info on the benchmark 8 test lines."""
    # 1. Object literal
    res = extract_secret_info("{ username: 'admin', password: 'hunter2' }")
    assert res == ("secret", "password")

    # 2. Preceding statement on same line
    res = extract_secret_info('const a = 1; const password = "hunter2";')
    assert res == ("secret", "password")

    # 3. Quoted key in JSON/object
    res = extract_secret_info('"password": "hunter2abc"')
    assert res == ("secret", "password")

    # 4. Subscript assignment
    res = extract_secret_info('config["password"] = "hunter2abc"')
    assert res == ("secret", "password")

    # 5. Assignment with trailing inline comment
    res = extract_secret_info('DB_PASS = "hunter2abc"  # prod')
    assert res == ("secret", "DB_PASS")

    # 6. Variable reference (not a string literal) -> not flagged
    assert extract_secret_info('password = req.body.password') is None

    # 7. SQL query string incorporating variable -> not flagged
    assert extract_secret_info('$query = "SELECT * FROM users WHERE password = \'$pass\'";') is None

    # 8. UI error message key -> not flagged
    assert extract_secret_info('invalidPasswordErrorMessage: "Invalid password"') is None


def test_committed_secrets_message_key_and_sql_and_placeholder_exclusions():
    """Verify message key suffixes, SQL keywords, and placeholder exclusions."""
    # Message / UI label suffixes
    assert extract_secret_info('passwordError = "Too short"') is None
    assert extract_secret_info('password_hint: "Mother maiden name"') is None
    assert extract_secret_info('const passwordPrompt = "Enter password:";') is None
    assert extract_secret_info('passwordLabel: "Password"') is None
    assert extract_secret_info('password_placeholder: "Password"') is None
    assert extract_secret_info('token_desc = "Auth token"') is None

    # SQL query strings and expressions
    assert extract_secret_info('const sql = "INSERT INTO users (password) VALUES (\'" + pwd + "\')";') is None
    assert extract_secret_info('$insert = "UPDATE users SET password = \'$new_pass\' WHERE id = 1";') is None
    assert extract_secret_info("models.query(`SELECT * FROM users WHERE password = '${hash(pwd)}'`);") is None

    # Function call pattern in value
    assert extract_secret_info('const API_KEY = "env(\'MY_KEY\')";') is None
    assert extract_secret_info('const TOKEN = "getAuthToken()";') is None

    # Placeholders
    assert extract_secret_info('API_KEY = "changeme"') is None
    assert extract_secret_info('API_KEY = "xxxxxxxx"') is None
    assert extract_secret_info('PASSWORD = "<your-password-here>"') is None


def test_committed_secrets_env_unchanged_and_value_never_printed(tmp_path: Path):
    """Verify .env behavior remains intact and secret values are never printed in findings JSON."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    secret_auth_val = "SECRET_AUTH_VAL_991188"
    secret_env_val = "SECRET_ENV_VAL_334455"
    conn_val = "SECRET_CONN_VAL_556677"

    (app_dir / "auth.js").write_text(
        f'const AUTH_TOKEN = "{secret_auth_val}";\n'
        f'const DB_URI = "postgres://user:{conn_val}@localhost:5432/mydb";\n',
        encoding="utf-8",
    )
    (app_dir / ".env").write_text(
        f"APP_SECRET={secret_env_val}\n"
        "APP_PLACEHOLDER=changeme\n"
        "DATABASE_URL=postgres://user:pass@localhost:5432/test\n"
        "OTHER_VAR_1=foo\n"
        "OTHER_VAR_2=bar\n",
        encoding="utf-8",
    )

    doc = evaluate_baseline(app_dir)
    json_text = json.dumps(doc)

    # Secret values never printed anywhere in findings JSON
    assert secret_auth_val not in json_text
    assert secret_env_val not in json_text
    assert conn_val not in json_text

    dpdp = next(f for f in doc["findings"] if f["check_id"] == "IN-DPDP-013")
    ev = dpdp["evidence"]

    # Redacted evidence lines
    assert any("auth.js:1: committed secrets: committed secret in AUTH_TOKEN (value not shown)" in line for line in ev)
    assert any("auth.js:2: committed secrets: committed credential in connection string for DB_URI (value not shown)" in line for line in ev)
    assert any(".env:1: committed secrets: committed secret in APP_SECRET (value not shown)" in line for line in ev)
    assert any(".env:3: committed secrets: committed credential in connection string for DATABASE_URL (value not shown)" in line for line in ev)
    assert any(".env: committed secrets: committed environment file with 3 other assignments (keys and values not shown)" in line for line in ev)


def test_committed_secrets_test_files_rule(tmp_path: Path):
    """Verify secret assignments in test or spec files are counted in notes, not listed in evidence."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # 1. No test files -> notes sentence omitted
    (app_dir / "auth.js").write_text('const API_KEY = "production_secret_123";\n', encoding="utf-8")
    doc_zero = evaluate_baseline(app_dir)
    notes_zero = doc_zero["findings"][0]["notes"]
    assert "secret-like assignment in test or spec files not listed" not in notes_zero
    ev_zero = doc_zero["findings"][0]["evidence"]
    assert any("auth.js:1: committed secrets: committed secret in API_KEY (value not shown)" in line for line in ev_zero)

    # 2. Singular: 1 secret in a test file
    test_dir = app_dir / "tests"
    test_dir.mkdir()
    (test_dir / "test_auth.js").write_text('const TEST_KEY = "test_fixture_secret_456";\n', encoding="utf-8")
    doc_single = evaluate_baseline(app_dir)
    notes_single = doc_single["findings"][0]["notes"]
    assert "1 secret-like assignment in test or spec files not listed." in notes_single
    assert "secret-like assignments" not in notes_single
    ev_single = doc_single["findings"][0]["evidence"]
    # Test fixture NOT listed in evidence
    assert not any("TEST_KEY" in line for line in ev_single)
    # Production secret still in evidence
    assert any("auth.js:1: committed secrets: committed secret in API_KEY (value not shown)" in line for line in ev_single)

    # 3. Plural: 2 secrets across test and spec files
    (app_dir / "login.spec.js").write_text('const MOCK_TOKEN = "mock_secret_token_789";\n', encoding="utf-8")
    doc_plural = evaluate_baseline(app_dir)
    notes_plural = doc_plural["findings"][0]["notes"]
    assert "2 secret-like assignments in test or spec files not listed." in notes_plural
    ev_plural = doc_plural["findings"][0]["evidence"]
    assert not any("TEST_KEY" in line for line in ev_plural)
    assert not any("MOCK_TOKEN" in line for line in ev_plural)
    assert any("auth.js:1: committed secrets: committed secret in API_KEY (value not shown)" in line for line in ev_plural)


def test_message_key_filter_mutation_test(monkeypatch: pytest.MonkeyPatch):
    """Mutation test: emptying MESSAGE_KEY_SUFFIXES causes message keys to be flagged as secrets."""
    import scripts.baseline

    test_line = 'invalidPasswordErrorMessage: "Invalid password provided"'

    # Normal baseline: message key is NOT flagged as a secret
    assert scripts.baseline.extract_secret_info(test_line) is None

    # Mutate MESSAGE_KEY_SUFFIXES to empty tuple
    mutated_suffixes = ()
    assert mutated_suffixes != scripts.baseline.MESSAGE_KEY_SUFFIXES, "Mutated suffixes must differ from original"

    monkeypatch.setattr(scripts.baseline, "MESSAGE_KEY_SUFFIXES", mutated_suffixes)
    mutated_res = scripts.baseline.extract_secret_info(test_line)
    assert mutated_res == ("secret", "invalidPasswordErrorMessage"), "Under mutation, message key must be erroneously flagged"


