# Privacy Preflight

Scans a web app's code and running pages for privacy-readiness issues and writes a findings report with LAW or BEST PRACTICE labels. It reports findings only, is not legal advice, and never claims an app is compliant or secure.

## The Problem

Privacy laws impose specific technical and notice obligations on software applications, such as explicit consent controls, accessible grievance channels, and baseline configuration standards. Development teams often discover gaps only late in the release cycle or during external reviews. Privacy Preflight provides preflight feedback during development by checking for the presence of consent controls, notice and grievance pages, and baseline configuration issues.

## How Honest It Is

The tool distinguishes between statutory legal obligations (LAW) and engineering recommendations (BEST PRACTICE). Legal in-force status is not hardcoded; it is computed dynamically by evaluating today's date against transition timelines in `config/effective-dates.yaml`. Every check records its `last_verified` date and `verified_by` method in its badge.

A result of `not-met` means only that the expected element was not found among the crawled pages or scanned code files. A result of `needs-human` means the tool cannot assess the requirement programmatically and requires human review.

The tool provides no overall score or percentage grade.

The tool never certifies an application.

## AI-Read, Not Lawyer-Reviewed

An AI model read the attached official PDFs ("Verified by an AI model reading attached official PDFs", `research/india/verification-log.md:3`). An independent non-lawyer read all five specific passages in full and reported that all match (`r.10(1)`, `r.8(3)`, `S.O. 5458(E)` (all three pages), `CERT-In FAQ Q35/Q36`, `e-Gazette 14 Nov metadata`). Whether pack wording was compared to the PDFs is not confirmed.

Not yet reviewed by legal counsel.

## Prerequisites

- **Python Runtime:** Developed and tested on Python 3.14.0; other versions not tested.
- **Third-Party Packages:** Imported by `scripts/`:
  - `yaml` (`PyYAML`): Used by `scripts/report.py` and `scripts/validate_checks.py` for parsing check definitions and jurisdiction configs.
  - `playwright` (`playwright.sync_api`): Used by `scripts/preflight.py` and `scripts/crawl.py` for dynamic page crawling (requires `playwright install chromium`).
- **Dependency Files:** No `requirements.txt` or `pyproject.toml` file exists in the repository. Dependencies can be installed directly with `pip install pyyaml playwright && playwright install chromium`.

## Usage

Scan only your own site, start it yourself, and use the port it is actually serving on.

### 1. Code Baseline Scan (Static Analysis Only)

Scans the local source tree without requiring a running web server:

```bash
python scripts/preflight.py demo/flawed-app --out reports/findings.json
python scripts/report.py --findings reports/findings.json --out reports/report.md
```

To render the markdown report directly to stdout for a code-only scan:

```bash
python scripts/preflight.py demo/flawed-app --report
```

### 2. Full Scan (Static Code Analysis + Dynamic Crawl)

To run a full scan including dynamic page crawling, first start the target site locally in a separate terminal:

```bash
# In terminal 1: start the local application
python -m http.server 8080 --directory demo/flawed-app
```

If port 8080 is busy, use any free port and change both commands.

Then run preflight targeting that local port in a second terminal:

```bash
# In terminal 2: run preflight with dynamic crawl
python scripts/preflight.py demo/flawed-app --url http://localhost:8080 --report
```

Or write findings to JSON and generate the markdown report as separate steps:

```bash
python scripts/preflight.py demo/flawed-app --url http://localhost:8080 --out reports/findings.json
python scripts/report.py --findings reports/findings.json --out reports/report.md
```

### 3. Check Validation

Validates the consistency and schema of all check definitions in the jurisdiction packs:

```bash
python scripts/validate_checks.py
```

## Active Checks (India Pack)

The scanner evaluates 12 active checks against the India jurisdiction pack (`references/jurisdictions/india.md`): 8 LAW checks and 4 BEST PRACTICE checks, plus 1 inactive proposed check:

- **IN-SPDI-001:** Privacy policy publication and named Grievance Officer · LAW
- **IN-DPDP-002:** Notice links and routes for withdrawal, rights, and complaints · LAW
- **IN-DPDP-004:** Consent controls (unbundled purposes and no pre-ticked controls) · LAW
- **IN-DPDP-008:** Contact details for data inquiries in notice and consent requests · LAW
- **IN-DPDP-009:** Mechanism for exercising data principal rights · LAW
- **IN-DPDP-010:** Grievance redressal mechanism and response timelines · LAW
- **IN-DPDP-011:** Verifiable parental consent and age verification signal · LAW (needs human review)
- **IN-DPDP-013:** Reasonable security safeguards and access logging · LAW (needs human review)
- **IN-BP-001:** Self-host static assets (fonts, scripts, and CDNs) · BEST PRACTICE
- **IN-BP-002:** Contact details accessible within two clicks · BEST PRACTICE
- **IN-BP-003:** Technical security baseline configurations · BEST PRACTICE
- **IN-BP-004:** Third-party recipient and cross-border transfer inventory · BEST PRACTICE (inventory only)
- **IN-CERTIN-001:** ICT clock synchronization and rolling 180-day log retention · LAW (proposed, inactive; not counted in the 12)

## Sample Reports

The following sample excerpts are drawn from crawl runs against locally served demo applications (`demo/flawed-app` and `demo/clean-app`). These excerpts show a subset of the 12 checks evaluated.

> **Normalisation Note:** Sample outputs are normalised for documentation clarity:
> 1. Ephemeral server port removed from evidence URLs (e.g. `http://localhost/signup.html`).
> 2. Verbose check notes (such as IN-BP-003 Notes) are shortened with `...`.
> 3. The Grievance Officer name (`Alex Sharma`) and email (`grievance-officer@example.com`) are fictional demo fixture data from `demo/clean-app/privacy.html`.

### Flawed App Excerpt (`demo/flawed-app`)

```markdown
### [LAW · IN FORCE NOW until 2027-05-13, then UNRESOLVED (Q8, Q23) · verified 2026-10-29 · official-text, ai-read, human check pending]

- **Check:** IN-SPDI-001: Privacy policy publication and named Grievance Officer
- **Result:** not-met
- **Evidence:**
  - `not found among the crawled pages`
- **Suggested Fix:** Publish a privacy policy covering the five Rule 4 elements and designate a named Grievance Officer with working contact information.
- **Notes:** Privacy policy not found among the crawled pages. Pages are classified by URL, title and link text; page content was not searched for pages that were not classified this way. (pages crawled: 7)
- **Confidence:** medium
- **Open Questions:** Q8, Q23
- **Caveats:** Binds any 'body corporate' handling personal information or sensitive personal data or information (SPDI). Full caveats: references/jurisdictions/india.md (IN-SPDI-001)

### [LAW · READINESS from 2027-05-13 · verified 2026-10-29 · official-text, ai-read, human check pending]

- **Check:** IN-DPDP-004: Consent controls (unbundled purposes and no pre-ticked controls)
- **Result:** not-met
- **Evidence:**
  - `http://localhost/signup.html: [pre-checked: True, bundled: True] label: "I agree to receive promotional marketing emails and allow analytics tracking of my browsing behavior across sessions."`
- **Suggested Fix:** Uncheck default consent checkboxes and provide separate toggles per distinct purpose.
- **Notes:** Detected pre-checked or bundled consent controls. (pages crawled: 7, max depth reached: 4, pages skipped: 0, pages failed: 0, interactions: none (no clicks except same-origin links, no forms submitted, no login))
- **Confidence:** medium
- **Open Questions:** None
- **Caveats:** Objective automated detection covers only pre-ticked controls and single controls bundling multiple distinct purposes. Full caveats: references/jurisdictions/india.md (IN-DPDP-004)

### [BEST PRACTICE · not a legal requirement · verified 2026-10-29]

- **Check:** IN-BP-003: Technical security baseline configurations
- **Result:** informational
- **Evidence:**
  - `auth.js: advisory: weak password hashing algorithm 'md5' detected (lines 1, 6, 7, 11)`
  - `nginx.conf: advisory: no Strict-Transport-Security header found`
  - `storage.rules:8: advisory: public write access permitted in storage rules (allow read, write: if true;)`
  - `logging.json:5: informational: log retention configured for 7 days`
- **Suggested Fix:** Upgrade password hashing to Argon2id or bcrypt with appropriate work factor; Configure Strict-Transport-Security header (e.g. 'max-age=31536000; includeSubDomains; preload') in web server configuration; Restrict storage rules to authenticated users or require explicit authorization conditions instead of 'if true'
- **Notes:** Technical baseline configuration scan. files scanned (5), files skipped (7). Technical thresholds (such as TLS 1.3/HSTS, AES-256 for data at rest, Argon2id/bcrypt for password hashing, and encrypted backups) are engineering best practices, not statutory standards prescribed by the Act or Rules. ... This is not an assessment of the application's security.
- **Confidence:** medium
- **Open Questions:** None
- **Caveats:** Specific technical thresholds (such as TLS 1.3/HSTS, AES-256 for data at rest, Argon2id/bcrypt for password hashing, and encrypted backups) are engineering best practices, not statutory standards prescribed by the Act or Rules. Full caveats: references/jurisdictions/india.md (IN-BP-003)
```

### Clean App Excerpt (`demo/clean-app`)

```markdown
### [LAW · IN FORCE NOW until 2027-05-13, then UNRESOLVED (Q8, Q23) · verified 2026-10-29 · official-text, ai-read, human check pending]

- **Check:** IN-SPDI-001: Privacy policy publication and named Grievance Officer
- **Result:** met
- **Evidence:**
  - `/privacy.html: covers practices, data types, purpose, disclosure, and security`
  - `/privacy.html: designated Grievance Officer 'Alex Sharma' with contact 'grievance-officer@example.com'`
- **Notes:** Privacy policy published covering all five Rule 4 elements with a designated named Grievance Officer and contact details. Elements checked by keyword presence signals; not a judgment of adequacy. (pages crawled: 8)
- **Confidence:** high
- **Open Questions:** Q8, Q23
- **Caveats:** Binds any 'body corporate' handling personal information or sensitive personal data or information (SPDI). Full caveats: references/jurisdictions/india.md (IN-SPDI-001)

### [BEST PRACTICE · not a legal requirement · verified 2026-10-29]

- **Check:** IN-BP-001: Self-host static assets (fonts, scripts, and CDNs)
- **Result:** met
- **Evidence:**
  - `All static assets are self-hosted; zero external static asset requests detected.`
- **Notes:** Self-hosted static assets baseline satisfied. (pages crawled: 8, max depth reached: 1, pages skipped: 0, pages failed: 0, interactions: none (no clicks except same-origin links, no forms submitted, no login))
- **Confidence:** low
- **Open Questions:** Q2
- **Caveats:** Self-hosting static assets (such as web fonts, common JavaScript libraries, CDNs) to avoid transmitting visitor IP addresses to third parties prior to consent is an engineering best practice, never a statutory violation. Full caveats: references/jurisdictions/india.md (IN-BP-001)
```

Q-numbers refer to research/india/open-questions.md.

## Known Limits

- **Web Stacks Only:** Code checks cover web stacks only; Dart/Flutter, Kotlin and Swift are not recognised.
- **Committed secrets:** Only string-literal assignments in recognised auth code, web config, container config and .env* files are flagged, and only the key name is shown. Matches in test or spec files are counted in the notes, not listed. Values that look like function calls, SQL, a leading $ or template interpolation are not flagged, so some real secrets can be missed and some non-secrets can still be flagged.
- **Presence != Adequacy:** Keyword and presence detection identifies whether statutory elements, policy pages, or controls exist; it does not evaluate the substantive legal adequacy of notice wording or policy terms.
- **Unauthenticated Crawl Scope:** The crawler inspects publicly reachable links only. It executes no logins, submits no forms, and clicks only same-origin navigation links.
- **Implied Consent Undetected:** Implied or narrative consent notices embedded solely in descriptive text are not detected (known limitation from testing).
- **Authorized Testing Only:** Scan only applications and websites you own or have explicit authorization to test.
- **Date Variance Note:** Gazette datelines say 13 November; e-Gazette metadata and the PIB backgrounder say 14 November (open question Q1).

## Repository Layout

- `LICENSE`: MIT License file.
- `SKILL.md`: skill instructions.
- `config/`: Jurisdiction configuration metadata:
  - `config/effective-dates.yaml`: Effective dates and milestone timeline (DPDP stages 1–3, SPDI in-force and s.43A omission, CERT-In in-force, and 13 vs 14 November variance note).
  - `config/restricted-countries.yaml`: Restricted countries list under DPDP Act s.16 (empty placeholder list).
- `demo/`: Synthetic demonstration applications (`demo/flawed-app/` and `demo/clean-app/`).
- `references/`: Legal rules, provisions, and check specifications (`references/jurisdictions/india.md`).
- `reports/`: local output, not committed (gitignored).
- `research/`: Primary legal texts, analysis, open questions, and verification logs (`research/india/`).
- `scripts/`: Python scanner modules, crawler, orchestrator, and report generator.
- `tests/`: Automated test suite and expected findings fixtures (`tests/expected-findings.json`).

## Licence

MIT (see LICENSE)

