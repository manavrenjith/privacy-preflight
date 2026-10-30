# Demo App Test Fixtures

> **CRITICAL WARNING: TEST FIXTURES ONLY — NOT COMPLIANT SOFTWARE — NOT LEGAL ADVICE**
>
> These applications (`demo/flawed-app/` and `demo/clean-app/`) are synthetic test fixtures designed solely to exercise and validate Privacy Preflight static analysis rules and check coverage against the India Jurisdiction Pack (`references/jurisdictions/india.md`).
>
> Neither application constitutes a production-ready system or certified compliant implementation. Passing these checks or replicating patterns in `clean-app` does **NOT** certify that an application or entity complies with the Digital Personal Data Protection Act, 2023 (DPDP Act), the Information Technology Act, 2000, the SPDI Rules, 2011, or any other legal framework. Legal compliance depends on factual data processing operations, verified contracts, organizational governance, and counsel review.

---

## 1. Overview of Fixtures

Both applications are completely **dependency-free**:
- Static HTML5, modern CSS, and vanilla JS.
- No `npm`, no `node_modules`, no external build pipelines, and no backend frameworks.
- Plain configuration and code stubs (`nginx.conf`, `storage.rules`, `auth.js`, `logging.json`).
- Synthetic hostnames restricted strictly to `example.com`, `example.test`, and `*.test`.
- No real personal data, phone numbers, email addresses, or credentials. Any planted fake secret is explicitly marked `FIXTURE` (e.g. `FAKE_KEY_DO_NOT_USE_0000`).

### Fixture Directories

1. **`demo/flawed-app/`**:
   Contains intentional, planted anti-patterns mapped 1:1 to every active check in `references/jurisdictions/india.md`.
2. **`demo/clean-app/`**:
   A counterpart application providing clean engineering baseline implementations that resolve each planted flaw from `flawed-app/`.

---

## 2. Check and Flaw Matrix

| Check ID | Provision / Label | Planted Flaw (`flawed-app/`) | Baseline Fix (`clean-app/`) |
|---|---|---|---|
| **IN-BP-004** | Engineering Best Practice | Remote Google Fonts link & external tracker `cdn.analytics.example.test` in `index.html`. | Zero external third-party network or cross-border transfer calls. |
| **IN-BP-001** | Engineering Best Practice | Remote static assets from Google Fonts and CDN script in `index.html`. | Self-hosted `@font-face` font file reference in `css/style.css` and no external scripts. |
| **IN-DPDP-004** | Act s.6(1), 6(2) | Single pre-ticked checkbox in `signup.html` bundling marketing and analytics consent. | Independent, unbundled, unchecked checkboxes for marketing and analytics in `signup.html`. |
| **IN-DPDP-002** | Act s.5(1); Rules r.3(c) | `signup.html` contains no link to any notice. | Notice linked directly from `signup.html`; `notice.html` details withdrawal, rights, and complaints routes with a working communication link. |
| **IN-DPDP-008** | Act s.6(3), 8(9); Rules r.9 | Neither footer nor consent screen contains contact details. | Data Protection Officer role title and `dpo@example.com` published in footer, consent screens, and `notice.html`. |
| **IN-BP-002** | Engineering Best Practice | `contact.html` is buried behind 4 nested navigation links (`nav/step1.html` &rarr; `step2` &rarr; `step3` &rarr; `contact.html`). | `contact.html` directly linked from header and footer within at most 1 click (&le; 2 clicks threshold). |
| **IN-DPDP-009** | Act ss.11, 12, 14; Rules r.14 | No page or control exists for data principal access, correction, erasure, or nomination. | Dedicated `rights.html` portal providing structured forms and stated identity authentication requirements for all statutory rights. |
| **IN-DPDP-010** | Act s.8(10), 13; Rules r.14(3) | No grievance channel published and no response time stated. | Dedicated `grievance.html` portal specifying a clear internal redressal workflow and an explicit 30-day response timeline. |
| **IN-DPDP-011** | Act s.2(f), 9(1); Rules r.10-12 | `signup.html` omits date-of-birth/age collection and lacks any parental consent branch. | `signup.html` collects date-of-birth and provides a dedicated parental/guardian consent verification branch for minors under 18 (*Needs Human Review*). |
| **IN-DPDP-013** | Act s.8(5); Rules r.6, r.8(3) | Plaintext credentials committed in `.env`; `logging.json` configures 7-day log retention below 1-year standard. | `.env` ignored via `.gitignore` with safe `.env.example`; `logging.json` configures 365-day audit retention. |
| **IN-BP-003** | Engineering Best Practice | `auth.js` uses MD5; `nginx.conf` omits HSTS; `storage.rules` allows public write. | `auth.js` uses Argon2id; `nginx.conf` enforces HSTS; `storage.rules` restricts access to authenticated owners. |
| **IN-SPDI-001** | SPDI Rules r.4, r.5(9) | No privacy policy published; no named Grievance Officer. | Dedicated `privacy.html` covering collection, purpose, disclosure, security, and a named Grievance Officer with `grievance-officer@example.com`. |

---

## 3. How to Serve Locally

You can serve either demo application locally using Python's built-in HTTP server module. No external web server or dependencies are required.

### Serving `flawed-app`

```bash
cd demo/flawed-app
python -m http.server 8000
```
Open [http://localhost:8000](http://localhost:8000) in your web browser.

### Serving `clean-app`

```bash
cd demo/clean-app
python -m http.server 8001
```
Open [http://localhost:8001](http://localhost:8001) in your web browser.

---

## 4. Test Oracles

Expected evaluation findings for both applications across all active check IDs are maintained in `tests/expected-findings.json` and verified by automated test assertions in `tests/test_demo_fixtures.py`.

