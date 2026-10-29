# India: Overlaps (SPDI, CERT-In, sector rules) with DPDP

Retrieved 2026-10-29. Source IDs refer to `sources.md`. Research only; not legal advice.

## 1. Which regime applies when

| Phase | Dates | Regimes in force for an ordinary app |
|---|---|---|
| A | Now to 12 Nov 2026 | IT Act s.43A + SPDI Rules; CERT-In Directions; sector rules (RBI, E-Commerce Rules, etc.). DPDP Board machinery only. |
| B | 13 Nov 2026 to 12 May 2027 | Same as A. DPDP adds Consent Manager registration only. |
| C | From 13 May 2027 | DPDP Act and Rules; CERT-In Directions; sector rules. s.43A is omitted (Act s.44(2)(a)); the SPDI rule-making power s.87(2)(ob) is omitted (s.44(2)(c)). **Survival of the SPDI Rules is unresolved** (open-questions.md Q8). |

Verified in P1: s.44(2) commences with the 18-month group. s.38 (DPDP prevails over conflicting law "to the extent of conflict") is already in force but has nothing to bite on until the substantive sections start.

## 2. SPDI Rules 2011 versus DPDP

The SPDI Rules were made under s.87(2)(ob) read with s.43A (P5 preamble). They bind a "body corporate" and mostly protect "sensitive personal data or information" (SPDI), an enumerated list in r.3 (items (i)-(viii), including related details).

| Topic | SPDI Rules (P5) | DPDP Act/Rules (P1, P3) | Practical difference |
|---|---|---|---|
| Who is covered | Body corporate (and persons acting for it). SPDI r.2(1)(c) and CERT-In FAQ Q25 both rely on the s.43A definition of 'body corporate'; s.43A is omitted from 13 May 2027 (Q23). | Any "person" who decides purpose and means (s.2(i), s.2(s)), including individuals, firms, the State | DPDP is wider |
| What data | SPDI list (passwords, financial instruments, health, sexual orientation, medical records, biometrics) for consent and disclosure rules; "personal information" for the policy and security rules | All digital personal data (s.3(a)), no sensitivity tiers | DPDP removes the tiering |
| Privacy policy / notice | r.4: published policy | s.5 and r.3: notice before or with each consent request, standalone, itemised, purposes, rights routes | DPDP notice is per request and more detailed |
| Consent form | r.5(1): written consent by letter, fax or email, for SPDI | s.6(1): free, specific, informed, unconditional, unambiguous, clear affirmative action | DPDP is technology-neutral and stricter on quality |
| Withdrawal | r.5(7): in writing | s.6(4): as easy as giving; r.3(c)(i) | DPDP removes the "in writing" friction |
| Grievance | r.5(9): Grievance Officer named on website; one month | s.8(10), s.13, r.14(3): published mechanism; cap up to 90 days; r.9 contact | Time limits differ: **one month (SPDI) versus up to 90 days (DPDP)**. While both apply the shorter one is safer. |
| Disclosure to third parties | r.6: prior permission for SPDI unless agreed in contract or legally required | Consent or legitimate use is the ground for any processing, which includes disclosure (s.2(x), s.4); processors only under contract (s.8(2)) | DPDP covers all disclosures |
| Transfer abroad | r.7: for SPDI, to a body ensuring the same level of protection, and only if necessary for the contract or with consent | s.16: allowed unless the destination is notified as restricted; none notified | DPDP default is permissive. SPDI r.7 is stricter for SPDI while it lasts. |
| Security | r.8: documented programme; ISO/IEC 27001 as a recognised standard; safe harbour with independent audit at least yearly | s.8(5), r.6: baseline measures; penalty up to INR 250 crore | DPDP has an explicit minimum list; no ISO safe harbour in the text I read |
| Retention | r.5(4): no longer than needed | s.8(7), r.8: erase on withdrawal or purpose served; one-year minimum retention of data and logs for specified purposes. r.8(3) says 'a Data Fiduciary'; the Third Schedule class limit is in r.8(1), not r.8(3) (Q6). | DPDP creates a retention floor as well as a ceiling (Q6) |
| Breach notice | none (SPDI has no breach clause) | s.8(6), r.7: users and Board | New duty |
| Remedy | s.43A: compensation for failure to protect (text not verified, P12) | Board penalties (Act Schedule); no compensation provision to the principal; civil court barred (s.39) | Different enforcement model |
| Children | none | s.9, r.10-12 | New duty |

## 3. CERT-In Directions (28 Apr 2022) versus DPDP

Source status: P9 opened (file 07), with the 27 Jun 2022 notice (07b) and the May 2022 FAQ (07c). Duties are verified against the Directions unless marked FAQ.

| Topic | CERT-In (reported) | DPDP | Overlap note |
|---|---|---|---|
| Incident reporting | Report listed incidents to CERT-In within 6 hours of noticing | Users: without delay. Board: without delay, then detailed report within 72 hours (r.7) | Separate recipients and clocks. A single event can trigger both. Build one runbook with both timers. |
| Logs | Enable logs of all ICT systems; keep 180 days within Indian jurisdiction. FAQ Q35 allows storage abroad if produced to CERT-In in reasonable time; FAQ Q36 uses 'Indian jurisdiction' for financial-transaction logs. Keep the two answers distinct. | r.6(1)(e): keep logs and personal data one year for detecting unauthorised access; r.8(3): keep personal data, traffic data and logs at least one year | Take the longer period (one year) while DPDP applies. The location requirement comes from CERT-In only. |
| Clocks | NTP sync to NIC/NPL | none | CERT-In only |
| Point of contact | Designate one and email details to CERT-In in the Annexure II format | r.9: published contact for data questions | Different purposes; the same person may serve both |
| Scope | Service providers, intermediaries, data centres, body corporates, government organisations | Data Fiduciaries | CERT-In covers non-personal-data incidents too |
| Enforcement | s.70B(7) IT Act | Board penalties | Separate |

## 4. Other Indian instruments

| Instrument | Status of my review | What matters for developers |
|---|---|---|
| **IT (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021** | **NOT EXAMINED** (P13). | Relevant only if the app hosts user-generated content. Grievance officer and takedown timelines exist, but I have not read them. The DPDP Rules also use the Intermediary Rules' definition of "social media intermediary" in the Third Schedule (P3). |
| **Consumer Protection (E-Commerce) Rules, 2020** | Text of r.4(4), r.4(5), r.4(9) seen via mirrors; official PDF not opened (P11). | Grievance officer displayed; 48-hour acknowledgement; one-month resolution; no pre-ticked purchase consent. Applies only to e-commerce entities. The Third Schedule of the DPDP Rules borrows the Consumer Protection Act definition of "e-commerce entity". |
| **RBI: Storage of Payment System Data (6 Apr 2018)** | Extract of RBI FAQ only (P6). | Applies to RBI-authorised payment system providers. Requires payment data stored only in India; 24-hour return rule if processed abroad. Not every merchant app is covered. This is a "higher degree of restriction on transfer" example that s.16(2) of the Act preserves. |
| **Other RBI, SEBI, IRDAI rules** | Not examined. | If the app is a regulated entity or a regulated entity's vendor, a lawyer must check sector directions. |
| **Telecom/DoT** | Not examined. | Out of scope for this pass. |

## 5. Rules for the skill

1. Report overlap checks by regime, not as one merged "India score".
2. While Phase A/B applies, SPDI and CERT-In checks are the only ones with present legal force. DPDP checks are readiness checks until 13 May 2027.
3. Where two regimes set different numbers, show both and recommend the stricter as best practice (one-month grievance; one-year logs; 6-hour CERT-In clock).
4. Never present sector checks (RBI, E-Commerce Rules) unless the app has been tagged as that kind of entity.
