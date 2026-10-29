# India Privacy Research: Summary

Prepared 2026-10-29 for the open-source "privacy ship-check" skill. **Research only. Not legal advice. Nothing here says any app is "compliant."**

## Files

| File | Contents |
|---|---|
| `sources.md` | Source register, with what I opened and what I could not |
| `timeline.md` | Commencement dates, what applies in each phase |
| `checks.md` | 25 candidate checks (19 DPDP, 6 related regimes), with top-5 / bottom-5 confidence |
| `overlaps.md` | SPDI, CERT-In, e-commerce, RBI versus DPDP |
| `open-questions.md` | 24 items for a lawyer |

## Headline findings

1. **Your staged dates need correcting.** The gazette dateline and the Act's own India Code footnote support **13 Nov 2025 / 13 Nov 2026 / 13 May 2027**, not 14. The 14 Nov date comes from the PIB backgrounder, law-firm articles, and the e-Gazette upload metadata (IDs and press signatures dated 14 Nov, files 01 and 03). Treat 14 as a possible one-day variance (timeline.md, open-questions Q1).
2. **Almost nothing developer-facing applies yet.** Notice, consent, children, security, breach, erasure, rights and transfer duties start **13 May 2027**. On 13 Nov 2026 only Consent Manager registration (Rule 4; s.6(9)) starts. Until May 2027 the operative regimes are the SPDI Rules and s.43A, CERT-In Directions, and sector rules.
3. **No shortened timeline has been notified.** MeitY floated 12 months for some entities in Jan 2026. Trackers checking up to mid-Oct 2026 found no amendment. Secondary only; re-check the Gazette before shipping. The **Removal of Difficulties Order (S.O. 5458(E), 5 Oct 2026)** has been read (official PDF, file 06): it makes two wording fixes (s.9(1) and s.10(2)(c)(ii)) without changing dates. The **corrigendum (G.S.R. 892(E))** has also been verified (official PDF, file 04): eight minor wording fixes, no date or substantive rule changed.
4. **The law is silent on third-party requests.** Nothing in the Act or Rules addresses analytics, fonts, CDNs, embeds or cookies. The Google Fonts question rests on whether an IP address is "personal data" and whether a browser request is a "disclosure": unresolved (Q2). The skill should output an inventory, not a violation.
5. **No cross-border restriction exists today.** s.16 is a negative list. No country, Rule 15 order or Rule 13(4) specification had been located as of Oct 2026 (secondary).
6. **Children:** "child" means under 18, with no age band. Parental consent verification (Rule 10) and the ban on tracking and targeted ads (s.9(3)) are clear on their face but key terms are undefined (Q4, Q5).
7. **There are internal tensions in the Rules** the skill should not paper over: one-year retention versus erasure (Q6), 90-day cap applied only to grievances in the text (Q7).

## What I could not verify

- **India Code footnote:** not attached in official PDF file 02 (which is the original gazette).
- **Hindi text layers:** Hindi Rules and Order text not compared; extracted Hindi text unreliable.
- **Human read of PDF passages:** AI reading of official PDFs completed; human spot-checks of key passages pending.
- **Consumer Protection (E-Commerce) Rules 2020:** official PDF not opened; text seen on mirrors.
- **IT Act text (s.43A, s.70B, s.87), IT Intermediary Rules 2021:** not opened.
- **RBI circular of 6 Apr 2018:** only the RBI FAQ extract seen.
- **Gazette notifications G.S.R. 844(E)/845(E)** (Board establishment): not opened.
- **"Nothing notified" claims** (s.16, s.17(3), s.10, Rule 15, Board appointments, compression of dates): from secondary trackers and law-firm pages only. I did not search the e-Gazette directly.
- **Press note of 24 Aug 2011** on electronic consent under SPDI: not opened.

## Sources that conflict (details in sources.md section D)

- Notification date: 13 Nov (gazette, India Code) versus 14 Nov (PIB, some firms).
- 90-day period: PIB (all requests) versus Rules text (grievances only).
- A website claiming all Act sections commenced on 13 Nov 2025 contradicts the commencement notification.
- A site describing a startup exemption in the Fourth Schedule is wrong; that Schedule covers children's data.

## Suggested order to read the primary texts

1. **Act s.1, s.2, s.3** (P1): scope, definitions (child under 18; personal data; processing).
2. **G.S.R. 843(E)** (P2) and the India Code footnote: what starts when.
3. **Act ss.4-9** and **Rules r.3, r.6-r.10, r.14**: the core duties.
4. **Rules r.12 and the Fourth Schedule**: children's exemptions.
5. **Act s.16, s.17** and **Rules r.13, r.15**: transfers and exemptions.
6. **Act s.44(2)** and **s.38**: how the IT Act changes and which law prevails.
7. **SPDI Rules r.3-r.8** (P5): the regime in force now.
8. **CERT-In Directions and FAQ** (P9/P10, files 07, 07b, 07c), then the **Removal of Difficulties Order** (file 06) and the **corrigendum** (file 04).

## Recommendations for the skill (engineering, not legal)

- Keep effective dates and the restricted-country list in a config file, not in code.
- Mark every check as **in force now** (SPDI, CERT-In, sector) or **readiness** (DPDP, from 13 May 2027).
- Report third-party calls as an inventory with "legal status unclear".
- Show the "last verified" date on every rule.

## Confidence (full lists in checks.md)

**Most confident:** IN-DPDP-008, IN-DPDP-002, IN-DPDP-004, IN-SPDI-001, IN-DPDP-018.
**Least confident:** IN-DPDP-017, IN-DPDP-012, IN-DPDP-011, IN-DPDP-003, IN-CERTIN-001.

## Scope

India is done to the extent the sources allowed. I have not started Nigeria (NDPA 2023 + GAID 2025). Do you want me to proceed, and should I first try to close the gaps above (official PDFs, CERT-In text, corrigendum, RoD Order)?
