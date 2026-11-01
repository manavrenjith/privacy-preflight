#!/usr/bin/env python3
"""
Privacy Preflight - Technical Security Baseline and Safeguards Analyzer (Task 8)

Evaluates technical configurations, safeguards, and baselines under Indian privacy law
and modern engineering standards:
- IN-DPDP-013 (assisted): Reasonable security safeguards and access logging.
  Under Act s.8(5) and Rules r.6(1)(a)-(g), r.8(3), Data Fiduciaries must implement
  reasonable security safeguards across encryption, access control, access logging,
  continuity measures, and log retention. Result is ALWAYS 'needs-human' when at least
  one recognised file was scanned, or 'unclear' if none. Never 'met' or 'not-met'.
- IN-BP-003 (automated): Technical security baseline configurations.
  Engineering best practice evaluation for password hashing algorithms, HSTS enforcement,
  storage permissions, and backup encryption. Result is ALWAYS 'informational'.

Standard library only. Not legal advice.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

MAX_FILE_SIZE = 1024 * 1024  # 1 MB
SKIP_DIRS = {".git", "node_modules", "reports", "dist", "build", "__pycache__"}

RULE_6_CATEGORIES = [
    "encryption/transport",
    "access control",
    "access logging and monitoring",
    "backups/continuity",
    "retention settings",
    "committed secrets",
]

AUTH_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".py", ".php", ".go", ".rb", ".java"}
AUTH_NAME_KEYWORDS = ("auth", "login", "password", "user", "account", "signup", "session")

LOGGING_EXTENSIONS = {".json", ".yaml", ".yml"}
STORAGE_RULE_EXTENSIONS = {".rules"}
CONFIG_EXTENSIONS = {".conf"}
BACKUP_EXTENSIONS = {".sh", ".py", ".json", ".yaml", ".yml", ".conf"}

# Regexes
SECRET_ASSIGNMENT_REGEX = re.compile(
    r"""(?i)\b[A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASS)[A-Z0-9_]*\s*[:=]\s*(['"]?)([^'"\s#;\r\n]+)\1"""
)
NON_SECRET_VALUES = {"null", "none", "false", "true", "undefined", ""}

WEAK_HASH_REGEX = re.compile(r"""(?i)\b(md5|sha1|sha-1|sha256|sha-256)\b""")
PASSWORD_KEYWORD_REGEX = re.compile(r"""(?i)\b(password|passwd|pwd)\b""")
STRONG_HASH_REGEX = re.compile(r"""(?i)\b(argon2id|argon2|bcrypt|scrypt|pbkdf2)\b""")

HSTS_HEADER_REGEX = re.compile(r"""(?i)\bStrict-Transport-Security\b""")
TLS_PROTOCOLS_REGEX = re.compile(r"""(?i)\bssl_protocols\s+([^;]+);""")
HTTPS_REDIRECT_REGEX = re.compile(r"""(?i)\breturn\s+(?:301|302)\s+https:""")

STORAGE_PUBLIC_WRITE_REGEX = re.compile(r"""(?i)allow\s+[^;]*\bwrite\b[^;]*:\s*if\s+true\s*;""")
STORAGE_RESTRICTED_REGEX = re.compile(
    r"""(?i)allow\s+[^;]*\bwrite\b[^;]*:\s*if\s+(?:false|request\.auth\b)"""
)

LOG_RETENTION_REGEX = re.compile(r"""(?i)["']retention(?:_days)?["']\s*:\s*([0-9]+)""")
LOG_LEVEL_REGEX = re.compile(r"""(?i)["']level["']\s*:\s*["']([^"']+)["']""")
LOG_DEST_REGEX = re.compile(r"""(?i)["']destination["']\s*:\s*["']([^"']+)["']""")

BACKUP_ENCRYPTION_REGEX = re.compile(r"""(?i)\b(gpg|kms|aes(?:-256)?|openssl\s+enc|encrypt(?:ed|ion)?)\b""")


def is_secret_assignment(line: str) -> bool:
    """Check if a line assigns a non-empty value to a secret-like key."""
    m = SECRET_ASSIGNMENT_REGEX.search(line)
    if m:
        val = m.group(2).strip()
        if val and val.lower() not in NON_SECRET_VALUES:
            return True
    return False


def get_safe_snippet(line: str, is_env: bool = False) -> str:
    """Return a sanitized snippet that never leaks secret values."""
    if is_env:
        return "<line redacted: possible secret>"
    if is_secret_assignment(line):
        return "<line redacted: possible secret>"
    return line.strip()[:80]


def is_recognised_file(file_path: Path) -> Tuple[bool, str]:
    """
    Determine if a file matches recognised formats.
    Returns (is_recognised, format_kind).
    """
    name = file_path.name
    name_lower = name.lower()
    ext = file_path.suffix.lower()

    # 1. Environment / secrets files (excluding templates/examples)
    if name_lower.startswith(".env"):
        if name_lower in {".env.example", ".env.sample", ".env.template", ".env.dist", ".env.test"}:
            return False, "env_template"
        return True, "env"

    # 2. Storage rules
    if ext in STORAGE_RULE_EXTENSIONS:
        return True, "storage_rules"

    # 3. Web server / Nginx config
    if ext in CONFIG_EXTENSIONS or name_lower == "nginx.conf":
        return True, "web_config"

    # 4. Logging config
    if ext in LOGGING_EXTENSIONS and "log" in name_lower:
        return True, "logging_config"

    # 5. Backup config or scripts
    if ext in BACKUP_EXTENSIONS and any(k in name_lower for k in ("backup", "dump", "archive")):
        return True, "backup_config"

    # 6. Container / deployment
    if name_lower in {"docker-compose.yml", "docker-compose.yaml", "dockerfile"} or (
        name_lower.startswith("docker-compose.") and (name_lower.endswith(".yml") or name_lower.endswith(".yaml"))
    ):
        return True, "container_config"

    # 7. Auth code
    if ext in AUTH_EXTENSIONS and any(k in name_lower for k in AUTH_NAME_KEYWORDS):
        return True, "auth_code"

    return False, "unrecognised"


def scan_directory(
    app_dir: Path,
) -> Tuple[
    Dict[str, List[str]],  # dpdp_matches by Rule 6 category
    List[str],             # bp_advisories
    List[str],             # bp_informational
    int,                   # files_scanned
    int,                   # files_skipped
]:
    """Scan directory for technical configurations, safeguards, and baseline markers."""
    dpdp_matches: Dict[str, List[str]] = {cat: [] for cat in RULE_6_CATEGORIES}
    bp_advisories: List[str] = []
    bp_informational: List[str] = []

    files_scanned = 0
    files_skipped = 0

    backup_files_found = 0

    for root, dirs, files in os.walk(app_dir, followlinks=False):
        # Prune skip directories in-place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (Path(root) / d).is_symlink()]

        for fname in sorted(files):
            file_path = Path(root) / fname
            if file_path.is_symlink():
                files_skipped += 1
                continue

            try:
                st = file_path.stat()
                if st.st_size > MAX_FILE_SIZE:
                    files_skipped += 1
                    continue
            except OSError:
                files_skipped += 1
                continue

            recognised, kind = is_recognised_file(file_path)
            if not recognised:
                files_skipped += 1
                continue

            try:
                raw_content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                files_skipped += 1
                continue

            files_scanned += 1
            rel_path_str = file_path.relative_to(app_dir).as_posix()
            lines = raw_content.splitlines()

            # --- 1. Environment / Committed Secrets File ---
            if kind == "env":
                env_keys_found = 0
                for idx, line in enumerate(lines):
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    if "=" in stripped:
                        line_no = idx + 1
                        env_keys_found += 1
                        dpdp_matches["committed secrets"].append(
                            f"committed secrets: {rel_path_str}:{line_no}: <line redacted: possible secret>"
                        )
                if env_keys_found == 0:
                    dpdp_matches["committed secrets"].append(
                        f"committed secrets: {rel_path_str} (committed environment configuration file)"
                    )
                continue

            # --- 2. Auth Code (Password Hashing) ---
            if kind == "auth_code":
                # Check for secrets committed in auth code
                for idx, line in enumerate(lines):
                    if is_secret_assignment(line):
                        line_no = idx + 1
                        dpdp_matches["committed secrets"].append(
                            f"committed secrets: {rel_path_str}:{line_no}: <line redacted: possible secret>"
                        )

                # Weak hashing with proximity
                for idx, line in enumerate(lines):
                    line_no = idx + 1
                    weak_match = WEAK_HASH_REGEX.search(line)
                    if weak_match:
                        # Check password keyword in window of +/- 3 lines
                        win_start = max(0, idx - 3)
                        win_end = min(len(lines), idx + 4)
                        has_pwd = any(PASSWORD_KEYWORD_REGEX.search(lines[j]) for j in range(win_start, win_end))
                        if has_pwd:
                            alg = weak_match.group(1).lower().replace("-", "")
                            dpdp_matches["access control"].append(
                                f"access control (authentication): password hashing found: {alg} ({rel_path_str}:{line_no})"
                            )
                            bp_advisories.append(
                                f"advisory: weak password hashing algorithm '{alg}' detected in {rel_path_str}:{line_no}"
                            )

                    strong_match = STRONG_HASH_REGEX.search(line)
                    if strong_match:
                        alg = strong_match.group(1).lower()
                        # Avoid double-reporting if line has both argon2 and argon2id
                        if "argon2id" in line.lower():
                            alg = "argon2id"
                        dpdp_matches["access control"].append(
                            f"access control (authentication): password hashing found: {alg} ({rel_path_str}:{line_no})"
                        )
                        bp_informational.append(
                            f"informational: recommended password hashing algorithm '{alg}' configured in {rel_path_str}:{line_no}"
                        )
                continue

            # --- 3. Web Server / Nginx Config ---
            if kind == "web_config":
                has_hsts = False
                for idx, line in enumerate(lines):
                    line_no = idx + 1
                    if is_secret_assignment(line):
                        dpdp_matches["committed secrets"].append(
                            f"committed secrets: {rel_path_str}:{line_no}: <line redacted: possible secret>"
                        )

                    if HSTS_HEADER_REGEX.search(line):
                        has_hsts = True
                        dpdp_matches["encryption/transport"].append(
                            f"encryption/transport: Strict-Transport-Security header configured ({rel_path_str}:{line_no})"
                        )
                        bp_informational.append(
                            f"informational: Strict-Transport-Security header configured in {rel_path_str}:{line_no}"
                        )

                    tls_m = TLS_PROTOCOLS_REGEX.search(line)
                    if tls_m:
                        protocols = tls_m.group(1).strip()
                        dpdp_matches["encryption/transport"].append(
                            f"encryption/transport: TLS protocols configured: {protocols} ({rel_path_str}:{line_no})"
                        )

                    if HTTPS_REDIRECT_REGEX.search(line):
                        dpdp_matches["encryption/transport"].append(
                            f"encryption/transport: HTTP to HTTPS redirect configured ({rel_path_str}:{line_no})"
                        )

                if not has_hsts:
                    dpdp_matches["encryption/transport"].append(
                        f"encryption/transport: no Strict-Transport-Security header found in {rel_path_str}"
                    )
                    bp_advisories.append(
                        f"advisory: no Strict-Transport-Security header found in {rel_path_str}"
                    )
                continue

            # --- 4. Storage Rules ---
            if kind == "storage_rules":
                for idx, line in enumerate(lines):
                    line_no = idx + 1
                    if STORAGE_PUBLIC_WRITE_REGEX.search(line):
                        snippet = line.strip()[:80]
                        dpdp_matches["access control"].append(
                            f"access control: storage rules permit public write access ({rel_path_str}:{line_no})"
                        )
                        bp_advisories.append(
                            f"advisory: public write access permitted in storage rules: {rel_path_str}:{line_no} ({snippet})"
                        )
                    elif STORAGE_RESTRICTED_REGEX.search(line):
                        dpdp_matches["access control"].append(
                            f"access control: storage rules restrict access with authorization conditions ({rel_path_str}:{line_no})"
                        )
                        bp_informational.append(
                            f"informational: storage access restricted by authorization conditions in {rel_path_str}:{line_no}"
                        )
                continue

            # --- 5. Logging Configuration ---
            if kind == "logging_config":
                for idx, line in enumerate(lines):
                    line_no = idx + 1
                    ret_m = LOG_RETENTION_REGEX.search(line)
                    if ret_m:
                        days = ret_m.group(1)
                        dpdp_matches["retention settings"].append(
                            f"retention settings: log retention configured for {days} days ({rel_path_str}:{line_no})"
                        )
                        bp_informational.append(
                            f"informational: log retention configured for {days} days in {rel_path_str}:{line_no}"
                        )

                    lvl_m = LOG_LEVEL_REGEX.search(line)
                    if lvl_m:
                        snippet = line.strip()[:80]
                        dpdp_matches["access logging and monitoring"].append(
                            f"access logging and monitoring: logging configuration detected in {rel_path_str}:{line_no} ({snippet})"
                        )
                continue

            # --- 6. Backup Configuration ---
            if kind == "backup_config":
                backup_files_found += 1
                has_enc = False
                for idx, line in enumerate(lines):
                    line_no = idx + 1
                    if BACKUP_ENCRYPTION_REGEX.search(line):
                        has_enc = True
                        dpdp_matches["backups/continuity"].append(
                            f"backups/continuity: encrypted backup configuration found ({rel_path_str}:{line_no})"
                        )
                        bp_informational.append(
                            f"informational: encrypted backup configuration detected in {rel_path_str}:{line_no}"
                        )
                        break
                if not has_enc:
                    dpdp_matches["backups/continuity"].append(
                        f"backups/continuity: unencrypted backup configuration found ({rel_path_str})"
                    )
                    bp_advisories.append(
                        f"advisory: unencrypted backup configuration detected in {rel_path_str}"
                    )
                continue

            # --- 7. Container / Deployment Config ---
            if kind == "container_config":
                for idx, line in enumerate(lines):
                    line_no = idx + 1
                    if is_secret_assignment(line):
                        dpdp_matches["committed secrets"].append(
                            f"committed secrets: {rel_path_str}:{line_no}: <line redacted: possible secret>"
                        )
                continue

    return dpdp_matches, bp_advisories, bp_informational, files_scanned, files_skipped


def evaluate_baseline(app_dir: str | Path) -> Dict[str, Any]:
    """
    Perform technical baseline and safeguards analysis on target directory.
    Returns findings JSON conforming to references/findings-schema.md.
    """
    app_path = Path(app_dir).resolve()
    dpdp_matches, bp_advisories, bp_informational, files_scanned, files_skipped = scan_directory(app_path)

    # -------------------------------------------------------------------------
    # IN-DPDP-013: Reasonable security safeguards and access logging (LAW, assisted)
    # -------------------------------------------------------------------------
    dpdp_notes = (
        f"Rule 6(1) safeguards scan across technical configurations. files scanned ({files_scanned}), files skipped ({files_skipped}). "
        f"Rule 6 gives no numeric standard besides the one-year log retention: encryption, obfuscation, masking or virtual tokens; "
        f"access control; logs and monitoring of access to personal data; continuity measures such as backups; "
        f"retention of such logs and personal data for one year (unless another law requires otherwise); "
        f"security terms in processor contracts; and appropriate technical and organisational measures. "
        f"Log retention: report the detected log retention setting and flag the r.6(1)(e) exception "
        f"('unless compliance with any law for the time being in force requires otherwise') and r.8(3) scope "
        f"('a Data Fiduciary' to retain data, traffic data, and logs for at least one year for Seventh Schedule purposes). "
        f"Rule 6(1) evaluation requires operational and human review. "
        f"Matches in code comments in .js/.ts/.py files are not excluded. "
        f"HSTS may be set elsewhere (included files, CDN, load balancer). "
        f"Formats checked: nginx.conf (*.conf): HSTS header and TLS configuration; "
        f"storage.rules (*.rules): public write permissions and authorization conditions; "
        f"logging.json (*log*.json): log retention days and logging configuration; "
        f"auth code (*.js, *.ts, *.py, *.php with auth/login/password/user/account/signup/session in name): password hashing algorithms; "
        f".env*: committed configuration and secrets. Other file types encountered were not analysed. "
        f"This is not an assessment of the application's security."
    )

    if files_scanned == 0:
        dpdp_result = "unclear"
        dpdp_evidence = ["no recognised files found; nothing assessed"]
    else:
        dpdp_result = "needs-human"  # ALWAYS needs-human when files scanned
        dpdp_evidence = []
        for cat in RULE_6_CATEGORIES:
            items = dpdp_matches.get(cat, [])
            if not items:
                if cat == "committed secrets":
                    dpdp_evidence.append("committed secrets: no committed secrets detected in scanned files")
                elif cat == "backups/continuity":
                    dpdp_evidence.append("backups/continuity: no backup or continuity configuration detected in scanned files")
                else:
                    dpdp_evidence.append(f"{cat}: no matching configuration detected in scanned files")
            elif len(items) <= 5:
                dpdp_evidence.extend(items)
            else:
                dpdp_evidence.extend(items[:5])
                overflow_count = len(items) - 5
                dpdp_evidence.append(f"{cat}: {overflow_count} more matches not shown (total {len(items)})")

    dpdp_finding: Dict[str, Any] = {
        "check_id": "IN-DPDP-013",
        "result": dpdp_result,
        "evidence": dpdp_evidence,
        "notes": dpdp_notes,
    }

    # -------------------------------------------------------------------------
    # IN-BP-003: Technical security baseline configurations (BEST PRACTICE, automated)
    # -------------------------------------------------------------------------
    bp_notes = (
        f"Technical baseline configuration scan. files scanned ({files_scanned}), files skipped ({files_skipped}). "
        f"Technical thresholds (such as TLS 1.3/HSTS, AES-256 for data at rest, Argon2id/bcrypt for password hashing, "
        f"and encrypted backups) are engineering best practices, not statutory standards prescribed by the Act or Rules. "
        f"Matches in code comments in .js/.ts/.py files are not excluded. "
        f"HSTS may be set elsewhere (included files, CDN, load balancer). "
        f"Formats checked: nginx.conf (*.conf): HSTS header and TLS configuration; "
        f"storage.rules (*.rules): public write permissions and authorization conditions; "
        f"logging.json (*log*.json): log retention days and logging configuration; "
        f"auth code (*.js, *.ts, *.py, *.php with auth/login/password/user/account/signup/session in name): password hashing algorithms; "
        f".env*: committed configuration and secrets. Other file types encountered were not analysed. "
        f"This is not an assessment of the application's security."
    )

    if files_scanned == 0:
        bp_evidence = ["no recognised files found; nothing assessed"]
        bp_suggested_fix = None
    else:
        if not bp_advisories:
            bp_evidence = [f"no advisory findings across {files_scanned} scanned files"] + bp_informational
        else:
            bp_evidence = bp_advisories + bp_informational

        # Compile suggested_fix only for advisories actually found
        fixes: List[str] = []
        if any("weak password hashing" in adv for adv in bp_advisories):
            fixes.append("Upgrade password hashing to Argon2id or bcrypt with appropriate work factor.")
        if any("no Strict-Transport-Security header" in adv for adv in bp_advisories):
            fixes.append("Configure Strict-Transport-Security header (e.g. 'max-age=31536000; includeSubDomains; preload') in web server configuration.")
        if any("public write access" in adv for adv in bp_advisories):
            fixes.append("Restrict storage rules to authenticated users or require explicit authorization conditions instead of 'if true'.")
        if any("unencrypted backup" in adv for adv in bp_advisories):
            fixes.append("Enable encryption for database and volume backups.")

        if fixes:
            bp_suggested_fix = "\n".join(f"{i + 1}. {fix}" for i, fix in enumerate(fixes))
        else:
            bp_suggested_fix = None

    bp_finding: Dict[str, Any] = {
        "check_id": "IN-BP-003",
        "result": "informational",
        "evidence": bp_evidence,
        "notes": bp_notes,
    }
    if bp_suggested_fix:
        bp_finding["suggested_fix"] = bp_suggested_fix

    return {
        "findings": [dpdp_finding, bp_finding]
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Privacy Preflight - Technical Security Baseline and Safeguards Analyzer (IN-DPDP-013, IN-BP-003)"
    )
    parser.add_argument("app_dir", help="Path to application directory to scan")
    parser.add_argument(
        "--findings-out",
        default="reports/baseline-findings.json",
        help="Path to output findings JSON (default: reports/baseline-findings.json)",
    )
    args = parser.parse_args()

    app_path = Path(args.app_dir)
    if not app_path.is_dir():
        sys.exit(f"Error: app directory not found: {app_path}")

    doc = evaluate_baseline(app_path)

    out_path = Path(args.findings_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)

    print(f"Baseline findings written to {out_path}")


if __name__ == "__main__":
    main()
