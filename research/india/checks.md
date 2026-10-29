# India: Candidate Checks

Retrieved 2026-10-29. Source IDs refer to `sources.md`. **Research notes, not legal advice. A passing check never means "compliant."**

**Conventions**
- "Act" = P1. "Rules" = P3 (pre-corrigendum text, mirror). "SPDI" = P5.
- `applies_from` for DPDP checks: **13 May 2027** (see timeline.md; 14 May if publication is read as 14 Nov 2025).
- `confidence` = how sure I am that (a) the check traces to a real provision and (b) the pass criterion is objective enough to automate. It is not a view on the legal merits.
- Labels: **LAW** = the provision says this. **BEST PRACTICE** = engineering inference, not a legal requirement.
- Official PDF URLs: Act https://www.indiacode.nic.in/bitstream/123456789/22037/2/a2023-22.pdf ; Rules https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf (not opened; read via mirror).

---

## Group 1: Notice and consent

### IN-DPDP-001
- **obligation (LAW):** Every request for consent is accompanied or preceded by a notice. The notice must make sense on its own (not depend on other documents), use plain language, itemise the personal data, and state each specified purpose and the specific goods, services or uses it enables.
- **source:** Act s.5(1); Rules r.3(a), r.3(b)(i)-(ii). Official URLs above.
- **applies_from:** 13 May 2027
- **detection:** assisted. Crawl signup, checkout and permission-request screens. Locate the notice linked at each consent point. Compare form fields (and mobile permissions) with the data items the notice lists. Flag consent UIs whose only notice is a link to a general terms page.
- **pass_criteria:** At each consent request there is a notice reachable at or before the request; every field or permission collected appears in an itemised list; each purpose is stated separately.
- **exemptions_or_caveats:** Not required for s.7 "certain legitimate uses" (consent is not the basis). s.17(3) lets the Government exempt classes (startups named) from s.5, but no such notification was found. "Independent" and "fair account" are judgment terms; the tool can only check structure.
- **confidence:** medium. The text is explicit; whether a notice is plain and sufficient is human judgment.

### IN-DPDP-002
- **obligation (LAW):** The notice gives the communication link to the website or app and describes the means to (i) withdraw consent as easily as it was given, (ii) exercise rights, (iii) complain to the Board.
- **source:** Act s.5(1)(ii)-(iii); Rules r.3(c).
- **applies_from:** 13 May 2027
- **detection:** automated for presence (find a working link plus text mentioning withdrawal, rights and complaint to the Board in the notice); assisted for adequacy.
- **pass_criteria:** The notice text contains a working link to the service and a described route for each of the three items.
- **exemptions_or_caveats:** Same as 001.
- **confidence:** high. Three enumerable items stated in the rule.

### IN-DPDP-003
- **obligation (LAW):** The notice and the consent request must be available in English or any language in the Eighth Schedule to the Constitution, at the person's option.
- **source:** Act s.5(3); s.6(3).
- **applies_from:** 13 May 2027
- **detection:** assisted. Check for a language selector or locale variants on notice and consent screens.
- **pass_criteria:** English is available, and a mechanism exists to access the notice in an Eighth Schedule language.
- **exemptions_or_caveats:** The text says "English or any language specified". Whether a fiduciary must offer *all* 22 languages, or only a language the principal selects, is unresolved (Q16).
- **confidence:** low. Pass criterion is ambiguous.

### IN-DPDP-004
- **obligation (LAW):** Consent is free, specific, informed, unconditional and unambiguous, given by a clear affirmative action, for a specified purpose.
- **source:** Act s.6(1) and its illustrations; s.6(2) (invalid parts).
- **applies_from:** 13 May 2027
- **detection:** automated for the objective part: scan HTML/JS and mobile layouts for consent checkboxes or toggles that default to checked/on; consent given by scrolling or continued use; a single checkbox covering several purposes (heuristic). Assisted for bundling and "unconditional".
- **pass_criteria:** No consent control is pre-selected; each purpose has its own control; the service is not conditional on consent to purposes that are unnecessary for it.
- **exemptions_or_caveats:** The Act does not use the word "cookie". Whether analytics cookies are consent-based processing is not addressed (see 017). Pre-ticked purchase consent is separately barred for e-commerce entities (IN-ECOM-001).
- **confidence:** medium. Pre-ticked detection is reliable; "unconditional" and bundling need judgment.

### IN-DPDP-005
- **obligation (LAW):** Consent covers only the personal data necessary for the specified purpose.
- **source:** Act s.6(1) and its telemedicine illustration (a request for the phone contact list is outside consent for a service that does not need it).
- **applies_from:** 13 May 2027
- **detection:** assisted. List form fields and mobile permissions (e.g. contacts, location, camera, SMS) and compare with the stated purposes. Flag high-risk permissions with no matching purpose in the notice.
- **pass_criteria:** Every collected field or permission maps to a stated purpose that requires it.
- **exemptions_or_caveats:** "Necessary" is contextual. This is a flag-for-review, not a pass/fail.
- **confidence:** medium-low.

### IN-DPDP-006
- **obligation (LAW):** The principal can withdraw consent at any time, with ease comparable to giving it.
- **source:** Act s.6(4); Rules r.3(c)(i).
- **applies_from:** 13 May 2027
- **detection:** assisted. Count steps and screens to give consent (signup) versus to withdraw (settings, email, support only). Look for an in-product withdrawal control.
- **pass_criteria:** Withdrawal is reachable through the same channel used to give consent, in no more steps than giving it.
- **exemptions_or_caveats:** Withdrawal does not undo earlier lawful processing (s.6(5)); the service may stop for features that depend on the data.
- **confidence:** medium. Step-count is measurable; "comparable" is a judgment.

### IN-DPDP-007
- **obligation (LAW):** On withdrawal, the fiduciary stops processing and causes its processors to stop, unless law requires or authorises continued processing. Personal data is erased on withdrawal or when the purpose is no longer served, whichever is earlier, and processors erase data given to them, unless retention is required by law.
- **source:** Act s.6(6); s.8(7); Rules r.8(3) (retention tension, see 016).
- **applies_from:** 13 May 2027
- **detection:** human-judgment, with code hints. Look for a withdrawal handler that updates a consent flag and for propagation to processors (queue, webhook, API call). Static analysis cannot confirm effect.
- **pass_criteria:** A code path exists that, on withdrawal, halts the related processing jobs and notifies each processor.
- **exemptions_or_caveats:** Conflicts with the one-year retention in Rules r.8(3) (Q6).
- **confidence:** low for automation; high that the obligation exists.

---

## Group 2: Rights, contact and grievance

### IN-DPDP-008
- **obligation (LAW):** Prominently publish on the website or app the business contact information of the Data Protection Officer (if applicable) or another person who can answer questions about processing. Include it in every response to a rights communication. A consent request must also carry this contact.
- **source:** Act s.8(9); s.6(3); Rules r.9.
- **applies_from:** 13 May 2027
- **detection:** automated. Crawl footer and privacy/notice pages for a named role or contact (email, phone, form). Assisted for the "every response" part (check auto-reply templates).
- **pass_criteria:** A contact for data questions is visible from the home page or app settings in at most two clicks; consent screens link to it.
- **exemptions_or_caveats:** DPO is mandatory only for notified Significant Data Fiduciaries (s.10(2)(a)); everyone else needs only a responsible person. "Prominently" is a judgment word.
- **confidence:** high.

### IN-DPDP-009
- **obligation (LAW):** Publish the means for principals to request access, correction, completion, updating, erasure and nomination, and the identifier or particulars needed to authenticate the request.
- **source:** Act ss.11, 12, 14; Rules r.14(1), r.14(4).
- **applies_from:** 13 May 2027
- **detection:** automated for presence (a rights page, form, or in-app control), assisted for coverage of each right.
- **pass_criteria:** A published route exists for each right; the page states what identifier is needed.
- **exemptions_or_caveats:** s.11 and s.5 can be disapplied for classes notified under s.17(3) (none found). Access under s.11 must list the other fiduciaries and processors the data was shared with, so keep a recipient inventory (see 017).
- **confidence:** medium.

### IN-DPDP-010
- **obligation (LAW):** Provide a grievance redressal mechanism, published on the website or app, with a response period not exceeding 90 days, backed by technical and organisational measures.
- **source:** Act s.8(10); s.13; Rules r.14(3).
- **applies_from:** 13 May 2027
- **detection:** automated for a published grievance route; human-judgment for the stated response period.
- **pass_criteria:** A grievance route is published and states a response time of 90 days or less.
- **exemptions_or_caveats:** PIB's backgrounder (P4) says 90 days applies to all rights requests; the Rules text I read applies the 90-day cap to grievances only (Q7). The Act requires the principal to use this route before approaching the Board (s.13(3)).
- **confidence:** medium.

---

## Group 3: Children

### IN-DPDP-011
- **obligation (LAW):** Before processing any personal data of a child (under 18) or of a person with disability who has a lawful guardian, obtain verifiable consent of the parent or guardian. The fiduciary exercises due diligence that the parent is an identifiable adult, by reference to identity and age details it already holds reliably, or details voluntarily provided directly or via a virtual token from an authorised entity (including a Digital Locker service provider).
- **source:** Act s.2(f), s.9(1); Rules r.10, r.11, r.12; Fourth Schedule.
- **applies_from:** 13 May 2027
- **detection:** assisted. Grep signup code for date-of-birth or age fields and "I am over 18" toggles; look for a parental-consent branch; flag any child-directed category (education, games, kids) by manifest or content signals; human decides whether children are likely users.
- **pass_criteria:** Where children may use the service: an age signal exists before data collection; a parental consent step with adult verification (Rule 10 routes) is triggered for under-18s; no account is created or data stored before that step completes.
- **exemptions_or_caveats:** The Fourth Schedule exempts certain classes (clinical establishments, health professionals, educational institutions for limited tracking, child-transport for location) and certain purposes (e.g. email-only account creation, real-time safety location, age-confirmation processing) from s.9(1) and s.9(3) only. s.9(2) is not exempted. No age-based exemption under s.9(5) was found. The Oct 2026 Removal of Difficulties Order reportedly adds "of" in s.9(1) (P8, unverified).
- **confidence:** medium for locating age signals; low for deciding sufficiency of verification.

### IN-DPDP-012
- **obligation (LAW):** Do not track or behaviourally monitor children, or run targeted advertising directed at children. Do not process in a way likely to harm a child's well-being.
- **source:** Act s.9(3); s.9(2); Rules r.12 and Fourth Schedule (exemptions to s.9(3) only).
- **applies_from:** 13 May 2027
- **detection:** automated partial. For flows where a child is identified (or the product is child-directed), capture network traffic and flag ad SDKs, ad-network domains, cross-site identifiers and behavioural analytics. Human-judgment for s.9(2) and for deciding whether the product is "directed at" children.
- **pass_criteria:** In child contexts, no ad-network or behavioural-tracking calls fire; analytics, if any, is aggregate and justified as non-monitoring.
- **exemptions_or_caveats:** "Tracking", "behavioural monitoring" and "targeted advertising directed at children" are not defined in the Act or the Rules I read. Whether crash reporting or aggregate analytics count is open (Q5). Penalty for s.9 breaches is up to INR 200 crore (Act Schedule).
- **confidence:** low-medium.

---

## Group 4: Security, breach, retention

### IN-DPDP-013
- **obligation (LAW):** Take reasonable security safeguards to prevent personal data breach. At minimum: encryption, obfuscation, masking or virtual tokens; access control; logs and monitoring of access to personal data; continuity measures such as backups; retention of such logs and personal data for one year (unless another law requires otherwise); security terms in processor contracts; and appropriate technical and organisational measures.
- **source:** Act s.8(5); Rules r.6(1)(a)-(g); r.8(3) (one-year retention for Seventh Schedule purposes).
- **applies_from:** 13 May 2027
- **detection:** automated partial; assisted. Scan code and config: HTTPS-only and HSTS; TLS config; database or volume encryption flags in IaC; secrets committed to the repo; password hashing; sensitive fields in plaintext logs; auth on admin routes; public cloud buckets; logging enabled; log retention setting at least 365 days; backup config.
- **pass_criteria (BEST PRACTICE thresholds):** Rule 6 gives no numeric standard besides the one-year log retention. The check passes if each Rule 6(1) item has an evidenced control. Treat TLS version, algorithms and hashing parameters as engineering defaults, not legal minimums.
- **exemptions_or_caveats:** s.8(5) applies even where other chapters are disapplied under s.17(1). The maximum penalty is INR 250 crore. Tension between one-year retention and erasure is unresolved (Q6). CERT-In asks for 180-day logs in India (see IN-CERTIN-001).
- **confidence:** medium. The categories are explicit; sufficiency ("reasonable") is not.

### IN-DPDP-014
- **obligation (LAW):** Use a processor only under a valid contract; the fiduciary stays responsible for processing done on its behalf; the contract includes appropriate security safeguards.
- **source:** Act s.8(1), s.8(2); Rules r.6(1)(f).
- **applies_from:** 13 May 2027
- **detection:** assisted. Enumerate third-party services that process personal data on the app's behalf (cloud, email, payments, support, analytics, error tracking) from dependency manifests and network traffic, then ask for evidence of a contract for each.
- **pass_criteria:** Every enumerated processor has a recorded contract with security terms.
- **exemptions_or_caveats:** The Act does not prescribe contract contents beyond safeguards. Whether a given vendor is a processor or an independent fiduciary is a legal characterisation.
- **confidence:** medium for the enumeration; low for the contract question (human evidence).

### IN-DPDP-015
- **obligation (LAW):** On a personal data breach, intimate (a) each affected principal, without delay, through her user account or registered contact, with a description, consequences, mitigation, safety steps and a contact; and (b) the Board, without delay with an initial description and within 72 hours (or a longer period the Board allows) with detailed information.
- **source:** Act s.8(6); Rules r.7(1), r.7(2).
- **applies_from:** 13 May 2027
- **detection:** human-judgment, with a presence check. Look for an incident response plan, a breach-notification template, and a way to message affected users (stored verified contact or in-app message).
- **pass_criteria:** A documented runbook with a user-notice template and a Board-notice template; ability to target affected users.
- **exemptions_or_caveats:** "Personal data breach" in s.2(u) has no materiality threshold. Penalty up to INR 200 crore for failing to notify (Act Schedule). No Board portal or form was located (the form and manner are prescribed by the Rules above).
- **confidence:** medium. The law is clear; compliance is an organisational capability, not a code property.

### IN-DPDP-016
- **obligation (LAW):** Erase personal data when consent is withdrawn or when it is reasonable to assume the purpose is no longer served, unless law requires retention. For specified classes, the purpose is deemed no longer served after a stated period of inactivity (three years for e-commerce with at least 2 crore registered users, online gaming intermediaries with at least 50 lakh, social media intermediaries with at least 2 crore), with notice at least 48 hours before erasure. Separately, such fiduciaries must retain the data, traffic data and logs for at least one year for Seventh Schedule purposes.
- **source:** Act s.8(7)-(8), s.12(3); Rules r.8(1)-(3); Third Schedule; Seventh Schedule.
- **applies_from:** 13 May 2027
- **detection:** assisted. Find account-deletion flows, deletion endpoints and TTL/retention jobs; check that deletion also reaches backups, analytics and processors; for large-scale classes, look for a 48-hour pre-erasure notification job.
- **pass_criteria:** A working deletion path exists that cascades to processors; documented retention periods per data type; for Third Schedule classes, an inactivity-based erasure job with advance notice.
- **exemptions_or_caveats:** The one-year retention in r.8(3) can sit awkwardly with deletion (Q6). The user-count thresholds mean most small apps are outside the Third Schedule.
- **confidence:** medium-low.

---

## Group 5: Third parties and transfers

### IN-DPDP-017
- **obligation (mixed):** The law has no rule specific to analytics, fonts, CDNs, embeds or ad calls. What it does say: the notice must itemise the data and purposes (s.5); consent must be specific (s.6(1)); the fiduciary is responsible for processors (s.8(1)-(2)); principals can ask for the identities of all other fiduciaries and processors with whom their data was shared (s.11(1)(b)). The checks below combine LAW and BEST PRACTICE.
- **source:** Act ss.2(t), 2(x), 4, 5, 6(1), 8(1)-(2), 11(1)(b).
- **applies_from:** 13 May 2027
- **detection:** automated. Headless crawl of key pages and flows: list every third-party domain contacted, what is sent (IP is implicit; look for identifiers, email hashes, user IDs in URLs and bodies), whether the request fires before any consent interaction, and the destination country (DNS/IP geolocation).
- **pass_criteria:**
  1. **LAW-derived:** every third party that receives personal data is listed in a recipient inventory and covered by the notice (data and purpose).
  2. **BEST PRACTICE, not a legal requirement:** non-essential trackers (ads, behavioural analytics) do not fire before the person acts on the consent control; static assets (fonts, CDNs) are self-hosted where practicable to avoid sending visitor IPs.
- **exemptions_or_caveats:** Whether a visitor IP address is "personal data" in this context, and whether a request to a font or CDN provider is a "disclosure" or "sharing", is unresolved (Q2). The Act contains no cookie rule. The skill should **report an inventory, not a violation**, for third-party calls.
- **confidence:** low as a legal check; high as an inventory tool.

### IN-DPDP-018
- **obligation (LAW):** Transfers abroad are permitted by default; the Government can restrict transfer for processing to specific countries by notification (s.16(1)). A stricter sectoral law still applies (s.16(2)). Significant Data Fiduciaries may be required to keep specified data and its traffic data in India (r.13(4)). Rule 15 conditions transfers on meeting requirements the Government may specify by order for making data available to a foreign State or its controlled entities.
- **source:** Act s.16; Rules r.13(4), r.13(5), r.15.
- **applies_from:** 13 May 2027
- **detection:** automated inventory. Resolve hosting regions and third-party endpoints to countries; compare with a maintained list of restricted countries, loaded from config.
- **pass_criteria:** No data flows to a country on the notified list. The list is currently **empty**: no s.16 notification, no r.15 order, no r.13(4) specification was found as of Oct 2026 (secondary sources; official gazette not searched).
- **exemptions_or_caveats:** s.16 is skipped where s.17(1) applies (e.g. processing of non-Indian residents' data under a foreign contract, s.17(1)(d)). Re-check the Gazette before every release of the skill.
- **confidence:** high that no country is currently restricted (as reported); low that the check protects anyone yet.

### IN-DPDP-019 (conditional)
- **obligation (LAW):** If notified as a Significant Data Fiduciary: appoint an India-based DPO answerable to the board; appoint an independent data auditor; run periodic DPIA and audits (at least every 12 months under r.13(1)); report to the Board; check algorithmic software for risk to principals; observe localisation specified under r.13(4).
- **source:** Act s.10; Rules r.13.
- **applies_from:** 13 May 2027 (and only if notified)
- **detection:** human-judgment. Ask whether the organisation has been notified; if yes, check for the artefacts.
- **pass_criteria:** Not applicable unless notified; no notification was found.
- **exemptions_or_caveats:** s.10(2)(c)(ii) is reportedly reworded to "data audit" by the Oct 2026 Order (P8, unverified). s.17(3) allows exemption of s.10 for classes (none found).
- **confidence:** low as a check; the skill should present it as informational.

---

## Group 6: Related Indian regimes (see overlaps.md)

### IN-SPDI-001
- **obligation (LAW):** A body corporate handling personal information or sensitive personal data must publish a privacy policy covering practices, data types, purpose, disclosure and security; and designate a Grievance Officer with name and contact published on its website, redressing grievances within one month.
- **source:** SPDI Rules r.4, r.5(9) (P5, via mirror).
- **applies_from:** In force now; ceases to be the primary regime when s.44(2) commences on 13 May 2027 (subject to Q8).
- **detection:** automated. Find a privacy policy link; find a named Grievance Officer and contact; check policy sections against r.4(i)-(v).
- **pass_criteria:** A published policy with the five elements; a named officer with contact details.
- **exemptions_or_caveats:** Applies to "body corporate" and, for consent and disclosure rules, to sensitive data only. A 2011 press note clarifying electronic consent is not verified.
- **confidence:** high on the text; medium on continuing force after 13 May 2027.

### IN-SPDI-002
- **obligation (LAW):** For sensitive personal data (passwords, financial instruments, health, sexual orientation, medical records, biometrics): collect only with written consent (letter, fax or email) stating purpose; only for a lawful purpose and where necessary; tell the person about collection, purpose, recipients and the collecting and retaining agency; allow refusal and withdrawal in writing; do not keep longer than needed; disclose to third parties only with prior permission unless agreed in contract or required by law; transfer abroad only to a body that ensures the same level of protection and only if necessary for the contract or with consent; maintain reasonable security (ISO 27001 as one recognised standard).
- **source:** SPDI Rules r.3, r.5(1)-(7), r.6, r.7, r.8.
- **applies_from:** In force now (Phase A/B).
- **detection:** assisted. Identify SPDI fields in forms and DB schemas; check for a consent step and a withdrawal route; list third-party recipients.
- **pass_criteria:** For every SPDI field: consent step present; stated purpose; withdrawal path; recipients disclosed.
- **exemptions_or_caveats:** Information in the public domain or furnished under RTI is not SPDI. Rule 8's safe harbour needs independent certification and audit at least yearly (r.8(4)).
- **confidence:** medium.

### IN-CERTIN-001
- **obligation (reported):** Synchronise ICT clocks with NIC or NPL NTP servers (or servers traceable to them); enable logs of all ICT systems and keep them securely for a rolling 180 days within Indian jurisdiction, ready to give to CERT-In.
- **source:** CERT-In Directions of 28 Apr 2022, No. 20(3)/2022-CERT-In (P9, **NOT OPENED**; summarised consistently by several law firms).
- **applies_from:** In force (effective 27 Jun 2022 per secondary sources; MSME extension reported)
- **detection:** assisted. Inspect server/IaC config for NTP sources; log retention settings; log storage region.
- **pass_criteria:** NTP source is NIC/NPL or traceable; log retention at least 180 days; logs stored in India.
- **exemptions_or_caveats:** Whether "within Indian jurisdiction" requires India-hosted storage is contested (Q18).
- **confidence:** low-medium. Primary text unread.

### IN-CERTIN-002
- **obligation (reported):** Report listed cyber incidents to CERT-In within 6 hours of noticing them (including unauthorised access to IT systems or data), and designate a point of contact.
- **source:** CERT-In Directions (P9, NOT OPENED). Report channel (email, phone) reported in a government-portal extract.
- **applies_from:** In force.
- **detection:** human-judgment. Check for an incident response plan with a 6-hour CERT-In step and a named contact.
- **pass_criteria:** Written plan; named contact; contact route saved.
- **exemptions_or_caveats:** Different clock from DPDP (72 hours to the Board). Both can apply to one event.
- **confidence:** medium on the duty (many consistent secondary summaries); low on exact wording.

### IN-ECOM-001 (conditional: e-commerce entities)
- **obligation (reported):** Display the grievance officer's name, contact and designation on the platform; acknowledge complaints within 48 hours and resolve within one month; record purchase consent only through explicit affirmative action, never pre-ticked boxes.
- **source:** Consumer Protection (E-Commerce) Rules, 2020, r.4(4), r.4(5), r.4(9) (P11, text seen via mirrors; official PDF NOT OPENED).
- **applies_from:** In force since 23 Jul 2020.
- **detection:** automated for pre-ticked purchase consent and grievance officer details; human for the response times.
- **pass_criteria:** No pre-ticked consent in checkout; grievance officer details visible.
- **exemptions_or_caveats:** Applies to "e-commerce entities" as defined in the Consumer Protection Act, 2019; not to occasional personal sellers.
- **confidence:** medium.

### IN-RBI-001 (conditional: payment system providers)
- **obligation (reported):** Entities authorised by RBI to operate payment systems must store the entire payment system data only in systems in India; if processed abroad, delete it abroad and bring it back within one business day or 24 hours, whichever is earlier.
- **source:** RBI circular DPSS.CO.OD.No.2785/06.08.005/2017-18 dated 6 Apr 2018, as summarised in the RBI FAQ (P6, extract only).
- **applies_from:** In force.
- **detection:** human-judgment. Applicable only if the app is itself an RBI-authorised payment system provider. For ordinary merchant apps, check whether the payment gateway is such a provider.
- **pass_criteria:** Not testable from outside.
- **exemptions_or_caveats:** Does not bind every app that accepts payments. Other RBI directions (digital lending, outsourcing) were not examined.
- **confidence:** low as an automated check; high that it exists.

---

## Summary of confidence

**Five I am most confident about**
1. **IN-DPDP-008**: contact for data questions. Explicit text (s.8(9), r.9), objective to crawl.
2. **IN-DPDP-002**: notice carries link and routes for withdrawal, rights, complaint. Three enumerated items in r.3(c).
3. **IN-DPDP-004**: no pre-ticked or bundled consent. Core of s.6(1), and pre-ticked boxes are detectable.
4. **IN-SPDI-001**: privacy policy and named grievance officer. Explicit text; objective check (but see Q8 on duration).
5. **IN-DPDP-018**: transfers allowed unless a country is notified. Clear in s.16; list currently empty (as reported).

**Five I am least confident about**
1. **IN-DPDP-017**: third-party calls and pre-consent trackers. The law is silent; IP-as-personal-data is unresolved.
2. **IN-DPDP-012**: child tracking and ads. Key terms undefined.
3. **IN-DPDP-011**: sufficiency of verifiable parental consent for small developers.
4. **IN-DPDP-003**: language option. Ambiguous pass criterion.
5. **IN-CERTIN-001**: primary text unread; "within Indian jurisdiction" unsettled.
