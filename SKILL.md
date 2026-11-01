---
name: privacy-preflight
description: "Scans a web app (code and running pages) for privacy-readiness issues and writes an honest findings report: third-party data flows, consent controls, notice and contact pages, rights and grievance routes, age signals at signup, and a security baseline. Use whenever the user is building, reviewing or about to launch an app with signup, analytics, third-party scripts or user data, or mentions DPDP, SPDI, privacy law, privacy policy, consent banner, age gate, or a pre-launch privacy check. Currently covers India. Reports findings only, never certifies compliance, and is not legal advice."
---

# Privacy Preflight

Evaluates web applications against statutory privacy requirements and engineering baselines under Indian privacy law.

## 1. When to Use / When Not to Use

### When to Use
- Building, reviewing, or preparing to launch a web app with user signup, analytics, third-party scripts, or personal data handling.
- Reviewing privacy readiness under Indian law (DPDP Act, SPDI Rules), privacy notices, consent controls, or age verification signals.

### When Not to Use
- **Code scope:** Code checks (age signal, baseline) cover web stacks only. Mobile-only or native apps (Dart/Flutter, Kotlin/Android, Swift/iOS) are not recognised.
- **Jurisdiction scope:** Only India is currently covered.
- **Unauthorized scanning:** Never scan sites, ports, or code without explicit user permission and ownership.

## 2. Safety Precautions
- **Never start the user's application:** The user must start and host their own site.
- **Never install app dependencies:** Do not run `npm install`, `pip install -r`, or application build steps. If Playwright is missing, show the user the two commands from preflight's output (`pip install playwright` and `playwright install chromium`) and let them run them.
- **Verify serving port:** Always ask or confirm the port actually serving the running site before crawling.
- **Target authorization:** Only scan repositories and running sites the user owns or is explicitly authorized to test.
- **Code integrity:** Never modify the user's codebase unless explicitly instructed.

## 3. Step 1: Jurisdiction Check
1. Ask the user which countries their users reside in.
2. If the user base is outside India, state that only India is currently covered and stop.
3. If India applies, load only `references/jurisdictions/india.md` for check specifications.

## 4. Step 2: Run Preflight Scanner

Run `scripts/preflight.py` pointing to the application directory:

```bash
python scripts/preflight.py <app_directory> [--url <running_url>] [--out <output_json>] [--report] [--today <YYYY-MM-DD>]
```
Example:
```bash
python scripts/preflight.py ./my-app --url http://127.0.0.1:8000 --report
```

- `app_directory`: Local codebase path (required).
- `--url`: URL of the locally running application (e.g. `http://127.0.0.1:8000`). Only supply `--url` if the site is already running and owned by the user.
- `--out`: Path to write merged findings JSON (default: `reports/findings.json`).
- `--report`: Renders the markdown report to standard output immediately after writing findings.
- `--today`: Overrides evaluation date in `YYYY-MM-DD` format.

**Execution Scope:**
- **Static analyzers (always run):** `age_signal` (IN-DPDP-011) and `baseline` (IN-DPDP-013, IN-BP-003).
- **Dynamic analyzers (require `--url`):** `crawl` (IN-BP-004, IN-BP-001, IN-DPDP-004, IN-BP-002) and `pages` (IN-DPDP-002, IN-DPDP-008, IN-DPDP-009, IN-DPDP-010, IN-SPDI-001).

### Failure Handling
- If Playwright or Chromium is missing, `preflight.py` prints install instructions (`pip install playwright` and `playwright install chromium`) and continues without crawl/pages checks.
- If the crawl fails, `preflight.py` prints `crawl failed: <type>; crawl and pages checks not run`, exits with code 1, still writes static findings to the JSON destination, and lists the 9 crawl/pages checks under Not Run. Report this error directly to the user; do not retry blindly.

## 5. Step 3: Assisted Checks Review (IN-DPDP-011, IN-DPDP-013)
For checks labeled with `detection_type: assisted`, automated tools cannot determine statutory sufficiency:
- **IN-DPDP-011 (Age Signal):** Inspect signup/onboarding code for age verification signals or parental consent branches. Report observations.
- **IN-DPDP-013 (Reasonable Safeguards):** Inspect storage rules, backup scripts, logging configs, and auth code. For `.env*` files, rely on the scanner's key names and line numbers; do not open them unless the user asks; never repeat a value. Report observations.
- **Strict Rule:** Never output `met` or `not-met` for assisted checks. Their scanner result is always `needs-human` when files were scanned, or `unclear` if none were found.

## 6. Step 4: Generate and Present Findings Report

Generate reports using `scripts/report.py`:

```bash
python scripts/report.py --findings <findings_json> [--jurisdiction india] [--today <YYYY-MM-DD>] [--out <md_path>] [--json <json_path>] [--base-dir <dir>] [--verbose]
```
Example:
```bash
python scripts/report.py --findings reports/findings.json --out reports/report.md
```

- `--findings`: Path to input findings JSON (required).
- `--out`: Markdown output file path; prints to stdout if omitted.
- `--json`: Optional JSON report output file path.
- `--verbose`: Prints full caveats in markdown report.

### Report Sections (Status is computed by report.py from config dates)
1. **In Force Now:** Active LAW findings with status category `in_force_now` whose result is `met` or `not-met`.
2. **Readiness:** Active LAW findings with status category `readiness` whose result is `met` or `not-met`.
3. **Unresolved:** Active LAW findings with status category `unresolved` whose result is `met` or `not-met`.
4. **Informational Inventory:** IN-BP-004 inventory and non-BEST PRACTICE informational findings, listed for information; no legal status assigned.
5. **Best Practice:** Findings with label `BEST PRACTICE` (met, not-met, or informational).
6. **Needs Human / Legal Judgment:** Findings with result `needs-human` or `unclear` across all checks.
7. **Not Run:** Active checks that had no findings supplied in the evaluation.
8. **Proposed Checks (Not Active):** Checks drafted as proposed and not active in the v0.1 evaluation.
9. **Not Verified:** Active LAW checks whose `verified_against` is not `official-text`.
10. **Human Check Pending:** Active LAW checks read by an AI model (`verified_by: ai-read`) with human spot-checks pending.
11. **Not Covered by This Scan:** Excluded regimes (other jurisdictions, sector rules, e-commerce, intermediary) and unrun check IDs.
12. **Limits of the Legal Research:** Legal research methodology limits, date variance notes, and pointer to full pack limits.

## 7. Rules
- **Classification:** Every finding must be labeled `LAW` or `BEST PRACTICE`.
- **Status & Metadata:** Display check status, `verified_by`, and `last_verified` date from the pack.
- **No Overall Score:** Never produce a composite score, grade, percentage, or pass/fail summary total.
- **Prohibited Words:** Never state that an app is "compliant" or "secure" (or "insecure", "broken").
- **No False All-Clear:** Never say "no issues"; state "no advisory findings among the patterns checked".
- **Secret Protection:** Never print raw secret values; report key names and placeholders only.
- **Absence Standard:** State that absence means "not found among crawled pages" or "not found among scanned files".
- **Present Limits:** Present Limits and Not Covered sections in full; do not summarise them away.
- **Legal Referral:** Hand legal questions and exemption interpretations to a qualified lawyer.
- **AI-Read Status:** Clarify that LAW checks were read by an AI model and have human spot-checks pending.

## 8. Limits
- **Web Stacks Only:** Code checks (age signal, baseline) cover web stacks only.
- **Keyword Presence != Adequacy:** Scanners verify keyword presence on short lines; wording adequacy is never judged.
- **Unauthenticated Scope:** Crawlers cannot access pages behind authentication or login walls.
- **Implied Consent Undetected:** Text asserting implied consent on continued use is not detected; only explicit interactive form controls are evaluated.
