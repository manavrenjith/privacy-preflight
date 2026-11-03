#!/usr/bin/env python3
"""
Privacy Preflight - Check Validator

Validates jurisdiction checks in references/jurisdictions/<jurisdiction>.md
against references/check-schema.md, config/effective-dates.yaml, and
research/<jurisdiction>/ verification sources.
Not legal advice; never claims an app is "compliant".
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml


ID_PATTERN = re.compile(r"^[A-Z]{2}-[A-Z0-9]+-[0-9]{3}$")
COMPLIANT_WORD_PATTERN = re.compile(r"\bcompliant\b", re.IGNORECASE)

REQUIRED_FIELDS = [
    "id",
    "title",
    "label",
    "provision",
    "applies_from",
    "last_verified",
    "verified_against",
    "verified_by",
    "confidence",
    "caveats",
    "open_question_refs",
    "detection_type",
    "detection",
    "pass_criteria",
]


@dataclass
class ValidationIssue:
    check_id: str
    rule: str
    message: str


@dataclass
class ValidationResult:
    failures: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    active_law_count: int = 0
    active_bp_count: int = 0
    proposed_count: int = 0
    total_checks: int = 0
    proposed_checks: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.failures) == 0


def load_yaml_file(path: Path) -> Any:
    """Load and parse a YAML file."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing required file: {path}. "
            "Reinstall the skill with all its folders (scripts, references, config, research); do not create this file."
        )
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_config_date(config_dict: Dict[str, Any], key_path: str) -> Optional[datetime.date]:
    """Resolve a dot-notation key in config_dict to a datetime.date."""
    if not key_path or not isinstance(key_path, str):
        return None
    parts = key_path.split(".")
    cur: Any = config_dict
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    if isinstance(cur, datetime.date):
        return cur
    if isinstance(cur, str):
        try:
            return datetime.datetime.strptime(cur, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def load_verification_log(log_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Parse research/<jurisdiction>/verification-log.md markdown table 1.
    Returns mapping from check_id to metadata dict {'verified_by': ..., 'row_id': ...}.
    """
    if not log_path.is_file():
        raise FileNotFoundError(
            f"Missing required verification log: {log_path}. "
            "Reinstall the skill with all its folders (scripts, references, config, research); do not create this file."
        )

    log_entries: Dict[str, Dict[str, str]] = {}
    with log_path.open("r", encoding="utf-8") as f:
        in_table_1 = False
        for line in f:
            line_str = line.strip()
            if line_str.startswith("# Verification log"):
                in_table_1 = True
                continue
            if line_str.startswith("## Second cross-check"):
                in_table_1 = False
                break
            if in_table_1 and line_str.startswith("|"):
                parts = [p.strip() for p in line_str.split("|")[1:-1]]
                if len(parts) >= 5 and re.match(r"^[A-Z]{2}-[A-Z0-9]+-[0-9]{3}", parts[0]):
                    raw_id = parts[0]
                    verified_against = parts[3]
                    verified_by = parts[4]
                    clean_id = re.sub(r"\s*\(.*?\)", "", raw_id).strip()
                    entry = {
                        "row_id": raw_id,
                        "verified_against": verified_against,
                        "verified_by": verified_by,
                    }
                    log_entries[clean_id] = entry
                    log_entries[raw_id] = entry
    return log_entries


def load_open_questions(oq_path: Path) -> Set[str]:
    """Parse research/<jurisdiction>/open-questions.md for '## Q<n>.' headings."""
    if not oq_path.is_file():
        raise FileNotFoundError(
            f"Missing required open-questions file: {oq_path}. "
            "Reinstall the skill with all its folders (scripts, references, config, research); do not create this file."
        )

    q_ids: Set[str] = set()
    with oq_path.open("r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^##\s+(Q\d+)\.", line.strip())
            if m:
                q_ids.add(m.group(1))
    return q_ids


def extract_fenced_yaml_checks(markdown_path: Path) -> List[Dict[str, Any]]:
    """Extract all fenced yaml blocks in markdown_path that contain an 'id:' field."""
    if not markdown_path.is_file():
        raise FileNotFoundError(
            f"Missing required jurisdiction file: {markdown_path}. "
            "Reinstall the skill with all its folders (scripts, references, config, research); do not create this file."
        )

    with markdown_path.open("r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.findall(r"```yaml\s*\n(.*?)\n```", content, re.DOTALL)
    checks: List[Dict[str, Any]] = []
    for b in blocks:
        try:
            data = yaml.safe_load(b)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parse error in block:\n{b}\nError: {e}") from e
        if isinstance(data, dict) and "id" in data:
            checks.append(data)
    return checks


def validate_check_item(
    check: Dict[str, Any],
    effective_dates: Dict[str, Any],
    verification_log: Dict[str, Dict[str, str]],
    open_questions: Set[str],
    today: datetime.date,
    seen_ids: Set[str],
    result: ValidationResult,
) -> None:
    """Validate a single check against all rules."""
    cid = check.get("id", "<missing-id>")

    # 1. Required fields
    for field_name in REQUIRED_FIELDS:
        if field_name not in check or check[field_name] is None:
            result.failures.append(
                ValidationIssue(cid, "required-fields", f"missing required field '{field_name}'")
            )

    # 2. ID pattern and uniqueness
    if not isinstance(cid, str) or not ID_PATTERN.match(cid):
        result.failures.append(
            ValidationIssue(cid, "id-pattern", f"id '{cid}' does not match pattern '^[A-Z]{{2}}-[A-Z0-9]+-[0-9]{{3}}$'")
        )
    if cid in seen_ids:
        result.failures.append(
            ValidationIssue(cid, "id-unique", f"duplicate check id '{cid}'")
        )
    seen_ids.add(cid)

    # 3. Label value
    label = check.get("label")
    if label not in ("LAW", "BEST PRACTICE"):
        result.failures.append(
            ValidationIssue(cid, "label-value", f"label must be 'LAW' or 'BEST PRACTICE', got '{label}'")
        )

    # 4. LAW check rules
    if label == "LAW":
        prov = check.get("provision")
        if not prov or not isinstance(prov, str) or prov.strip() == "" or prov == "none (engineering practice)":
            result.failures.append(
                ValidationIssue(
                    cid,
                    "law-provision",
                    "LAW entries must cite a valid legal provision, cannot be 'none (engineering practice)' or empty",
                )
            )

        va = check.get("verified_against")
        if va == "n/a" or va not in ("official-text", "mirror", "secondary", "not-verified"):
            result.failures.append(
                ValidationIssue(
                    cid,
                    "law-verified-against",
                    f"LAW entries must have verified_against in ('official-text', 'mirror', 'secondary', 'not-verified'), got '{va}'",
                )
            )

        af = check.get("applies_from")
        if af == "none":
            result.failures.append(
                ValidationIssue(
                    cid,
                    "law-applies-from",
                    "LAW entries must reference a valid config key in config/effective-dates.yaml, cannot be 'none'",
                )
            )
        else:
            af_date = resolve_config_date(effective_dates, af)
            if af_date is None:
                result.failures.append(
                    ValidationIssue(
                        cid,
                        "law-applies-from",
                        f"applies_from '{af}' is not a valid date key in config/effective-dates.yaml",
                    )
                )

    # 5. BEST PRACTICE rules
    if label == "BEST PRACTICE":
        prov = check.get("provision")
        if prov != "none (engineering practice)":
            result.failures.append(
                ValidationIssue(
                    cid,
                    "bp-provision",
                    f"BEST PRACTICE entries must have provision exactly 'none (engineering practice)', got '{prov}'",
                )
            )

        va = check.get("verified_against")
        if va != "n/a":
            result.failures.append(
                ValidationIssue(
                    cid,
                    "bp-verified-against",
                    f"BEST PRACTICE entries must have verified_against 'n/a', got '{va}'",
                )
            )

        af = check.get("applies_from")
        if af != "none":
            result.failures.append(
                ValidationIssue(
                    cid,
                    "bp-applies-from",
                    f"BEST PRACTICE entries must have applies_from 'none', got '{af}'",
                )
            )

        if "applies_until" in check and check["applies_until"] is not None:
            result.failures.append(
                ValidationIssue(
                    cid,
                    "bp-applies-until-absent",
                    f"BEST PRACTICE entries must not have applies_until, found '{check['applies_until']}'",
                )
            )

    # 6. applies_until (LAW only)
    if "applies_until" in check and check["applies_until"] is not None:
        au = check["applies_until"]
        if label != "LAW":
            result.failures.append(
                ValidationIssue(cid, "applies-until-law-only", "applies_until is allowed only on LAW entries")
            )
        else:
            au_date = resolve_config_date(effective_dates, au)
            if au_date is None:
                result.failures.append(
                    ValidationIssue(
                        cid,
                        "applies-until-key-exists",
                        f"applies_until key '{au}' does not exist in config/effective-dates.yaml",
                    )
                )
            else:
                af = check.get("applies_from")
                af_date = resolve_config_date(effective_dates, af) if af else None
                if af_date is not None and au_date <= af_date:
                    result.failures.append(
                        ValidationIssue(
                            cid,
                            "applies-until-later",
                            f"applies_until date ({au_date}) must be later than applies_from date ({af_date})",
                        )
                    )

    # 7. Verification log parity
    va = check.get("verified_against")
    if va == "official-text":
        if cid not in verification_log:
            result.failures.append(
                ValidationIssue(
                    cid,
                    "official-text-log-row",
                    f"verified_against is 'official-text' but check id '{cid}' was not found in verification log",
                )
            )
        else:
            vb = check.get("verified_by")
            log_vb = verification_log[cid].get("verified_by")
            if vb == "human-read" and log_vb != "human-read":
                result.failures.append(
                    ValidationIssue(
                        cid,
                        "human-read-log-row",
                        f"verified_by is 'human-read' but verification log row for '{cid}' records '{log_vb}'",
                    )
                )
            if vb not in ("ai-read", "human-read"):
                result.failures.append(
                    ValidationIssue(
                        cid,
                        "verified-by-value",
                        f"verified_by must be 'ai-read' or 'human-read', got '{vb}'",
                    )
                )

    # 8. Open question references
    oq_refs = check.get("open_question_refs")
    if isinstance(oq_refs, list):
        for q in oq_refs:
            if q not in open_questions:
                result.failures.append(
                    ValidationIssue(
                        cid,
                        "open-questions-exist",
                        f"open_question_refs contains '{q}' which does not exist as a '## {q}.' heading in open-questions.md",
                    )
                )
    elif oq_refs is not None:
        result.failures.append(
            ValidationIssue(
                cid,
                "open-questions-format",
                f"open_question_refs must be a list, got {type(oq_refs).__name__}",
            )
        )

    # 9. last_verified date validation
    lv = check.get("last_verified")
    lv_date: Optional[datetime.date] = None
    if isinstance(lv, datetime.date):
        lv_date = lv
    elif isinstance(lv, str):
        try:
            lv_date = datetime.datetime.strptime(lv, "%Y-%m-%d").date()
        except ValueError:
            result.failures.append(
                ValidationIssue(
                    cid,
                    "last-verified-format",
                    f"last_verified '{lv}' is not a valid date in YYYY-MM-DD format",
                )
            )
    elif lv is not None:
        result.failures.append(
            ValidationIssue(
                cid,
                "last-verified-format",
                f"last_verified must be a date string YYYY-MM-DD, got {type(lv).__name__}",
            )
        )

    if lv_date is not None:
        if lv_date > today:
            result.failures.append(
                ValidationIssue(
                    cid,
                    "last-verified-future",
                    f"last_verified date ({lv_date}) is in the future relative to today ({today})",
                )
            )
        elif (today - lv_date).days > 90:
            result.warnings.append(
                ValidationIssue(
                    cid,
                    "last-verified-stale",
                    f"last_verified date ({lv_date}) is more than 90 days before today ({today}) ({(today - lv_date).days} days old)",
                )
            )

    # 10. Prohibited "compliant" wording
    title = check.get("title", "")
    if isinstance(title, str) and COMPLIANT_WORD_PATTERN.search(title):
        result.failures.append(
            ValidationIssue(
                cid,
                "no-compliant-wording",
                f"title contains prohibited word 'compliant': '{title}'",
            )
        )
    pass_criteria = check.get("pass_criteria", "")
    if isinstance(pass_criteria, str) and COMPLIANT_WORD_PATTERN.search(pass_criteria):
        result.failures.append(
            ValidationIssue(
                cid,
                "no-compliant-wording",
                "pass_criteria contains prohibited word 'compliant'",
            )
        )

    # 11. Additional field enum validations
    conf = check.get("confidence")
    if conf not in ("high", "medium", "low"):
        result.failures.append(
            ValidationIssue(
                cid,
                "confidence-value",
                f"confidence must be 'high', 'medium', or 'low', got '{conf}'",
            )
        )

    dt = check.get("detection_type")
    if dt not in ("automated", "assisted", "human-judgment"):
        result.failures.append(
            ValidationIssue(
                cid,
                "detection-type-value",
                f"detection_type must be 'automated', 'assisted', or 'human-judgment', got '{dt}'",
            )
        )

    status = check.get("status", "active")
    if status not in ("active", "proposed", "deprecated"):
        result.failures.append(
            ValidationIssue(
                cid,
                "status-value",
                f"status must be 'active', 'proposed', or 'deprecated', got '{status}'",
            )
        )

    # Counts
    result.total_checks += 1
    if status == "proposed":
        result.proposed_count += 1
        result.proposed_checks.append(check)
    else:
        if label == "LAW":
            result.active_law_count += 1
        elif label == "BEST PRACTICE":
            result.active_bp_count += 1


def validate_jurisdiction(
    jurisdiction: str = "india",
    today: Optional[datetime.date] = None,
    base_dir: Path | str = ".",
) -> ValidationResult:
    """Validate a jurisdiction pack within base_dir."""
    base_path = Path(base_dir).resolve()
    if today is None:
        today = datetime.date.today()

    research_dir = base_path / "research" / jurisdiction
    if not research_dir.is_dir():
        raise FileNotFoundError(
            f"Missing required research directory: {research_dir}. "
            "Reinstall the skill with all its folders (scripts, references, config, research); do not create this file."
        )

    markdown_path = base_path / "references" / "jurisdictions" / f"{jurisdiction}.md"
    config_path = base_path / "config" / "effective-dates.yaml"
    verification_log_path = research_dir / "verification-log.md"
    open_questions_path = research_dir / "open-questions.md"

    effective_dates = load_yaml_file(config_path)
    verification_log = load_verification_log(verification_log_path)
    open_questions = load_open_questions(open_questions_path)
    checks = extract_fenced_yaml_checks(markdown_path)

    result = ValidationResult()
    seen_ids: Set[str] = set()

    for check in checks:
        validate_check_item(
            check=check,
            effective_dates=effective_dates,
            verification_log=verification_log,
            open_questions=open_questions,
            today=today,
            seen_ids=seen_ids,
            result=result,
        )

    return result


def format_validation_output(result: ValidationResult) -> str:
    """Format validation result into text output."""
    lines: List[str] = []
    for f in result.failures:
        lines.append(f"FAIL [{f.check_id}] rule '{f.rule}': {f.message}")
    for w in result.warnings:
        lines.append(f"WARN [{w.check_id}] rule '{w.rule}': {w.message}")

    if result.proposed_checks:
        lines.append("")
        lines.append("Proposed checks (not active):")
        for p in result.proposed_checks:
            lines.append(f"  - {p.get('id')}: {p.get('title')}")

    lines.append("")
    lines.append("Validation Summary:")
    lines.append(f"  Active LAW checks:          {result.active_law_count}")
    lines.append(f"  Active BEST PRACTICE checks: {result.active_bp_count}")
    lines.append(f"  Proposed checks:            {result.proposed_count}")
    lines.append(f"  Total checks validated:     {result.total_checks}")
    lines.append(f"  Total failures:             {len(result.failures)}")
    lines.append(f"  Total warnings:             {len(result.warnings)}")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate jurisdiction checks against schema, dates, and verification sources."
    )
    parser.add_argument(
        "--jurisdiction",
        default="india",
        help="Jurisdiction name to validate (default: india)",
    )
    parser.add_argument(
        "--today",
        default=None,
        help="Evaluation date in YYYY-MM-DD format (default: system date)",
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Base workspace directory (default: current directory)",
    )

    args = parser.parse_args(argv)

    today = None
    if args.today:
        try:
            today = datetime.datetime.strptime(args.today, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format for --today: '{args.today}', expected YYYY-MM-DD", file=sys.stderr)
            return 1

    try:
        result = validate_jurisdiction(
            jurisdiction=args.jurisdiction,
            today=today,
            base_dir=args.base_dir,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error during validation: {e}", file=sys.stderr)
        return 1

    print(format_validation_output(result))
    return 0 if result.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())

