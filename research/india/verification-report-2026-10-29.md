> Source: verification report produced by Claude Sonnet on 2026-10-29 from the official PDFs. Corrected 2026-10-29 (v2) after a second cross-check of five findings (section 11).
> Status: AI-read. The five findings in section 11 were confirmed against supplied excerpts (second cross-check). A person's read of the PDF pages is still pending unless `verification-log.md` says otherwise. Not legal advice.

# India privacy research: verification report (v2, corrected)

Date: Thursday, 29 October 2026. Not legal advice. Nothing here says any app is "compliant".
"official-text" = read in an attached official PDF. Web material is "secondary" unless stated.

## Changes in v2

1. **Section 11 added.** Second cross-check of five findings: r.10(1), r.8(3), S.O. 5458(E), CERT-In FAQ Q35/Q36, e-Gazette metadata. All five confirmed on supplied excerpts. Status is "second cross-check", not "human-read", until a person has read the PDF passage.
2. **Section 4:** e-Gazette metadata now has signature times to the second and page references (one page reference needs re-confirming, see section 11).
3. **Sections 2, 8, 9:** r.10(1) qualifier kept for check 011; r.8(3) scope sharpened (the Third Schedule class limit sits in r.8(1), not r.8(3)).
4. **B2:** the Hindi s.9(1) observation is downgraded to unverified (Q21). A full-text scan of the Order is still pending.
5. **Section 9:** the `sources.md` P9 URL edit is **withdrawn** (probable line-break artifact). The `checks.md` S.O. 5458(E) edit no longer states the Hindi wording as verified. Schedules-commencement edits are labelled "inferred".
6. **Section 10:** updated to match.

## 1. Document register

| File | What it is | Readable? | Pages |
|---|---|---|---|
| 01 | DPDP Rules 2025, G.S.R. 846(E), Gazette No. 760, 13 Nov 2025, CG-DL-E-14112025-267650. Hindi pp.1-23, English pp.24-41 | Yes. Hindi text layer garbled; English used only. | 41 |
| 02 | DPDP Act 2023, Gazette No. 25, 11 Aug 2023. Original gazette, not the India Code copy (no commencement footnote) | Yes | 21 |
| 03 | G.S.R. 843(E), Act commencement, Gazette No. 757, dated 13 Nov 2025 | Yes | 2 |
| 04 | G.S.R. 892(E), corrigenda, dated 10 Dec 2025, Gazette No. 806 of 11 Dec 2025 | Yes | 1 |
| 05 | SPDI Rules 2011, G.S.R. 313(E), 11 Apr 2011 | Yes. OCR-style typos in text layer ("boy corporate", "snail") | 5 |
| 06 | Removal of Difficulties Order, S.O. 5458(E), dated 5 Oct 2026, Gazette No. 5248 of 6 Oct 2026 | Yes (Hindi and English) | 3 |
| 07 | CERT-In Directions, No. 20(3)/2022-CERT-In, 28 Apr 2022 | Yes | 8 |
| 07b | CERT-In extension notice, 27 Jun 2022, with MSME notification S.O. 1702(E) annexed | Yes | 4 |
| 07c | CERT-In FAQ on the Directions. Document says only "May 2022"; "18 May" is from the filename (unverified) | Yes | 28 |

Notes:
- Government of India Press digital signatures are present on the gazette PDFs. Not validated cryptographically.
- The India Code copy of the Act (P1) with its footnote is not attached.

## 2. Verification table

| id | provision cited | result | verified against | what differs | proposed fix |
|---|---|---|---|---|---|
| IN-DPDP-017 | Act ss.2(t), 2(x), 4, 5, 6(1), 8(1)-(2), 11(1)(b) | MATCHES | official-text (02) | s.11(1)(b) applies only against a fiduciary the person previously consented to (incl. s.7(a)); s.11(2) carves out sharing with fiduciaries authorised by law | Add caveat |
| IN-DPDP-018 | Act s.16; Rules r.13(4), 13(5), 15 | MATCHES, minor error | official-text (01, 02) | r.13(5) only defines "committee"; r.13(4) also covers traffic data | Cite r.13(4), r.15 only |
| IN-DPDP-004 | Act s.6(1), 6(2) | MATCHES | official-text (02) | none | none |
| IN-DPDP-002 | Act s.5(1); r.3(c) | MATCHES | official-text (01, 02) | s.5(1)(ii) names s.6(4) and s.13 rights; r.3(c)(ii) widens to "rights under the Act"; r.3(c) requires a link plus "other means, if any" | Note wording |
| IN-DPDP-008 | Act s.8(9), 6(3); r.9 | MATCHES | official-text | "two clicks" is not in law; r.9 says "prominently" | Label threshold BEST PRACTICE |
| IN-DPDP-009 | Act ss.11, 12, 14; r.14(1), 14(4) | MATCHES | official-text | s.11/12 apply only where consent was given (or s.7(a)); s.17(3) lists s.5, 8(3), 8(7), 10, 11, not s.12 | Optional note |
| IN-DPDP-010 | Act s.8(10), 13; r.14(3) | MATCHES | official-text | none | none |
| IN-DPDP-011 | Act s.2(f), 9(1); r.10-12; 4th Sch | DIFFERS | official-text; r.10(1) point second-cross-checked (section 11) | (a) r.10(1): parent must be an adult "identifiable if required" in connection with compliance with any Indian law (confirmed in section 11); qualifier dropped in check and Q4. (b) r.11 guardian verification not described. (c) 4th Sch Part A row 4 (crèche/day-care individual) omitted. (d) s.9(1) now amended (see B2) | See section 9 |
| IN-DPDP-013 | Act s.8(5); r.6(1)(a)-(g), 8(3) | MATCHES | official-text | r.6(1)(e) exception "unless compliance with any law requires otherwise" can cut either way | none |
| IN-SPDI-001 | SPDI r.4, 5(9) | MATCHES | official-text (05) | none | "via mirror" -> official gazette PDF |
| IN-SPDI-002 | SPDI r.3, 5(1)-(7), 6, 7, 8 | MATCHES, omissions | official-text (05) | See B1 | See B1 |
| IN-CERTIN-001 | Directions (i), (iv); 07b; FAQ | MATCHES, updates | official-text (07, 07b, 07c); FAQ Q35/Q36 second-cross-checked (section 11) | See B3 | See section 9 |
| IN-CERTIN-002 | Directions (ii), (iii); Annexures I, II | MATCHES, updates | official-text (07) | See B3 | See section 9 |

Additional:
- checks.md internal inconsistency: IN-DPDP-016 says "such fiduciaries must retain" one year. r.8(3) says "a Data Fiduciary" with no class limit (as Q6 already says). Second cross-check (section 11) confirms the class limit appears in r.8(1), not r.8(3). Fix 016.
- All "nothing notified" claims remain secondary-only; official documents cannot confirm absence.

## 3. Corrigendum G.S.R. 892(E): every change (A1)

Eight edits at five places; matches the secondary description.

| # | Where | Rule | Old | New |
|---|---|---|---|---|
| 1 | p.24 l.22 | r.1(3) | "of this Gazette" | "in the Official Gazette" |
| 2 | p.24 l.24 | r.1(4) | "of this Gazette" | "in the Official Gazette" |
| 3 | p.29 l.44 | r.13(5) | "Department" | "Departments" |
| 4 | p.32 l.4 | r.23(1) | "given in such" | "given in such order" |
| 5 | p.34 l.1 | First Sch, Part B item 11(c) | "everybody" | "every body" |
| 6 | p.34 l.26 | First Sch, Note (d) | "(18 or 2013)" | "(18 of 2013)" |
| 7 | p.38 l.2 | Fourth Sch Note | "." | ";" |
| 8 | p.38 l.1-15 | Fourth Sch Note | "(a) to (f)" | "(a) to (g)" |

- Item 8: the literal phrase "(a) to (f)" is not in the text layer. The Note has seven items lettered (a),(a),(b)..(f); this looks like a lettering fix (inferred).
- Effect on the 9 checks: none substantive. Items 1-2 touch commencement wording only; item 3 touches r.13(5) (cited by 018); items 7-8 touch the Fourth Schedule Note (cited by 011). The "pre-corrigendum" caveat can be dropped.
- The MeitY URL fetched on 29 Oct 2026 still serves the uncorrected text.

## 4. Commencement findings (A2)

From G.S.R. 843(E) and Rules r.1 (matches timeline.md exactly):

| Stage | Act | Rules |
|---|---|---|
| On publication | s.1(2), s.2, ss.18-26, 35, 38-43, s.44(1) and (3) | r.1, 2, 17-21 |
| One year | s.6(9), s.27(1)(d) | r.4 |
| Eighteen months | ss.3-5, s.6(1)-(8) and (10), ss.7-17, s.27 except (1)(d), ss.28-34, 36, 37, s.44(2) | r.3, 5-16, 22, 23 |

Deciding phrase: 843(E) uses "date of publication of this gazette"; r.1(3)/(4) said "of this Gazette", now "in the Official Gazette" per corrigendum. No day is named in either.

13 versus 14 November:
- 13 Nov (official text): datelines of 843(E) and 846(E); issue headers ("THURSDAY, NOVEMBER 13, 2025"); corrigendum describes 846(E) as "dated the 13th November, 2025".
- 14 Nov (official metadata, second-cross-checked in section 11):
  - File 01 (Rules): e-Gazette ID CG-DL-E-14112025-267650; digital signature 14 Nov 2025, 10:43:53 IST.
  - File 03 (G.S.R. 843(E)): e-Gazette ID CG-DL-E-14112025-267647; digital signature 14 Nov 2025, 10:37:23 IST.
- Same one-day lag on later gazettes: corrigendum (issue 11 Dec, ID/signature 12 Dec); RoD Order (issue 6 Oct, ID 07102026, signed 7 Oct). This suggests the 14th is an upload date. **That is an inference. No document says so.**
- PIB backgrounder extract (official, secondary): Rules "notified on 14 November 2025".

Recommendation: keep 13 Nov 2026 and 13 May 2027 as conservative defaults, and replace "could not verify that stamp" with the verified metadata. Q1 stays with a lawyer: the metadata shows when the files were signed and uploaded, not which date is the legal date of publication.

Schedules (new finding, **inferred**): r.1 names no Schedule. timeline.md places the Fifth and Sixth Schedules in the later stage, but their headings read "[See rule 18]" and "[See rule 21(2)]", and those rules commence on publication. The mapping is inference from cross-references, not stated in any commencement text.

## 5. A4 and A5

A4 (90 days): No Rule sets a deadline for fulfilling access, correction or erasure requests.
- Only r.14(3) has the cap: a published grievance-system period "within a reasonable period not exceeding ninety days".
- Act s.13(2) delegates only the grievance period; ss.11, 12 have no deadline.
- PIB's broader statement is unsupported by the Rules text (only a snippet of PIB was seen).
- Q7 closed on the text. Residual lawyer question: whether the grievance route is the expected channel for late rights requests.

A5 (definitions), confirmed absent in the Act (02) and English Rules (01):
- "IP address", "cookie", "device identifier": not present.
- "Tracking", "behavioural monitoring", "targeted advertising": undefined. Appear in s.9(3) and Fourth Schedule Parts A/B. Rules do not use "targeted advertising".
- "Advertisement": defined only by reference to the Consumer Protection Act, 2019.
- "Identifier": r.14(5), limited to an ID issued by the fiduciary for rights requests.
- "Traffic data": used in r.8(3), r.13(4); undefined.
- Hindi text not searched.

## 6. Part B findings

### B1. SPDI Rules (05)
All claims for IN-SPDI-001/002 match.
- r.3: enumerated list incl. items (vii), (viii) (related details); overlaps.md "closed list" is slightly too strong. Public-domain/RTI proviso.
- r.4: policy elements (i)-(v) match.
- r.5(9): Grievance Officer name/contact on website; redress "within one month". Matches.
- r.6, r.7, r.8 match as described.
- Omissions to add: r.6(1) proviso (Government agencies); r.6(3)-(4) (no publication; no onward disclosure); r.8(3) (industry codes).
- r.2(1)(c) borrows "body corporate" from the s.43A explanation.

### B2. Removal of Difficulties Order S.O. 5458(E) (06)
- Two changes to the Act, none to the Rules (second-cross-checked on an excerpt, section 11; **full-text scan of all three pages still pending**).
- s.9(1): inserts "of" in the English text ("child or of a person with disability").
- s.10(2)(c)(ii): "audit" becomes "data audit". r.13(1) still says "audit".
- No commencement date, Rule or other section changed (on the excerpt). In force on publication.
- Matches the secondary description.
- **Hindi wording (unverified, Q21):** the first pass read the Hindi operative text for s.9(1) as substituting "ऐसे" ("such") rather than a "के" ("of") equivalent. That reading came from extracted Devanagari text, which is unreliable (the Rules' Hindi text layer was garbled). Do not treat it as a finding until a Hindi reader checks the PDF.

### B3. CERT-In Directions (07, 07b, 07c)

| Item | Official text |
|---|---|
| 6-hour reporting | Direction (ii): report Annexure I incidents "within 6 hours" of noticing or being told. Email/phone/fax channels printed. Verified |
| Incident list | Annexure I: 20 categories (i)-(xx), incl. unauthorised access, data breach, data leak, application attacks, AI/ML systems |
| Logs | Direction (iv): logs of all ICT systems, rolling 180 days, maintained "within the Indian jurisdiction"; provide to CERT-In with incident reports or on order |
| NTP | Direction (i): sync to NIC/NPL or traceable servers; multi-geography entities may use another accurate source that does not deviate |
| Point of contact | Direction (iii): designate one; email details in Annexure II format (filing step omitted in research) |
| Effective date | 60 days after issue = 27 Jun 2022 (also FAQ Q44, 07b) |
| Enforcement | s.70B(7) IT Act (Directions; FAQ Q23) |

- FAQ Q30 lists criteria for what must be reported within 6 hours, which could read narrower than Annexure I.
- Directions also contain KYC/registration duties for data centres, VPS, cloud, VPN and virtual asset providers (conditional entity types; not in checks).

### B3b. Notice of 27 Jun 2022 (07b)
- Whole Directions effective 25 Sep 2022 for MSMEs (per S.O. 1702(E) of 1 Jun 2020, attached).
- Subscriber-validation items (v)(a), (v)(f) for data centres, VPS, cloud, VPN also effective 25 Sep 2022.
- Does NOT change the 6-hour duty, 180-day retention or NTP sync; only start dates.
- For IN-CERTIN-001: both dates are past; applies to everyone now.
- Not settled: whether the 2020 MSME thresholds are still current (could not verify); log storage location.

### B3c. FAQ (07c)
- Q35: logs "may be stored outside India" if produced to CERT-In in reasonable time.
- Q36: providers offering services to users in India must maintain logs and financial-transaction records "in Indian jurisdiction".
- The two answers address different things and must stay distinct (confirmed, section 11): Q35 covers overseas storage and production; Q36 states the jurisdictional requirement.
- FAQ says it is not a legal document and does not alter the Directions.
- Scope: Q7 (service providers, intermediaries, data centres, body corporates, VPS, cloud, VPN, virtual asset providers, Government organisations; not individuals); Q26 (any entity for cyber incidents, incl. foreign firms); Q29 (Point of Contact needed even without physical presence); Q25 (reproduces s.43A "body corporate" definition).
- Q18: narrowed, not closed. Lawyer needed.

## 7. Part C: current-status search

Searched five web queries and fetched the MeitY Rules PDF. Did not directly search egazette.gov.in or pib.gov.in listings. Nothing found is official. Absence is not proof.

| Topic | Finding | Source type | Date |
|---|---|---|---|
| Commencement shortening | No amending notification found. Jan 2026 proposal (meeting 23 Jan, comments due 4 Feb 2026) not notified. dpdprules.org: MeitY library checked 9 Oct 2026, only the RoD Order new | secondary (Mondaq, dpdprules.org, consentplix) | 9-17 Oct 2026 |
| s.16 restricted countries | None notified | secondary (Mondaq, iCompaaS) | Sep-Oct 2026 |
| s.17(3) startup exemption | None notified | secondary (Legal500, dpdactindia) | Aug-Oct 2026 |
| Significant Data Fiduciary | None found; consultation on criteria reportedly expected Q3-Q4 2026 (unconfirmed) | secondary | Sep 2026 |
| Board appointments | 6 May 2026 MeitY circular invited applications (1 Chairperson, 4 Members); April 2026 commentary says not all appointed; no appointment found | secondary (wiki marked "machine-extracted, not verified") | May-Oct 2026 |
| New MeitY FAQ on children, IP, cookies | None found. A DSCI-hosted "FAQs on Data Protection Board" exists; authorship unclear, Board-only, some rule cross-references do not match the Rules | secondary | 2026 |
| RoD Order publication | Reported published 6 Oct 2026, consistent with gazette header | secondary | Oct 2026 |

Official fetches: MeitY Rules URL returned the same pre-corrigendum text as file 01; PIB backgrounder extract says "14 November 2025". veritect.ai still repeats the false Fourth Schedule startup claim.

## 8. Open questions

| Q | Status |
|---|---|
| Q1 | Narrowed (metadata shows 14 Nov; second-cross-checked); legal date still for a lawyer |
| Q2 | Partly settled (no IP/cookie/device-identifier terms verified); whether IP is personal data still for a lawyer |
| Q3, 9, 10, 11, 12, 15, 16, 19, 20 | Unchanged |
| Q4 | Sharpened (add r.10(1) qualifier; confirmed in section 11); sufficiency still for a lawyer |
| Q5 | Closed on text (undefined); meaning still for a lawyer |
| Q6 | Sharpened (r.8(3) has no class limit; the Third Schedule limit is in r.8(1); confirmed in section 11) |
| Q7 | Closed on text (see A4) |
| Q8 | Unchanged |
| Q13 | Closed on the English text (see B2; full-text scan pending); Hindi/English sub-question stays open as Q21 (unverified) |
| Q14 | No change found; re-check Gazette before release |
| Q17 | Definition verified; commercial ed-tech application for a lawyer |
| Q18 | Narrowed (see B3c; Q35 and Q36 confirmed in section 11) |

New questions:
- Q21: Hindi vs English wording of the RoD Order on s.9(1). **Unverified**: the Hindi reading came from extracted text and needs a Hindi reader.
- Q22: how the Schedules commence (inference from cross-references).
- Q23: definition of "body corporate" once s.43A is omitted on 13 May 2027 (SPDI Rules and CERT-In FAQ rely on it).
- Q24: whether the 2020 MSME criteria are still current.

## 9. Proposed edits (not applied)

Corrections in v2: the `sources.md` P9 URL row is withdrawn and replaced; the `checks.md` S.O. 5458(E) row no longer states the Hindi wording as verified; Schedules rows are labelled inferred; Q6 and metadata rows are sharpened.

### timeline.md
| Replace | With |
|---|---|
| `A secondary source also says the electronic publication stamp reads 14 Nov 2025. I could not verify that stamp (NOT VERIFIED).` | `The e-Gazette IDs of G.S.R. 843(E) and 846(E) are CG-DL-E-14112025-267647 and -267650, and the Government Press signatures are dated 14 Nov 2025 (10:37:23 and 10:43:53 IST). The issue headers and datelines say 13 Nov. The same one-day lag appears on G.S.R. 892(E) and S.O. 5458(E); that this reflects an upload lag is an inference. (official metadata; second cross-check, 2026-10-29)` |
| `\| 10 Dec 2025 \| Corrigendum to the Rules \| G.S.R. 892(E) (P7) \| NOT VERIFIED (secondary only) \|` | `\| 10 Dec 2025 (Gazette No. 806 of 11 Dec) \| Corrigendum to the Rules \| G.S.R. 892(E) (P7) \| Verified (official PDF, file 04) \|` |
| `\| 5-6 Oct 2026 \| Removal of Difficulties Order \| S.O. 5458(E) (P8) \| NOT VERIFIED (secondary only). Reported as wording fixes in s.9(1) and s.10(2)(c)(ii); no change to dates. \|` | `\| 5 Oct 2026 (Gazette No. 5248 of 6 Oct) \| Removal of Difficulties Order \| S.O. 5458(E) (P8) \| Read (official PDF, file 06; second cross-check on excerpt, full-text scan pending). Wording changes in Act s.9(1) and s.10(2)(c)(ii) only; no date or Rule changed. \|` |
| `The corrigendum (P7, unverified) reportedly changes that phrase to “in the Official Gazette” without naming a day. The text I read is pre-corrigendum.` | `The corrigendum (verified, file 04) changes that phrase to “in the Official Gazette” in r.1(3) and r.1(4) without naming a day. The Rules text read is pre-corrigendum, as is the text currently served at the MeitY URL.` |
| `…and the First Schedule \|` (Stage 2 row) | `…and, by cross-reference (inferred), the First Schedule (r.1 names no Schedule) \|` |
| `…Rules 1, 2, 17-21 (title, definitions, Board appointment, terms, meetings, digital office, staff) \|` | same, plus `; Fifth and Sixth Schedules by cross-reference to rules 18 and 21 (inferred)` |
| `Rules 3, 5-16, 22, 23 and the Second to Seventh Schedules` | `Rules 3, 5-16, 22, 23 and, by cross-reference (inferred), the Second, Third, Fourth and Seventh Schedules` |

### sources.md
| Replace | With |
|---|---|
| P2, P3 status "OPENED (mirror)" | "OPENED (official gazette PDF, files 03 and 01). The meity.gov.in URL also opened on 2026-10-29 with the same pre-corrigendum text." |
| P5 status "OPENED (mirror)" | "OPENED (gazette PDF, file 05; text layer has OCR-style typos)" |
| P7, P8 rows (section B) | Move to section A as OPENED (official), files 04 and 06 |
| P9 "NOT OPENED / refused" | "OPENED (file 07). Note: the direct PDF link `https://cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf` (printed in the 27 Jun 2022 notice, wrapped across two lines) returned 'The requested URL is not found' on 2026-10-29. A government-portal source lists the Directions page as `https://www.cert-in.org.in/Directions70B.jsp`." |
| ~~P9 URL note: "file 07b prints the URL as …CERTIn_Directions…, which differs from the URL in this register"~~ | **WITHDRAWN.** Probable line-break artifact: the URL wraps at "CERT-" in the notice, and the original has a hyphen. Do not apply. |
| P10 | "OPENED (file 07c). Document says only 'May 2022'." |
| P1 | Add: "Attached file 02 is the original gazette. The India Code footnote is not attached." |
| Add row P9b | "27 Jun 2022 extension notice (file 07b), OPENED" |
| Section D | Add: "PIB backgrounder extract: 'notified on 14 November 2025' (official; confirms the 14 Nov variance)" |

### checks.md
| Replace | With |
|---|---|
| `"Rules" = P3 (pre-corrigendum text, mirror)` | `"Rules" = P3 (pre-corrigendum text, official gazette PDF file 01; the corrigendum changes no substantive rule)` |
| IN-DPDP-011 "an identifiable adult" | "an adult who is identifiable if required in connection with compliance with any law for the time being in force in India" (r.10(1); confirmed, section 11) |
| `The Oct 2026 Removal of Difficulties Order reportedly adds "of" in s.9(1) (P8, unverified).` | `S.O. 5458(E) (file 06; second cross-check on excerpt) inserts "of" in the English text of s.9(1). A possible Hindi/English wording difference is unverified (Q21). r.11 requires the guardian to be appointed by a court, designated authority or local level committee; Fourth Sch Part A also covers crèche and day-care individuals.` |
| IN-DPDP-016 `Separately, such fiduciaries must retain the data, traffic data and logs…` | `Separately, r.8(3) says "a Data Fiduciary" (the Third Schedule class limit is in r.8(1), not r.8(3)) must retain at least one year… (scope unresolved, Q6; r.8(3) wording confirmed, section 11).` |
| IN-DPDP-018 `Act s.16; Rules r.13(4), r.13(5), r.15.` | `Act s.16; Rules r.13(4), r.15 (r.13(5) only defines "committee").` |
| IN-DPDP-008 `A contact for data questions is visible from the home page or app settings in at most two clicks` | Prefix: "BEST PRACTICE (not in r.9, which says 'prominently'):" |
| IN-DPDP-019 `s.10(2)(c)(ii) is reportedly reworded to "data audit" by the Oct 2026 Order (P8, unverified).` | `s.10(2)(c)(ii) reads "data audit" under S.O. 5458(E) (file 06; second cross-check on excerpt). r.13(1) still says "audit" and is unamended.` |
| IN-CERTIN-001 source "(P9, **NOT OPENED**; …)" | "(P9 opened, file 07; extension notice 07b; FAQ 07c)" |
| IN-CERTIN-001 applies_from | "In force. Effective 27 Jun 2022 per the Directions; 25 Sep 2022 for MSMEs per the 27 Jun 2022 notice." |
| IN-CERTIN-001 pass_criteria "logs stored in India" | "logs of all ICT systems retained 180 days rolling and producible to CERT-In. India-hosted storage is the conservative reading; FAQ Q35 allows storage abroad if produced in reasonable time; FAQ Q36 uses 'Indian jurisdiction' for financial-transaction logs (the two answers stay distinct); the FAQ is non-binding. Report storage location as information only." |
| IN-CERTIN-001 confidence "low-medium. Primary text unread." | "medium. Primary text read; storage-location scope unresolved." |
| IN-CERTIN-002 source "(P9, NOT OPENED)…" | "(P9, opened, file 07, directions (ii)-(iii), Annexures I-II). 20 incident categories. Point-of-contact details must be emailed to CERT-In in the Annexure II format." |
| Least-confident item 5 "primary text unread" | "primary text now read; storage-location scope unsettled" |
| IN-SPDI-001 `(P5, via mirror)` | `(P5, official gazette PDF file 05)` |

### overlaps.md
| Replace | With |
|---|---|
| `Source status: P9 not opened. Duties below come from consistent law-firm summaries and are NOT VERIFIED against the PDF.` | `Source status: P9 opened (file 07), with the 27 Jun 2022 notice (07b) and the May 2022 FAQ (07c). Duties are verified against the Directions unless marked FAQ.` |
| Logs row | Add: "FAQ Q35 allows storage abroad if produced to CERT-In in reasonable time; FAQ Q36 uses 'Indian jurisdiction' for financial-transaction logs. Keep the two answers distinct." |
| `Designate one` (Point of contact row) | "Designate one and email details to CERT-In in the Annexure II format" |
| Remedy row / section 2 | Add: "SPDI r.2(1)(c) and CERT-In FAQ Q25 both rely on the s.43A definition of 'body corporate'; s.43A is omitted from 13 May 2027 (Q23)." |
| "closed list in r.3" | "enumerated list in r.3 (items (i)-(viii), including related details)" |
| Retention row | Add: "r.8(3) says 'a Data Fiduciary'; the Third Schedule class limit is in r.8(1), not r.8(3) (Q6)." |

### open-questions.md
| Replace | With |
|---|---|
| Q1 `The corrigendum reportedly rewords Rule 1(3)/(4) without naming a day (P7, unverified).` | `The corrigendum (verified) rewords r.1(3)/(4) to "in the Official Gazette" without naming a day. The e-Gazette IDs and press signatures on both notifications are dated 14 Nov 2025; the issue headers and datelines say 13 Nov.` |
| Q4 | Add: "r.10(1) requires the parent to be an adult 'identifiable if required in connection with compliance with any law for the time being in force in India'." |
| Q5 `The terms are not defined in the Act or in the Rules I read (r.1-r.23 and schedules).` | `Verified: not defined in the Act (file 02) or the English Rules (file 01). They appear only in s.9(3) and Fourth Schedule Parts A-B.` |
| Q6 | Add: "Confirmed (second cross-check): r.8(3) says 'a Data Fiduciary'. The Third Schedule class limit appears in r.8(1), not r.8(3)." |
| Q7 | "Closed on text: the only 90-day text is r.14(3) (grievance system). No rule sets a deadline for s.11/12 requests. PIB's broader statement is unsupported by the Rules." |
| Q13 `I only have secondary reports (P8).` | `Read on the English text (file 06; second cross-check on excerpt, full-text scan pending): the Order changes only the wording of s.9(1) (adds "of") and s.10(2)(c)(ii) ("data audit"). No date or Rule changed.` |
| Q18 | Add: "Narrowed: FAQ Q35 allows storage abroad if produced in reasonable time; Q36 uses 'Indian jurisdiction' for financial-transaction logs; the FAQ is non-binding." |
| Add Q21-Q24 | As listed in section 8. Mark Q21 "unverified by a Hindi reader; extracted text was unreliable". |

### README.md
| Replace | With |
|---|---|
| `The 14 Nov date comes from PIB and law-firm articles.` | `The 14 Nov date comes from the PIB backgrounder, law-firm articles, and the e-Gazette upload metadata (IDs and press signatures dated 14 Nov, files 01 and 03).` |
| "What I could not verify": bullets on the official MeitY PDF, corrigendum, RoD Order, CERT-In Directions and FAQs | Delete (now read). Add: "India Code footnote (not attached); Hindi Rules and Order text not compared; Part C 'nothing notified' claims remain secondary; human read of the PDF passages pending." |

## 10. Could not verify, and top five findings

Could not verify:
- The legal "date of publication" (13 or 14 Nov).
- The India Code commencement footnote (not attached).
- The PIB 90-day claim.
- All "nothing notified" items (s.16, s.17(3), SDF, s.9(5), Board appointments, FAQ, date compression); official gazette sites not searched.
- Consumer Protection (E-Commerce) Rules 2020, RBI circular, IT Act text, Intermediary Rules 2021.
- The Hindi versions of the Rules, the Act and the RoD Order (including the Q21 observation).
- Cryptographic validity of gazette signatures.
- Whether the 2020 MSME thresholds are current.
- Corrigendum item 8 by exact phrase.
- Full-text scan of S.O. 5458(E) (all three pages).
- A person's read of the PDF passages behind the five items in section 11.

Top five findings (unchanged by the cross-check, which confirmed items 1, 3, 4 and 5 in part):
1. IN-CERTIN-001 changes. Primary text read; both effective dates (27 Jun and 25 Sep 2022) are past. "Logs stored in India" should no longer be the pass criterion: FAQ Q35 permits storage abroad if producible in reasonable time, Q36 points the other way. Report storage location as information only.
2. Date handling. Official metadata supports 14 Nov as well as 13 Nov, so the variance is real. Keep 13 Nov 2026 / 13 May 2027 as defaults, in config.
3. IN-DPDP-011 and 016 need correcting: 011 omits the r.10(1) "identifiable if required" qualifier; 016 wrongly limits r.8(3) retention to Third Schedule classes (the class limit is in r.8(1)).
4. Corrigendum and RoD Order are minor: eight non-substantive edits; two Act phrases changed, no date or Rule. The "pre-corrigendum" caveat can go. The Hindi/English question on s.9(1) is unverified and needs a Hindi reader and a lawyer.
5. Q7 and Q5 close on the text: no deadline rule for rights requests (only r.14(3) for grievances); tracking, behavioural monitoring, IP address and cookie are undefined. The skill should present third-party calls as an inventory with "legal status unclear".

Also note: the Schedules commencement mapping is inferred, and the s.43A "body corporate" definition issue arises after 13 May 2027.

Verified items: 16. Not verified: 12 (10 from the first pass, plus the Order's full-text scan and the human read of the PDF passages). Second cross-check: 5 items confirmed on supplied excerpts (section 11).

## 11. Second cross-check of five findings (2026-10-29)

Method: each item was checked against excerpts supplied after the first report. Status is "second cross-check, confirmed". It becomes "human-read" only when a person has opened the PDF and read the passage. Record that in `verification-log.md`.

| # | Item | Result | What was confirmed | Effect |
|---|---|---|---|---|
| 1 | Rule 10(1), parental identification | Confirmed | The parent must be an adult who is "identifiable if required in connection with compliance with any law for the time being in force in India". | Keep the conditional qualifier in check 011. Do not simplify it to an unconditional requirement. |
| 2 | Rule 8(3), one-year retention | Confirmed | Sub-rule (3) says "a Data Fiduciary" and requires retention for at least one year of the specified personal data, associated traffic data and other processing logs. The Third Schedule class limit appears in r.8(1), not r.8(3). | Check 016 and Q6 must say r.8(3) is not limited to the Third Schedule classes. |
| 3 | S.O. 5458(E), Removal of Difficulties Order | Confirmed on excerpt | Two substitutions only: s.9(1) "child or a person with disability" becomes "child or of a person with disability"; s.10(2)(c)(ii) "audit" becomes "data audit". Commencement is on publication in the Official Gazette. No fixed date, and no Rule amended. | Q13 closed on the English text. The full text of all three pages is still to be scanned. The Hindi wording stays unverified (Q21). |
| 4 | CERT-In FAQ Q35 and Q36, log location | Confirmed | Q35: logs may be stored outside India if the entity can produce them to CERT-In within a reasonable time. Q36: service providers serving users in India must enable and maintain logs and financial-transaction records in "Indian jurisdiction". | Keep the answers distinct. IN-CERTIN-001 reports storage location as information only, never pass/fail. |
| 5 | e-Gazette metadata | Confirmed | File 01 (Rules): ID `CG-DL-E-14112025-267650`; signature 14 Nov 2025, 10:43:53 IST. File 03 (G.S.R. 843(E)): ID `CG-DL-E-14112025-267647`; signature 14 Nov 2025, 10:37:23 IST. | Q1 narrowed, not closed. The metadata shows signing and upload, not the legal publication date. |

**Page references to re-confirm.** The supplied references were: file 01, ID on "Page 1 · English masthead" and signature on p.41; file 03, ID on p.1 and signature on p.2. The register (section 1) says file 01 has Hindi on pp.1-23 and English on pp.24-41, so the English masthead should be on p.24, not p.1. Check which page holds the ID before recording page numbers in `verification-log.md`.