# India Jurisdiction Pack (v0.1)

> **Research and engineering checks. Not legal advice.**
> Passing these checks does not certify that an application or entity is "compliant" with the Digital Personal Data Protection Act, 2023, the Information Technology Act, 2000, or any other law.

---

## Active Checks (v0.1)

Status (`IN FORCE NOW` vs `READINESS`) is computed dynamically from `applies_from` relative to today's date. Each entry contains a single self-contained YAML block. Mixed checks have been split into separate `LAW` and `BEST PRACTICE` entries.

---

### IN-BP-004: Third-party recipient and cross-border transfer inventory

```yaml
id: IN-BP-004
title: Third-party recipient and cross-border transfer inventory
research_ref: "IN-DPDP-017/018"
label: BEST PRACTICE
provision: "none (engineering practice)"
applies_from: none
last_verified: 2026-10-29
verified_against: n/a
verified_by: ai-read
confidence: low
caveats: "Informational only, no pass/fail; every row outputs 'legal status unclear' (Q2). The DPDP Act and Rules are silent on third-party network requests (analytics, fonts, CDNs, embeds, cookies). Sections 2(t), 2(x), 11(1)(b), and 16 provide context only: whether visitor IP is personal data and whether third-party asset calls constitute sharing or disclosure is legally unresolved (Q2). Section 11(1)(b) applies only against a fiduciary to which consent was given (or s.7(a)); s.11(2) carves out sharing authorized by law. Transfer restriction under s.16: restricted list currently empty (secondary finding). Rules r.13(4) and r.15 cited for context only (r.13(5) only defines 'committee'). Self-hosting static assets is covered separately under IN-BP-001."
open_question_refs:
  - Q2
detection_type: automated
detection: "Automated crawl of key application pages and network requests; extract outbound domains and resolve destination countries via DNS/IP geolocation; compare against config/restricted-countries.yaml."
pass_criteria: "Informational inventory output only. No pass/fail assigned. Every third-party call reports 'legal status unclear' (open-questions.md Q2)."
```

---

### IN-BP-001: Self-host static assets (fonts, scripts, and CDNs)

```yaml
id: IN-BP-001
title: Self-host static assets (fonts, scripts, and CDNs)
label: BEST PRACTICE
provision: "none (engineering practice)"
applies_from: none
last_verified: 2026-10-29
verified_against: n/a
verified_by: ai-read
confidence: low
caveats: "Self-hosting static assets (such as web fonts, common JavaScript libraries, CDNs) to avoid transmitting visitor IP addresses to third parties prior to consent is an engineering best practice, never a statutory violation. The law does not mandate self-hosting."
open_question_refs:
  - Q2
detection_type: automated
detection: "Scan HTML templates, bundle manifests, and outbound network traffic for third-party hosted static assets (e.g. Google Fonts, CDNjs, unpkg, external font/CSS delivery endpoints)."
pass_criteria: "Flag external static asset domains as recommendations to self-host. Informational only; never output a failure or violation."
```

---

### IN-DPDP-004: Consent controls (unbundled purposes and no pre-ticked controls)

```yaml
id: IN-DPDP-004
title: Consent controls (unbundled purposes and no pre-ticked controls)
label: LAW
provision: "Act s.6(1), 6(2)"
applies_from: dpdp.stage_3
last_verified: 2026-10-29
verified_against: official-text
verified_by: ai-read
confidence: medium
caveats: "Objective automated detection covers only pre-ticked controls and single controls bundling multiple distinct purposes. Evaluation of whether consent is 'unconditional', 'free', or 'informed' requires legal and contextual judgment. The Act contains no cookie-specific rule."
open_question_refs: []
detection_type: automated
detection: "Automated scan of HTML/JS, DOM trees, and mobile UI layouts for consent checkboxes/toggles that default to checked/on, consent inferred from scrolling or continued use, or a single control covering multiple distinct processing purposes."
pass_criteria: "No consent control is pre-selected (pre-ticked); each distinct purpose has its own independent control."
```

---

### IN-DPDP-002: Notice links and routes for withdrawal, rights, and complaints

```yaml
id: IN-DPDP-002
title: Notice links and routes for withdrawal, rights, and complaints
label: LAW
provision: "Act s.5(1); Rules r.3(c)"
applies_from: dpdp.stage_3
last_verified: 2026-10-29
verified_against: official-text
verified_by: ai-read
confidence: high
caveats: "Not required for s.7 'certain legitimate uses' where consent is not the legal basis. Startup exemption power under s.17(3) not notified (secondary finding). Note that Act s.5(1)(ii) names s.6(4) and s.13; r.3(c)(ii) widens to 'rights under the Act'; r.3(c) requires a link plus 'other means, if any'."
open_question_refs: []
detection_type: automated
detection: "Automated search on notice pages for a working communication link to the website/app, plus described routes for consent withdrawal, rights exercise, and Board complaints."
pass_criteria: "Notice contains an accessible communication link to the website/app and explicitly describes the routes for withdrawal, rights exercise, and Board complaints."
```

---

### IN-DPDP-008: Contact details for data inquiries in notice and consent requests

```yaml
id: IN-DPDP-008
title: Contact details for data inquiries in notice and consent requests
label: LAW
provision: "Act s.6(3), 8(9); Rules r.9"
applies_from: dpdp.stage_3
last_verified: 2026-10-29
verified_against: official-text
verified_by: ai-read
confidence: high
caveats: "LAW (Act s.6(3), r.9): consent requests must contain or link to the business contact details of the DPO or authorized contact person. Contact details must also be prominently published on the website or app (Act s.8(9), r.9). Mandatory DPO applies only to notified Significant Data Fiduciaries (s.10(2)(a); from original research; not re-verified in the verification report); other fiduciaries require an authorized contact person. Note: reaching contact details within two clicks is a separate engineering best practice (see IN-BP-002), not in r.9 which uses 'prominently'."
open_question_refs: []
detection_type: automated
detection: "Automated crawl of footer, privacy notice, and consent request screens for a named role or contact channel (email, phone, webform)."
pass_criteria: "Consent requests contain or link directly to contact details; business contact information is published on the website or app."
```

---

### IN-BP-002: Contact details accessible within two clicks

```yaml
id: IN-BP-002
title: Contact details accessible within two clicks
label: BEST PRACTICE
provision: "none (engineering practice)"
applies_from: none
last_verified: 2026-10-29
verified_against: n/a
verified_by: ai-read
confidence: medium
caveats: "Reaching contact details from the home page or app settings within at most two clicks is an engineering best-practice threshold. Rule 9 uses the qualitative standard 'prominently', not a two-click count."
open_question_refs: []
detection_type: automated
detection: "Crawl page link graph from the home page or mobile root settings; measure click-distance to views displaying privacy contact information."
pass_criteria: "Contact information reachable in at most two clicks or taps from landing screens. Output advisory notice if distance exceeds two clicks."
```

---

### IN-DPDP-009: Mechanism for exercising data principal rights

```yaml
id: IN-DPDP-009
title: Mechanism for exercising data principal rights
label: LAW
provision: "Act ss.11, 12, 14; Rules r.14(1), 14(4)"
applies_from: dpdp.stage_3
last_verified: 2026-10-29
verified_against: official-text
verified_by: ai-read
confidence: medium
caveats: "Note that s.11 (access) and s.12 (correction and erasure) apply only where processing is based on consent or s.7(a) voluntary provision. Access under s.11(1)(b) includes third-party recipient inventory. s.17(3) exemption power covers s.11 but not s.12 (none notified; secondary finding). Automated checks verify presence of published routes and stated authentication requirements; fulfillment adequacy requires operational review."
open_question_refs: []
detection_type: automated
detection: "Automated crawl for published rights endpoints, forms, or in-app controls; verify mention of access, correction, erasure, and nomination routes, and required authentication particulars."
pass_criteria: "A published mechanism exists covering each statutory right, specifying the authentication particulars required."
```

---

### IN-DPDP-010: Grievance redressal mechanism and response timelines

```yaml
id: IN-DPDP-010
title: Grievance redressal mechanism and response timelines
label: LAW
provision: "Act s.8(10), 13; Rules r.14(3)"
applies_from: dpdp.stage_3
last_verified: 2026-10-29
verified_against: official-text
verified_by: ai-read
confidence: medium
caveats: "Dual regime clocks: SPDI r.5(9) requires grievance redressal 'within one month' (in force now); DPDP Rules r.14(3) sets a response period 'within a reasonable period not exceeding ninety days' (grievance redressal system only, not rights under ss.11-12, resolving Q7). While both regimes apply, developers are advised to observe the stricter one-month clock. Act s.13 requires exhaustion of grievance mechanism before approaching the Board."
open_question_refs:
  - Q7
detection_type: automated
detection: "Automated crawl for a published grievance channel and stated response timeline."
pass_criteria: "A published grievance route exists. Tool displays both applicable response clocks (SPDI: 1 month; DPDP: up to 90 days under r.14(3) for grievances only) and recommends following the stricter one-month standard while both regimes apply."
```

---

### IN-DPDP-011: Verifiable parental consent and age verification signal

```yaml
id: IN-DPDP-011
title: Verifiable parental consent and age verification signal
label: LAW
provision: "Act s.2(f), 9(1); Rules r.10, 11, 12; Fourth Schedule"
applies_from: dpdp.stage_3
last_verified: 2026-10-29
verified_against: official-text
verified_by: ai-read
confidence: medium
caveats: "Presence or absence check only; never judge the legal sufficiency of verification methods. Keep the r.10(1) qualifier: parent must be an adult who is 'identifiable if required in connection with compliance with any law for the time being in force in India' (second cross-check, verification-report section 11). r.11 guardian verification requires appointment by a court, designated authority, or local level committee. Fourth Schedule Part A exempts specific classes (healthcare, limited tracking in educational institutions, child transport for location, crèche/day-care) and purposes from s.9(1) and s.9(3). S.O. 5458(E) inserts 'of' in English s.9(1); possible Hindi discrepancy is unverified (Q21; extracted Hindi text unreliable). No age-band exemption under s.9(5) notified (secondary finding)."
open_question_refs:
  - Q4
  - Q21
detection_type: assisted
detection: "Inspect onboarding, signup, or checkout code for date-of-birth fields, age gates, or child-directed signals. Human reviewer confirms whether the application is child-directed or accessible to children."
pass_criteria: "Where users may be under 18: an age signal exists prior to personal data collection, triggering a parental consent verification branch before account creation or storage. The tool never judges the legal sufficiency of verification mechanisms."
```

---

### IN-DPDP-013: Reasonable security safeguards and access logging

```yaml
id: IN-DPDP-013
title: Reasonable security safeguards and access logging
label: LAW
provision: "Act s.8(5); Rules r.6(1)(a)-(g), r.8(3)"
applies_from: dpdp.stage_3
last_verified: 2026-10-29
verified_against: official-text
verified_by: ai-read
confidence: medium
caveats: "Rule 6 gives no numeric standard besides the one-year log retention: encryption, obfuscation, masking or virtual tokens; access control; logs and monitoring of access to personal data; continuity measures such as backups; retention of such logs and personal data for one year (unless another law requires otherwise); security terms in processor contracts; and appropriate technical and organisational measures. Treat TLS version, algorithms and hashing parameters as engineering defaults, not legal minimums (see IN-BP-003). Log retention: no pass/fail; report the configured retention setting found. r.6(1)(e) exception: retention of logs and data for one year 'unless compliance with any law for the time being in force requires otherwise'. r.8(3) requires 'a Data Fiduciary' to retain data, traffic data, and logs for at least one year for Seventh Schedule purposes (class limit is in r.8(1), not r.8(3); tension between one-year retention and erasure is unresolved, Q6). s.8(5) applies even where other chapters are disapplied under s.17(1) (from original research, checks.md; not re-verified in the verification report)."
open_question_refs:
  - Q6
detection_type: assisted
detection: "Scan code and cloud config for HTTPS-only enforcement, database/volume encryption, secrets committed to repositories, authentication on administrative routes, access logging flags, log retention settings, and backup policies."
pass_criteria: "Evidence of controls across Rule 6(1) categories. Log retention: no pass/fail; report the detected log retention setting and flag the r.6(1)(e) exception and r.8(3) scope."
```

---

### IN-BP-003: Technical security baseline configurations

```yaml
id: IN-BP-003
title: Technical security baseline configurations
label: BEST PRACTICE
provision: "none (engineering practice)"
applies_from: none
last_verified: 2026-10-29
verified_against: n/a
verified_by: ai-read
confidence: medium
caveats: "Specific technical thresholds (such as TLS 1.3/HSTS, AES-256 for data at rest, Argon2id/bcrypt for password hashing, and encrypted backups) are engineering best practices, not statutory standards prescribed by the Act or Rules."
open_question_refs: []
detection_type: automated
detection: "Static analysis of server configuration, TLS cipher suites, password hashing algorithms, and backup encryption configurations."
pass_criteria: "Evaluate configurations against modern engineering security baselines. Report non-binding advisory findings for deprecated ciphers or insecure storage parameters."
```

---

### IN-SPDI-001: Privacy policy publication and named Grievance Officer

```yaml
id: IN-SPDI-001
title: Privacy policy publication and named Grievance Officer
label: LAW
provision: "SPDI Rules r.4, r.5(9)"
applies_from: spdi.in_force
applies_until: spdi.s43a_omitted
last_verified: 2026-10-29
verified_against: official-text
verified_by: ai-read
confidence: high
caveats: "Binds any 'body corporate' handling personal information or sensitive personal data or information (SPDI). Privacy policy must cover the five elements specified in r.4. Grievance Officer name and contact details must be published on the website, with grievances redressed within one month. Section 43A of the IT Act is omitted on the date set by spdi.s43a_omitted in config/effective-dates.yaml (s.44(2)); whether the SPDI Rules survive the omission of s.43A is legally unresolved (open-questions.md Q8, Q23)."
open_question_refs:
  - Q8
  - Q23
detection_type: automated
detection: "Automated crawl for privacy policy link, verification of five r.4 policy sections, and presence of named Grievance Officer and contact details."
pass_criteria: "A published privacy policy containing the five required elements and a named Grievance Officer with working contact information."
```

---

## Proposed Checks (Not Active in v0.1)

The following proposed check is drafted for future inclusion upon approval. It is **NOT** part of the active v0.1 pack.

---

### IN-CERTIN-001 (PROPOSED): ICT clock synchronization and rolling 180-day log retention

```yaml
id: IN-CERTIN-001
title: ICT clock synchronization and rolling 180-day log retention
label: LAW
provision: "CERT-In Directions No. 20(3)/2022-CERT-In, Directions (i), (iv)"
applies_from: certin.in_force
last_verified: 2026-10-29
verified_against: official-text
verified_by: ai-read
confidence: medium
status: proposed
caveats: "Status: PROPOSED, NOT ACTIVE in v0.1 pack. Synchronize ICT clocks to NIC/NPL or traceable NTP servers. Enable and maintain logs of all ICT systems for a rolling 180-day period. Log storage location is reported as INFORMATION ONLY, NEVER pass/fail: Direction (iv) requires logs maintained 'within the Indian jurisdiction'; non-binding FAQ Q35 permits storage abroad if produced to CERT-In in reasonable time, while FAQ Q36 mentions Indian jurisdiction for financial-transaction logs (answers stay distinct; unresolved legal conflict, Q18)."
open_question_refs:
  - Q18
detection_type: assisted
detection: "Inspect server/IaC configuration for NTP time sources, logging retention settings across ICT systems, and storage region."
pass_criteria: "Report configured log retention days (180 rolling) and NTP source. Report log storage location as information only, never pass/fail."
```

---

## Known Limits

1. **Schedules-Commencement Mapping:** The mapping of DPDP Schedules (e.g. Second through Seventh Schedules) to commencement stages is **inferred from cross-references** to the Rules (e.g. r.18, r.21(2)), not explicitly verified in commencement text (r.1 names no Schedule).
2. **Absence of Notifications:** Every statement asserting that a notification has not been issued (e.g. s.16 restricted countries, s.17(3) startup exemptions, Significant Data Fiduciary designations, s.9(5) age exemptions, Board appointments) is a **secondary-source finding**, not verified against direct e-Gazette searches.
3. **Unread Primary Sources:**
   - **Consumer Protection (E-Commerce) Rules, 2020 (P11):** Official text not opened (text seen on mirrors only); pre-ticked purchase consent prohibitions (r.4(9)) and e-commerce grievance officer duties are unverified against primary gazette.
   - **Information Technology Act, 2000 text:** Sections 43A, 70B, and 87 not opened.
   - **Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021:** Official gazette text not opened.
   - **Reserve Bank of India (RBI) circular of 6 April 2018 (DPSS.CO.OD.No.2785/06.08.005/2017-18):** Only FAQ extracts seen; primary circular text not opened.
4. **Hindi Text Layers:** Hindi versions of the Rules (file 01), the Act (file 02), and the Removal of Difficulties Order (file 06) were not compared against the English text; extracted Hindi text was unreliable (Q21 unverified by a Hindi reader).
5. **India Code Commencement Footnote:** The India Code copy of the Act containing the commencement footnote was not attached in official PDF file 02 (which is the original 11 August 2023 Gazette of India issue).
6. **Human Spot-Checks Pending:** Primary texts were read by an AI model. See research/india/verification-log.md for which items have a human read.
7. **Legal Publication Date (Q1):** Official e-Gazette digital signatures and upload IDs for the Rules and commencement notification are dated 14 November 2025; issue headers and datelines state 13 November 2025. That the 14th represents upload lag is an inference; the legal publication date remains an open question for legal counsel (open-questions.md Q1).
8. **Jurisdictional and Sectoral Scope:** Other jurisdictions (e.g. Nigeria NDPA 2023, GAID 2025) and specialized Indian sector regimes (health data, telecom, SEBI, insurance) are not covered in this pack.

