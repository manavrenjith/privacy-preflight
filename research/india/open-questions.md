# India: Open Questions for a Lawyer

Retrieved 2026-10-29. Each question says why it is unclear. Source IDs refer to `sources.md`. None of this is legal advice.

## Q1. What is the legal "date of publication", 13 or 14 Nov 2025?
Both notifications count one year and eighteen months from "the date of publication". The dateline says 13 Nov; the PIB backgrounder and several firms say 14 Nov; the India Code footnote uses 13 Nov. The corrigendum (verified) rewords r.1(3)/(4) to "in the Official Gazette" without naming a day. The e-Gazette IDs and press signatures on both notifications are dated 14 Nov 2025; the issue headers and datelines say 13 Nov. **Why unclear:** the Act's own commencement mechanics (s.1(2)) do not say which publication date counts. **Impact:** one day on 13/14 Nov 2026 and 13/14 May 2027. Ask whether a conservative reading (13th) is safe. (Narrowed: metadata verified, legal date remains for a lawyer).

## Q2. Is a visitor IP address sent to a foreign third party (e.g. Google Fonts) a regulated disclosure or transfer?
Pieces I could establish:
- "Personal data" means data about an individual who is identifiable by or in relation to the data (s.2(t)). Neither the Act nor the Rules mention IP addresses, cookies or device identifiers.
- "Processing" includes sharing and disclosure by transmission (s.2(x)). Whether an automatic browser request to a font host is a "disclosure" by the site owner is not addressed.
- s.16 restricts transfers only to countries the Government notifies, and none is notified; r.15 depends on orders not yet found. So even if it is a transfer, no country restriction currently bites.
- The notice duty (s.5) and consent specificity (s.6(1)) could be engaged if the IP is personal data and consent is the ground. But if the font provider is a processor, s.8(2) requires a contract; if it is an independent fiduciary, who needs a basis for the disclosure?
- The SPDI Rules' transfer rule (r.7) applies only to SPDI, and an IP address is not on the r.3 list.

**Why unclear:** no text on cookies or passive network identifiers; no Board guidance (the Board has no reported members as of Oct 2026, secondary); no case law. **Ask:** (a) is an IP address "personal data" when collected by a CDN/font host? (b) Can the website owner treat the third party as a processor, or does it need a legal basis for the disclosure? (c) Does the 13 May 2027 start date apply to sites already live?

## Q3. Do small apps and startups get an exemption?
s.17(3) lets the Government notify classes (startups named) as exempt from s.5, s.8(3), s.8(7), s.10 and s.11, "having regard to volume and nature" of data. **No notification found** (secondary sources, Aug-Sep 2026). The Rules contain thresholds only for the Third Schedule erasure periods (large e-commerce, gaming and social media), not a small-business exemption. s.3(c)(i) excludes personal or domestic use by individuals. s.17(1) exempts certain processing (enforcing legal claims, offshore contracts, etc.). Note even a startup exemption would not remove s.6, s.8(5), s.8(6) or s.9. **Why unclear:** it is a power, not a grant; scope is unknown until notified; "startup" is defined by reference to a future DPIIT-linked process.

## Q4. How does "verifiable" parental consent work for a small developer?
Rule 10 needs a check that the person claiming to be the parent is an identifiable adult, by reference to reliable identity and age details the fiduciary already holds, or details voluntarily provided directly, or through a virtual token from an authorised entity (the text mentions Digital Locker service providers). r.10(1) requires the parent to be an adult 'identifiable if required in connection with compliance with any law for the time being in force in India'. It does not say: whether self-declaration or a payment-card check suffices; what "reliable details available with the Data Fiduciary" means for a new user; how a parent-child link is established; whether a developer may rely on a third-party age or identity service; or whether DigiLocker-based tokens are practically available to small developers. No age-assurance guidance from the Board or MeitY was found. Also: "child" is under 18 with no age band, and no s.9(5) notification was found.

## Q5. What is "tracking or behavioural monitoring" and "targeted advertising directed at children"?
Verified: not defined in the Act (file 02) or the English Rules (file 01). They appear only in s.9(3) and Fourth Schedule Parts A-B. Closed on text. Open for a lawyer: whether first-party product analytics, crash reporting, fraud detection or contextual ads are caught; how a mixed-audience product should treat child accounts; and how the Fourth Schedule Part B items (e.g. keeping harmful content or ads away from children; age confirmation) interact with ad systems.

## Q6. How do the one-year retention duties fit with erasure rights?
Rule 8(3) requires retention of personal data, traffic data and logs for at least one year for Seventh Schedule purposes, and the illustration says a platform keeps order data even if the user deletes the account. Rule 6(1)(e) separately requires one-year log and data retention for security. Yet s.8(7) and s.12(3) oblige erasure on withdrawal or request unless retention is "necessary for compliance with any law". Confirmed (second cross-check): r.8(3) says 'a Data Fiduciary'. The Third Schedule class limit appears in r.8(1), not r.8(3). **Unclear:** whether r.8(3) is a retention "law" for that exception; scope remains unresolved between general fiduciaries and specific classes; and what should happen to user-facing deletion promises. Affects every deletion flow the skill checks.

## Q7. What is the time limit for access, correction and erasure requests?
Closed on text: the only 90-day text is r.14(3) (grievance system). No rule sets a deadline for s.11/12 requests. PIB's broader statement is unsupported by the Rules. Residual lawyer question: whether the grievance route is the expected channel for late rights requests.

## Q8. What happens to the SPDI Rules after 13 May 2027?
s.44(2) omits s.43A and s.87(2)(ob), the provisions the SPDI Rules were made under. Nothing I read says the SPDI Rules are repealed. **Unclear:** whether they lapse, survive as orphaned subordinate legislation, or are overridden only where in conflict under s.38(2). Also how s.43A claims that arose before 13 May 2027 are handled.

## Q9. How granular must the notice be, and can it sit inside a signup flow?
r.3(a) requires the notice to be understandable independently of other information. Unclear whether an in-flow notice on the consent screen suffices, whether a layered notice is acceptable, and whether each purpose needs separate consent (s.6(1) says "specified purpose", singular).

## Q10. What must existing users receive?
s.5(2) requires notice "as soon as reasonably practicable" to people who consented before commencement; processing may continue until withdrawal. Unclear whether r.3 applies in full to those notices, and what "reasonably practicable" means after 13 May 2027.

## Q11. Territorial reach for apps outside India and for non-resident users
s.3(b) reaches processing outside India linked to offering goods or services to people in India. s.17(1)(d) disapplies most duties for non-resident principals' data processed under a contract with a person outside India. Unclear how a global SaaS with Indian visitors is treated, and how s.16 applies to onward processing.

## Q12. Does the Consent Manager regime on 13 Nov 2026 affect developers?
Rule 4 starts 13 Nov 2026, but no registration process was located. Unclear whether fiduciaries must accept consent through a Consent Manager (s.6(7) says the principal "may" use one) and what an integration obligation would look like.

## Q13. Is the Removal of Difficulties Order confined to wording fixes?
Read on the English text (file 06; second cross-check on excerpt, full-text scan pending): the Order changes only the wording of s.9(1) (adds "of") and s.10(2)(c)(ii) ("data audit"). No date or Rule changed. Closed on the English text. Residual question for a lawyer: whether further orders under s.43(2) (permitted until three years after commencement) are likely.

## Q14. Are there pending changes to dates?
MeitY floated shortening the window in Jan 2026. As of 12-17 Oct 2026, trackers found no notification. **Why unclear:** the Government can appoint dates by notification at any time (s.1(2)) and s.43 allows removal-of-difficulties orders. Re-check the Gazette immediately before release.

## Q15. UGC and the IT Intermediary Rules
I did not read these (P13). If the app hosts user content, a lawyer should map grievance officer, takedown and traceability duties against DPDP r.9, r.14 and the Third Schedule definitions.

## Q16. Language access
s.5(3) and s.6(3) give the option of English "or any language specified in the Eighth Schedule". Unclear whether a service must support all 22 languages or only languages it serves.

## Q17. Fourth Schedule exemption scope for ed-tech and similar services
Educational institutions are exempt for tracking or behavioural monitoring only for educational activities or safety. Unclear whether commercial ed-tech platforms qualify as "educational institution" ("an institution of learning that imparts education, including vocational education").

## Q18. CERT-In "within Indian jurisdiction" for logs
Narrowed: FAQ Q35 allows storage abroad if produced in reasonable time; Q36 uses 'Indian jurisdiction' for financial-transaction logs; the FAQ is non-binding. Still unclear whether "within Indian jurisdiction" in Direction (iv) mandates India-hosted storage or availability on order.

## Q19. Rule 15 orders and "foreign State" entities
Rule 15 refers to requirements the Government may specify for making data available to a foreign State or entities under its control. No such order was found. Unclear what "making available" covers for ordinary SaaS vendors.

## Q20. "Personal data breach" has no materiality threshold
s.2(u) covers any unauthorised processing or accidental disclosure or loss of access that compromises confidentiality, integrity or availability. Unclear whether trivial incidents must be reported to the Board (the Board may only impose penalty for "significant" breach, s.33(1), but the duty to intimate in s.8(6) is unqualified).

## Q21. Does the Hindi text of the Removal of Difficulties Order (S.O. 5458(E)) alter s.9(1) differently from the English text?
The English text inserts "of" ("child or of a person with disability"). The Hindi operative text appears to substitute "ऐसे" ("such") rather than a "के" ("of") equivalent. Unverified by a Hindi reader; extracted Hindi text unreliable. Needs confirmation by a Hindi reader and review by a lawyer.

## Q22. How do the Schedules commence under G.S.R. 846(E)?
Rule 1 names no Schedule. The commencement mapping (First Schedule with Rule 4; Fifth and Sixth Schedules with Rules 18 and 21; Second, Third, Fourth and Seventh Schedules with the substantive rules) is inferred from cross-references within the rules. Unclear whether the absence of explicit Schedule commencement creates ambiguity (for a lawyer).

## Q23. What defines a "body corporate" once IT Act s.43A is omitted on 13 May 2027?
Both SPDI Rule 2(1)(c) and CERT-In FAQ Q25 rely on the s.43A definition of "body corporate". Under DPDP Act s.44(2)(a), s.43A is omitted from 13 May 2027. Unclear how "body corporate" is defined once s.43A falls away.

## Q24. Are the 2020 MSME criteria in CERT-In Notice 07b still current?
The 27 Jun 2022 extension notice annexed S.O. 1702(E) of 1 Jun 2020 for the MSME definition and thresholds. Unclear whether the 2020 MSME criteria are still current.
