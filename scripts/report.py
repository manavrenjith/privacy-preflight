#!/usr/bin/env python3
"""
Privacy Preflight - Report Generator

Generates markdown and structured JSON findings reports for a given jurisdiction.
Not legal advice; never claims an app meets statutory certification or security standards.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.validate_checks import (
    extract_fenced_yaml_checks,
    format_validation_output,
    load_yaml_file,
    resolve_config_date,
    validate_jurisdiction,
)

PROHIBITED_WORDS = [
    re.compile(r"\bcompliant\b", re.IGNORECASE),
    re.compile(r"\bsecure\b", re.IGNORECASE),
]


def extract_first_sentence(text: str) -> str:
    """Extract the first sentence from a caveats string."""
    cleaned = text.strip()
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    return sentences[0].strip() if sentences else cleaned


def extract_known_limits(markdown_path: Path) -> str:
    """Extract markdown text from '## Known Limits' to the end of the file."""
    if not markdown_path.is_file():
        return ""
    content = markdown_path.read_text(encoding="utf-8")
    idx = content.find("## Known Limits")
    if idx == -1:
        return ""
    return content[idx + len("## Known Limits") :].strip()


def compute_check_status(
    check: Dict[str, Any],
    effective_dates: Dict[str, Any],
    today: datetime.date,
) -> Tuple[str, str]:
    """
    Compute status and category for an active check relative to today's date.
    Returns (status_label, status_category).
    """
    label = check.get("label", "LAW")
    if label == "BEST PRACTICE":
        return ("not a legal requirement", "best_practice")

    af_key = check.get("applies_from")
    af_date = resolve_config_date(effective_dates, af_key) if af_key else None
    au_key = check.get("applies_until")
    au_date = resolve_config_date(effective_dates, au_key) if au_key else None

    oq_list = check.get("open_question_refs", [])
    oq_str = ", ".join(oq_list) if oq_list else "open question"

    if af_date and today < af_date:
        return (f"READINESS from {af_date}", "readiness")
    elif au_date and today >= au_date:
        return (f"UNRESOLVED ({oq_str})", "unresolved")
    elif au_date and today < au_date:
        return (f"IN FORCE NOW until {au_date}, then UNRESOLVED ({oq_str})", "in_force_now")
    else:
        return ("IN FORCE NOW", "in_force_now")


def format_finding_heading(check: Dict[str, Any], status_label: str) -> str:
    """
    Build the exact heading shape:
    [LAW · READINESS from 2027-05-13 · verified 2026-10-29 · official-text, ai-read, human check pending]
    [BEST PRACTICE · not a legal requirement · verified 2026-10-29]
    """
    lv = check.get("last_verified")
    if isinstance(lv, datetime.date):
        lv_str = lv.strftime("%Y-%m-%d")
    else:
        lv_str = str(lv)

    if check.get("label") == "LAW":
        va = check.get("verified_against", "not-verified")
        vb = check.get("verified_by", "ai-read")
        parts = [va, vb]
        if vb == "ai-read":
            parts.append("human check pending")
        v_str = ", ".join(parts)
        return f"[{check['label']} · {status_label} · verified {lv_str} · {v_str}]"
    else:
        return f"[{check['label']} · not a legal requirement · verified {lv_str}]"


def render_finding_markdown(
    finding_data: Dict[str, Any],
    jurisdiction: str = "india",
    verbose: bool = False,
) -> str:
    """Render a single finding block in markdown."""
    lines: List[str] = [
        f"### {finding_data['heading_label']}",
        "",
        f"- **Check:** {finding_data['check_id']}: {finding_data['title']}",
        f"- **Result:** {finding_data['result']}",
        "- **Evidence:**",
    ]
    for ev in finding_data.get("evidence", []):
        lines.append(f"  - `{ev}`")

    if finding_data.get("suggested_fix"):
        lines.append(f"- **Suggested Fix:** {finding_data['suggested_fix']}")
    if finding_data.get("notes"):
        lines.append(f"- **Notes:** {finding_data['notes']}")

    lines.append(f"- **Confidence:** {finding_data.get('confidence', 'medium')}")

    oq_refs = finding_data.get("open_question_refs", [])
    oq_display = ", ".join(oq_refs) if oq_refs else "None"
    lines.append(f"- **Open Questions:** {oq_display}")

    full_caveats = finding_data.get("caveats", "")
    if verbose:
        lines.append(f"- **Caveats:** {full_caveats}")
    else:
        first_sentence = extract_first_sentence(full_caveats)
        cid = finding_data["check_id"]
        pointer = f"Full caveats: references/jurisdictions/{jurisdiction}.md ({cid})"
        if first_sentence:
            lines.append(f"- **Caveats:** {first_sentence} {pointer}")
        else:
            lines.append(f"- **Caveats:** {pointer}")

    lines.append("")
    return "\n".join(lines)


def generate_report(
    findings_path: Path | str,
    jurisdiction: str = "india",
    today: Optional[datetime.date] = None,
    base_dir: Path | str = ".",
    verbose: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate markdown and structured JSON reports.
    Returns (markdown_content, structured_json_dict).
    """
    base_path = Path(base_dir).resolve()
    if today is None:
        today = datetime.date.today()

    # 1. Run validator first. Refuse to render on any failure.
    val_result = validate_jurisdiction(jurisdiction=jurisdiction, today=today, base_dir=base_path)
    if not val_result.is_valid:
        raise ValueError(
            f"Check pack validation failed; refusing to generate report.\n"
            f"{format_validation_output(val_result)}"
        )

    # 2. Load jurisdiction checks and effective dates
    md_path = base_path / "references" / "jurisdictions" / f"{jurisdiction}.md"
    cfg_path = base_path / "config" / "effective-dates.yaml"

    effective_dates = load_yaml_file(cfg_path)
    all_checks = extract_fenced_yaml_checks(md_path)

    checks_by_id: Dict[str, Dict[str, Any]] = {c["id"]: c for c in all_checks}
    proposed_checks = [c for c in all_checks if c.get("status") == "proposed"]
    active_checks = [c for c in all_checks if c.get("status") != "proposed"]
    active_check_ids = {c["id"] for c in active_checks}
    proposed_check_ids = {c["id"] for c in proposed_checks}

    # 3. Load input findings
    findings_file = Path(findings_path)
    if not findings_file.is_file():
        raise FileNotFoundError(f"Findings file not found: {findings_file}")

    with findings_file.open("r", encoding="utf-8") as f:
        raw_findings = json.load(f)

    scan_data: Optional[Dict[str, Any]] = None
    if isinstance(raw_findings, dict):
        if "scan" in raw_findings and isinstance(raw_findings["scan"], dict):
            scan_data = raw_findings["scan"]
        if "findings" in raw_findings and isinstance(raw_findings["findings"], list):
            findings_list = raw_findings["findings"]
        else:
            raise ValueError("Findings JSON dict must contain a 'findings' list")
    elif isinstance(raw_findings, list):
        findings_list = raw_findings
    else:
        raise ValueError("Findings JSON must be a list of finding objects or a dict with a 'findings' key")

    # Validate findings and disallow proposed check findings
    evaluated_active_ids: Set[str] = set()
    processed_findings: List[Dict[str, Any]] = []

    for item in findings_list:
        if not isinstance(item, dict):
            raise ValueError(f"Each finding must be an object, got {type(item).__name__}")
        cid = item.get("check_id")
        if not cid:
            raise ValueError("Finding is missing required 'check_id'")
        if cid in proposed_check_ids:
            raise ValueError(
                f"Finding references proposed check '{cid}'. Proposed checks cannot be evaluated as findings."
            )
        if cid not in active_check_ids:
            raise ValueError(f"Finding references unknown check ID: '{cid}'")

        res = item.get("result")
        if res not in ("met", "not-met", "unclear", "needs-human", "informational"):
            raise ValueError(f"Finding '{cid}' has invalid result '{res}'")

        ev = item.get("evidence")
        if not isinstance(ev, list) or len(ev) == 0:
            raise ValueError(f"Finding '{cid}' must contain a non-empty 'evidence' list")

        check_def = checks_by_id[cid]
        status_label, status_cat = compute_check_status(check_def, effective_dates, today)
        heading_label = format_finding_heading(check_def, status_label)

        pack_conf = check_def.get("confidence", "medium")
        item_conf = item.get("confidence")
        finding_confidence = item_conf if item_conf in ("high", "medium", "low") else pack_conf

        finding_record = {
            "check_id": cid,
            "title": check_def.get("title", ""),
            "label": check_def.get("label", "LAW"),
            "status": status_label,
            "status_category": status_cat,
            "heading_label": heading_label,
            "result": res,
            "evidence": ev,
            "suggested_fix": item.get("suggested_fix"),
            "notes": item.get("notes"),
            "confidence": finding_confidence,
            "caveats": check_def.get("caveats", ""),
            "open_question_refs": check_def.get("open_question_refs", []),
            "last_verified": str(check_def.get("last_verified", "")),
            "verified_against": check_def.get("verified_against", ""),
            "verified_by": check_def.get("verified_by", ""),
        }
        processed_findings.append(finding_record)
        evaluated_active_ids.add(cid)

    # 4. Check for staleness (> 90 days before today)
    stale_checks: List[Tuple[str, str, int]] = []
    for c in all_checks:
        lv = c.get("last_verified")
        if isinstance(lv, str):
            lv = datetime.datetime.strptime(lv, "%Y-%m-%d").date()
        if isinstance(lv, datetime.date):
            days_old = (today - lv).days
            if days_old > 90:
                stale_checks.append((c["id"], lv.strftime("%Y-%m-%d"), days_old))

    # 5. Partition findings into sections
    in_force_findings: List[Dict[str, Any]] = []
    readiness_findings: List[Dict[str, Any]] = []
    unresolved_findings: List[Dict[str, Any]] = []
    informational_findings: List[Dict[str, Any]] = []
    best_practice_findings: List[Dict[str, Any]] = []
    needs_human_findings: List[Dict[str, Any]] = []

    for f in processed_findings:
        if f["result"] in ("needs-human", "unclear"):
            needs_human_findings.append(f)
        elif f["check_id"] == "IN-BP-004" or (f["result"] == "informational" and f["label"] != "BEST PRACTICE"):
            informational_findings.append(f)
        elif f["label"] == "BEST PRACTICE":
            best_practice_findings.append(f)
        elif f["label"] == "LAW":
            if f["status_category"] == "in_force_now":
                in_force_findings.append(f)
            elif f["status_category"] == "readiness":
                readiness_findings.append(f)
            elif f["status_category"] == "unresolved":
                unresolved_findings.append(f)

    # 6. Not run checks
    not_run_checks = [c for c in active_checks if c["id"] not in evaluated_active_ids]

    # 7. Not verified checks: list only active LAW checks whose verified_against is not official-text
    not_verified_checks = [
        c for c in active_checks
        if c.get("label") == "LAW" and c.get("verified_against") != "official-text"
    ]

    # 8. Human check pending checks
    human_pending_checks = [
        c for c in active_checks if c.get("label") == "LAW" and c.get("verified_by") == "ai-read"
    ]

    # 9. Not covered (raw known limits text for JSON output)
    full_known_limits = extract_known_limits(md_path)

    # 10. Summary result counts among those run
    result_counts = {
        "met": 0,
        "not-met": 0,
        "unclear": 0,
        "needs-human": 0,
        "informational": 0,
    }
    for f in processed_findings:
        r = f["result"]
        if r in result_counts:
            result_counts[r] += 1

    # Build Markdown Document
    md_lines: List[str] = [
        f"# Privacy Preflight Findings Report: {jurisdiction.capitalize()}",
        "",
        f"- **Evaluation Date:** {today.strftime('%Y-%m-%d')}",
        (
            "  Note: Dates assume 13 Nov / 13 May per official gazette datelines; "
            "upload metadata indicates a possible one-day variance (open question Q1)."
        ),
        f"- **Jurisdiction:** {jurisdiction}",
    ]

    if scan_data is not None:
        def _scan_val(k: str) -> Any:
            v = scan_data.get(k)
            return "not reported" if v is None else v

        crawled = _scan_val("pages_crawled")
        max_d = _scan_val("max_depth_reached")
        skipped = _scan_val("pages_skipped")
        failed = _scan_val("pages_failed")
        interactions = _scan_val("interactions")
        md_lines.append(
            f"- **Scan coverage:** pages crawled: {crawled}, "
            f"max depth: {max_d}, "
            f"skipped: {skipped}, "
            f"failed: {failed}; "
            f"interactions: {interactions}"
        )

    md_lines.append("")

    # Summary block directly under header
    md_lines.append("## Summary")
    md_lines.append("")
    md_lines.append(f"- **Active Checks:** {len(active_checks)}")
    md_lines.append(f"- **Checks Run:** {len(processed_findings)}")
    md_lines.append(f"- **Checks Not Run:** {len(not_run_checks)}")
    md_lines.append("- **Results:**")
    md_lines.append(f"  - met: {result_counts['met']}")
    md_lines.append(f"  - not-met: {result_counts['not-met']}")
    md_lines.append(f"  - unclear: {result_counts['unclear']}")
    md_lines.append(f"  - needs-human: {result_counts['needs-human']}")
    md_lines.append(f"  - informational: {result_counts['informational']}")
    md_lines.append("")

    # Section 1: Staleness warning (only if any last_verified is > 90 days)
    if stale_checks:
        md_lines.append("## Staleness Warning")
        md_lines.append("")
        md_lines.append("> **Warning:** The following checks have verification dates older than 90 days:")
        for cid, date_str, days_old in stale_checks:
            md_lines.append(f"> - `{cid}`: last verified {date_str} ({days_old} days old)")
        md_lines.append("")

    # Section 2: In force now
    md_lines.append("## In Force Now")
    md_lines.append("")
    if in_force_findings:
        for f in in_force_findings:
            md_lines.append(render_finding_markdown(f, jurisdiction=jurisdiction, verbose=verbose))
    else:
        md_lines.append("No findings of this kind among the checks that ran.")
        md_lines.append("")

    # Section 3: Readiness
    md_lines.append("## Readiness")
    md_lines.append("")
    if readiness_findings:
        for f in readiness_findings:
            md_lines.append(render_finding_markdown(f, jurisdiction=jurisdiction, verbose=verbose))
    else:
        md_lines.append("No findings of this kind among the checks that ran.")
        md_lines.append("")

    # Section 4: Unresolved
    md_lines.append("## Unresolved")
    md_lines.append("")
    if unresolved_findings:
        for f in unresolved_findings:
            md_lines.append(render_finding_markdown(f, jurisdiction=jurisdiction, verbose=verbose))
    else:
        md_lines.append("No findings of this kind among the checks that ran.")
        md_lines.append("")

    # Section 5: Informational inventory
    md_lines.append("## Informational Inventory")
    md_lines.append("")
    if informational_findings:
        for f in informational_findings:
            md_lines.append(render_finding_markdown(f, jurisdiction=jurisdiction, verbose=verbose))
    else:
        md_lines.append("No findings of this kind among the checks that ran.")
        md_lines.append("")

    # Section 6: Best practice
    md_lines.append("## Best Practice")
    md_lines.append("")
    if best_practice_findings:
        for f in best_practice_findings:
            md_lines.append(render_finding_markdown(f, jurisdiction=jurisdiction, verbose=verbose))
    else:
        md_lines.append("No findings of this kind among the checks that ran.")
        md_lines.append("")

    # Section 7: Needs human or legal judgment
    md_lines.append("## Needs Human or Legal Judgment")
    md_lines.append("")
    if needs_human_findings:
        for f in needs_human_findings:
            md_lines.append(render_finding_markdown(f, jurisdiction=jurisdiction, verbose=verbose))
    else:
        md_lines.append("No findings of this kind among the checks that ran.")
        md_lines.append("")

    # Section 8: Not run (active checks with no finding supplied)
    md_lines.append("## Not Run")
    md_lines.append("")
    if not_run_checks:
        md_lines.append("The following active checks had no findings supplied in the evaluation:")
        for c in not_run_checks:
            md_lines.append(f"- **{c['id']}**: {c.get('title', '')}")
    else:
        md_lines.append("None. All active checks were evaluated.")
    md_lines.append("")

    # Section 9: Proposed checks (not active)
    md_lines.append("## Proposed Checks (Not Active)")
    md_lines.append("")
    if proposed_checks:
        md_lines.append("The following checks are drafted as proposed and are not active in the v0.1 evaluation:")
        for c in proposed_checks:
            md_lines.append(f"- **{c['id']}**: {c.get('title', '')}")
    else:
        md_lines.append("None.")
    md_lines.append("")

    # Section 10: Not verified (only LAW checks whose verified_against is not official-text)
    md_lines.append("## Not Verified")
    md_lines.append("")
    if not_verified_checks:
        md_lines.append("The following checks are not verified against official texts:")
        for c in not_verified_checks:
            md_lines.append(f"- **{c['id']}**: {c.get('title', '')} (source: {c.get('verified_against', 'not-verified')})")
    else:
        md_lines.append("None.")
    md_lines.append("")

    # Section 11: Human check pending
    md_lines.append("## Human Check Pending")
    md_lines.append("")
    if human_pending_checks:
        md_lines.append("The following LAW checks were read by an AI model and have human spot-checks pending:")
        for c in human_pending_checks:
            md_lines.append(f"- **{c['id']}**: {c.get('title', '')} (ai-read)")
    else:
        md_lines.append("None.")
    md_lines.append("")

    # Section 12: Not covered by this scan
    md_lines.append("## Not Covered by This Scan")
    md_lines.append("")
    not_run_ids_str = ", ".join(c["id"] for c in not_run_checks) if not_run_checks else "none"
    md_lines.append("- Other jurisdictions")
    md_lines.append("- Sector rules (health, telecom, SEBI, insurance)")
    md_lines.append("- E-commerce rules")
    md_lines.append("- Intermediary rules")
    md_lines.append(f"- checks not run: {not_run_ids_str}")
    md_lines.append("")

    # Section 13: Limits of the legal research
    md_lines.append("## Limits of the Legal Research")
    md_lines.append("")
    md_lines.append(
        f"- Primary texts were read by an AI model and human checks are pending (see research/{jurisdiction}/verification-log.md)."
    )
    md_lines.append(
        "- Statements that a notification has not been issued come from secondary sources, not a direct e-Gazette search."
    )
    md_lines.append(
        "- The 13 vs 14 November date variance (Q1)."
    )
    md_lines.append("")
    md_lines.append(f"Full Known Limits: references/jurisdictions/{jurisdiction}.md")
    md_lines.append("")

    # Section 14: Closing Line
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("This report lists findings. It is not legal advice and it does not certify anything.")

    markdown_output = "\n".join(md_lines)

    # Build Structured JSON Output
    json_output: Dict[str, Any] = {
        "jurisdiction": jurisdiction,
        "evaluation_date": today.strftime("%Y-%m-%d"),
        "disclaimer": "This report lists findings. It is not legal advice and it does not certify anything.",
        "date_variance_note": (
            "Dates assume 13 Nov / 13 May per official gazette datelines; "
            "upload metadata indicates a possible one-day variance (open question Q1)."
        ),
        "summary": {
            "active_checks": len(active_checks),
            "checks_run": len(processed_findings),
            "checks_not_run": len(not_run_checks),
            "results": result_counts,
        },
        "scan": scan_data,
        "staleness_warning": (
            [{"check_id": c, "last_verified": d, "days_old": o} for c, d, o in stale_checks]
            if stale_checks
            else None
        ),
        "sections": {
            "in_force_now": in_force_findings,
            "readiness": readiness_findings,
            "unresolved": unresolved_findings,
            "informational_inventory": informational_findings,
            "best_practice": best_practice_findings,
            "needs_human_or_legal_judgment": needs_human_findings,
        },
        "not_run": [{"check_id": c["id"], "title": c.get("title", "")} for c in not_run_checks],
        "proposed_checks": [{"check_id": c["id"], "title": c.get("title", "")} for c in proposed_checks],
        "not_verified": [
            {"check_id": c["id"], "title": c.get("title", ""), "verified_against": c.get("verified_against", "")}
            for c in not_verified_checks
        ],
        "human_check_pending": [
            {"check_id": c["id"], "title": c.get("title", "")} for c in human_pending_checks
        ],
        "not_covered": full_known_limits,
        "not_covered_by_this_scan": [
            "Other jurisdictions",
            "Sector rules (health, telecom, SEBI, insurance)",
            "E-commerce rules",
            "Intermediary rules",
            f"checks not run: {not_run_ids_str}",
        ],
        "limits_of_legal_research": [
            f"Primary texts were read by an AI model and human checks are pending (see research/{jurisdiction}/verification-log.md).",
            "Statements that a notification has not been issued come from secondary sources, not a direct e-Gazette search.",
            "The 13 vs 14 November date variance (Q1).",
        ],
        "known_limits_reference": f"references/jurisdictions/{jurisdiction}.md",
    }

    # Verify negative constraints: no compliant, no secure
    for pattern in PROHIBITED_WORDS:
        match_md = pattern.search(markdown_output)
        if match_md:
            raise ValueError(f"Prohibited word '{match_md.group(0)}' found in generated markdown report")
        json_dump = json.dumps(json_output)
        match_js = pattern.search(json_dump)
        if match_js:
            raise ValueError(f"Prohibited word '{match_js.group(0)}' found in generated JSON report")

    return (markdown_output, json_output)


def main(argv: Optional[List[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = argparse.ArgumentParser(description="Generate privacy preflight findings report.")
    parser.add_argument("--findings", required=True, help="Path to JSON findings file")
    parser.add_argument("--jurisdiction", default="india", help="Jurisdiction name (default: india)")
    parser.add_argument("--today", default=None, help="Evaluation date YYYY-MM-DD (default: system date)")
    parser.add_argument("--out", default=None, help="Output markdown report file path")
    parser.add_argument("--json", dest="json_out", default=None, help="Output JSON report file path")
    parser.add_argument("--base-dir", default=".", help="Base workspace directory (default: current directory)")
    parser.add_argument("--verbose", action="store_true", help="Print full caveats in markdown report")

    args = parser.parse_args(argv)

    today = None
    if args.today:
        try:
            today = datetime.datetime.strptime(args.today, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format for --today: '{args.today}', expected YYYY-MM-DD", file=sys.stderr)
            return 1

    try:
        md_report, json_report = generate_report(
            findings_path=args.findings,
            jurisdiction=args.jurisdiction,
            today=today,
            base_dir=args.base_dir,
            verbose=args.verbose,
        )
    except ValueError as e:
        print(f"Validation Error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"File Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        return 1

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md_report, encoding="utf-8")
        print(f"Markdown report written to: {out_path}")
    else:
        print(md_report)

    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(json_report, indent=2), encoding="utf-8")
        print(f"JSON report written to: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
