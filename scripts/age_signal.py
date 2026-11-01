#!/usr/bin/env python3
"""
Privacy Preflight - Age Signal and Child-Directed Verification Analyzer (Task 7)

Evaluates onboarding and signup code for age signals under Indian privacy law:
- IN-DPDP-011 (assisted): Verifiable parental consent and age verification signal.
  Under Act s.2(f), 9(1) and Rules r.10-12, Data Fiduciaries must obtain verifiable
  parental consent before processing personal data of children (under 18).

This tool conducts static analysis for presence or absence of:
1. dob_field
2. age_field
3. over_18_toggle
4. parental_branch
and notes detected child-directed keywords as informational context.

This tool NEVER judges legal sufficiency and NEVER outputs 'met' or 'not-met'.
Result is 'needs-human' whenever files are scanned, or 'unclear' if 0 files scanned.

Standard library only. Not legal advice.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

MAX_FILE_SIZE = 1024 * 1024  # 1 MB
SKIP_DIRS = {".git", "node_modules", "reports", "dist", "build", "__pycache__"}
ALLOWED_EXTENSIONS = {
    ".html",
    ".htm",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".vue",
    ".svelte",
    ".php",
    ".py",
    ".json",
}
HTML_COMMENT_EXTENSIONS = {".html", ".htm", ".vue", ".svelte", ".php"}
SIGNAL_KINDS = ["dob_field", "age_field", "over_18_toggle", "parental_branch"]

HTML_COMMENT_REGEX = re.compile(r"<!--[\s\S]*?-->")

# 1. dob_field regexes
DOB_KEYWORDS_REGEX = re.compile(
    r"(?i)\b(?:dob|date[_-]of[_-]birth|birth[_-]?date|birthday|date\s+of\s+birth)\b"
)
DOB_ATTR_REGEX = re.compile(
    r"""(?i)\b(?:name|id|for|placeholder)\s*=\s*["'][^"']*\b(?:dob|date[_-]of[_-]birth|birth[_-]?date|birthday)\b"""
)
DOB_LABEL_REGEX = re.compile(
    r"""(?i)<label\b[^>]*>[^<]*\b(?:date\s+of\s+birth|birth[_-]?date|birthday|dob)\b"""
)
DATE_INPUT_REGEX = re.compile(r"""(?i)\btype\s*=\s*["']date["']""")

# 2. age_field regexes
AGE_ATTR_REGEX = re.compile(r"""(?i)\b(?:name|id|for)\s*=\s*["'](?:your[_-])?age["']""")
AGE_LABEL_REGEX = re.compile(r"""(?i)<label\b[^>]*>(.*?)(?:</label>|$)""")

# 3. over_18_toggle regex
OVER_18_TOGGLE_REGEX = re.compile(
    r"""(?i)(?:\b18\+(?!\d)|\b(?:18\s+or\s+older|over\s+18|at\s+least\s+18|above\s+18|i\s+am\s+(?:at\s+least\s+)?18)\b)"""
)

# 4. parental_branch regex (exact list: parent, guardian, parental consent, guardian_email, parent_email, under 18, minor)
PARENTAL_BRANCH_REGEX = re.compile(
    r"""(?i)\b(?:parental\s+consent|guardian_email|parent_email|under\s+18|parent|guardian|minor)\b"""
)

# Child-directed words (informational notes only)
CHILD_DIRECTED_REGEX = re.compile(r"""(?i)\b(?:kids?|children|child|students?|schools?|teens?)\b""")


def check_dob_field(lines: List[str], i: int) -> bool:
    """
    Check if line i represents a dob_field:
    - Direct attribute match (name, id, for, placeholder with DOB keyword)
    - Label tag match
    - type="date" where a DOB keyword appears within 2 lines before or after
    """
    line = lines[i]
    if DOB_ATTR_REGEX.search(line):
        return True
    if DOB_LABEL_REGEX.search(line):
        return True
    if DATE_INPUT_REGEX.search(line):
        start_idx = max(0, i - 2)
        end_idx = min(len(lines), i + 3)
        for j in range(start_idx, end_idx):
            if DOB_KEYWORDS_REGEX.search(lines[j]):
                return True
    return False


def check_age_field(line: str) -> bool:
    """
    Check if line represents an age_field:
    - Attribute name, id, or for is exactly 'age' or 'your_age'/'your-age'
    - Label text (trimmed, case-insensitive, ignoring trailing colon or asterisk)
      is exactly 'age' or 'your age'
    """
    if AGE_ATTR_REGEX.search(line):
        return True
    m = AGE_LABEL_REGEX.search(line)
    if m:
        label_inner = m.group(1)
        text_only = re.sub(r"<[^>]+>", "", label_inner).strip().rstrip(":* \t").lower()
        if text_only in ("age", "your age"):
            return True
    return False


def check_over_18_toggle(line: str) -> bool:
    """Check if line matches over_18_toggle text."""
    return bool(OVER_18_TOGGLE_REGEX.search(line))


def check_parental_branch(line: str) -> bool:
    """Check if line matches parental_branch text."""
    return bool(PARENTAL_BRANCH_REGEX.search(line))


def extract_child_directed_words(line: str) -> List[str]:
    """Extract child-directed words for informational notes."""
    return [w.lower() for w in CHILD_DIRECTED_REGEX.findall(line)]


def scan_directory(
    app_dir: Path,
) -> Tuple[Dict[str, List[Tuple[str, int, str]]], Set[str], int, int]:
    """
    Walk directory, filter eligible files, strip HTML comments where appropriate,
    and detect signals.
    """
    findings_by_kind: Dict[str, List[Tuple[str, int, str]]] = {
        k: [] for k in SIGNAL_KINDS
    }
    child_words: Set[str] = set()
    files_scanned = 0
    files_skipped = 0

    if not app_dir.is_dir():
        return findings_by_kind, child_words, 0, 0

    for root, dirnames, filenames in os.walk(app_dir, followlinks=False):
        # Prune skipped dirs and symlinked directories
        for d in list(dirnames):
            dir_full = Path(root) / d
            if d in SKIP_DIRS or os.path.islink(dir_full):
                files_skipped += 1
                dirnames.remove(d)

        # Sort filenames for deterministic ordering
        for fname in sorted(filenames):
            file_path = Path(root) / fname

            # 1. Symlink file check
            if os.path.islink(file_path):
                files_skipped += 1
                continue

            # 2. .env* files
            if fname.startswith(".env"):
                files_skipped += 1
                continue

            # 3. File size <= 1 MB
            try:
                if file_path.stat().st_size > MAX_FILE_SIZE:
                    files_skipped += 1
                    continue
            except OSError:
                files_skipped += 1
                continue

            # 4. Extensions check
            ext = file_path.suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                files_skipped += 1
                continue

            # 5. JSON only for signup / onboard
            if ext == ".json":
                fname_lower = fname.lower()
                if "signup" not in fname_lower and "onboard" not in fname_lower:
                    files_skipped += 1
                    continue

            # Read file
            try:
                raw_content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                files_skipped += 1
                continue

            files_scanned += 1

            # Strip HTML comments only for specified extensions, preserving newline counts
            if ext in HTML_COMMENT_EXTENSIONS:
                content = HTML_COMMENT_REGEX.sub(
                    lambda m: "\n" * m.group(0).count("\n"), raw_content
                )
            else:
                content = raw_content

            lines = content.splitlines()
            rel_path_str = file_path.relative_to(app_dir).as_posix()

            for i, line in enumerate(lines):
                line_no = i + 1
                trimmed_snippet = line.strip()[:80]
                if not trimmed_snippet:
                    continue

                if check_dob_field(lines, i):
                    if len(findings_by_kind["dob_field"]) < 3:
                        findings_by_kind["dob_field"].append(
                            (rel_path_str, line_no, trimmed_snippet)
                        )

                if check_age_field(line):
                    if len(findings_by_kind["age_field"]) < 3:
                        findings_by_kind["age_field"].append(
                            (rel_path_str, line_no, trimmed_snippet)
                        )

                if check_over_18_toggle(line):
                    if len(findings_by_kind["over_18_toggle"]) < 3:
                        findings_by_kind["over_18_toggle"].append(
                            (rel_path_str, line_no, trimmed_snippet)
                        )

                if check_parental_branch(line):
                    if len(findings_by_kind["parental_branch"]) < 3:
                        findings_by_kind["parental_branch"].append(
                            (rel_path_str, line_no, trimmed_snippet)
                        )

                for cw in extract_child_directed_words(line):
                    child_words.add(cw)

    return findings_by_kind, child_words, files_scanned, files_skipped


def evaluate_age_signals(app_dir: str | Path) -> Dict[str, Any]:
    """
    Perform age signal analysis on target application directory.
    Returns findings JSON compliant with references/findings-schema.md.
    """
    app_path = Path(app_dir).resolve()
    findings_by_kind, child_words, files_scanned, files_skipped = scan_directory(app_path)

    evidence_lines: List[str] = []
    for kind in SIGNAL_KINDS:
        items = findings_by_kind.get(kind, [])
        if items:
            for rel_path, line_no, snippet in items[:3]:
                evidence_lines.append(f"{rel_path}:{line_no}: {kind}: {snippet}")
        else:
            evidence_lines.append(f"{kind}: not found in scanned files")

    result = "needs-human" if files_scanned > 0 else "unclear"

    child_words_line = (
        f"Child-directed words detected in scanned files (informational only): {', '.join(sorted(child_words))}."
        if child_words
        else "Child-directed words: none detected in scanned files."
    )

    notes = (
        f"Age signal scan across onboarding and signup code. files scanned ({files_scanned}), files skipped ({files_skipped}). "
        f"Presence or absence only. Order of events (age signal before personal data collection) was not assessed. "
        f"A human must confirm whether the application is child-directed or accessible to children. "
        f"Matches in code comments in .js/.ts/.py files are not excluded. "
        f"A match is a presence signal for a human reviewer, not a verified consent branch. "
        f"{child_words_line}"
    )

    return {
        "findings": [
            {
                "check_id": "IN-DPDP-011",
                "result": result,
                "evidence": evidence_lines,
                "notes": notes,
            }
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Privacy Preflight - Age Signal Analyzer (IN-DPDP-011)"
    )
    parser.add_argument("app_dir", help="Path to application directory to scan")
    parser.add_argument(
        "--findings-out",
        default="reports/age-findings.json",
        help="Path to output findings JSON (default: reports/age-findings.json)",
    )
    args = parser.parse_args()

    app_path = Path(args.app_dir)
    if not app_path.is_dir():
        sys.exit(f"Error: app directory not found: {app_path}")

    doc = evaluate_age_signals(app_path)

    out_path = Path(args.findings_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)

    print(f"Age signal findings written to {out_path}")


if __name__ == "__main__":
    main()

