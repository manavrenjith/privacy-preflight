#!/usr/bin/env python3
"""
Privacy Preflight - Page Content Analyzer (Task 6)

Analyzes page text, links, headings, and consent controls from a crawl.json artifact
to evaluate compliance with statutory page requirements under Indian privacy law:
- IN-DPDP-002: Notice linked from consent requests with withdrawal, rights, and Board complaint.
- IN-DPDP-008: Direct contact details or named role on consent request pages.
- IN-DPDP-009: Dedicated rights mechanism covering all 4 rights with authentication.
- IN-DPDP-010: Grievance redressal mechanism with stated response timeline.
- IN-SPDI-001: Privacy policy covering 5 Rule 4 elements with named Grievance Officer.

Page Kind Assignment:
- A page may hold several kinds simultaneously (set of kinds). For example, a single page
  combining notice and privacy policy will have both 'notice' and 'privacy policy' kinds.
- A page is assigned kind:
  * 'notice': if filename, title, or inbound link anchor text contains 'notice'.
  * 'rights': if filename, title, or inbound link anchor text contains 'rights'.
  * 'grievance': if filename, title, or inbound link anchor text contains 'grievance' or 'redress'.
  * 'privacy policy': if filename contains 'privacy' or title/inbound link anchor text contains 'privacy policy'.
  * 'contact': if filename, title, or inbound link anchor text contains 'contact'.

Status Decision Table:
-----------------------------------------------------------------------------------------------------------------------
Check ID     | Condition                                                              | Result   | Notes
-----------------------------------------------------------------------------------------------------------------------
IN-DPDP-002  | Notice page found; consent page links to it; mentions withdraw,        | met      | Notice satisfies all
             | rights, board complaint; contains contact channel or link to it        |          | statutory requirements
IN-DPDP-002  | Notice page found; 1 or 2 of the 3 conditions satisfied                | unclear  | Missing specific elements
IN-DPDP-002  | Notice page found; 0 of the 3 conditions satisfied                     | not-met  | None of elements found
IN-DPDP-002  | Notice page not found, crawl complete                                  | not-met  | Not found among crawled pages
IN-DPDP-002  | Notice page not found, crawl incomplete/truncated                      | unclear  | Incomplete crawl
-----------------------------------------------------------------------------------------------------------------------
IN-DPDP-008  | All consent pages contain or directly link to contact details/role    | met      | Covers consent pages only
IN-DPDP-008  | Any consent page lacks contact details and direct link to one          | not-met  | Covers consent pages only
IN-DPDP-008  | No consent pages exist in the crawled app                              | unclear  | No consent pages found
-----------------------------------------------------------------------------------------------------------------------
IN-DPDP-009  | Rights page found; covers access, correction, erasure, nomination,     | met      | Pass threshold: 5/5 groups
             | and authentication                                                     |          |
IN-DPDP-009  | Rights page found; 1 to 4 groups present                               | unclear  | Lists missing groups
IN-DPDP-009  | Rights page found; 0 of the 5 groups present                            | not-met  | None of groups found
IN-DPDP-009  | Rights page not found, crawl complete                                  | not-met  | Not found among crawled pages
IN-DPDP-009  | Rights page not found, crawl incomplete/truncated                      | unclear  | Incomplete crawl
-----------------------------------------------------------------------------------------------------------------------
IN-DPDP-010  | Grievance page found with stated response timeline                     | met      | States dual-clock note;
             |                                                                        |          | notes if > 1 month
IN-DPDP-010  | Grievance page found without stated timeline in context window         | unclear  | Route exists, timeline missing
IN-DPDP-010  | Grievance page not found, crawl complete                               | not-met  | Not found among crawled pages
IN-DPDP-010  | Grievance page not found, crawl incomplete/truncated                   | unclear  | Incomplete crawl
-----------------------------------------------------------------------------------------------------------------------
IN-SPDI-001  | Privacy policy found; covers practices, data types, purpose,           | met      | 5/5 elements + named officer
             | disclosure, security; and named Grievance Officer with email/phone     |          |
IN-SPDI-001  | Privacy policy found; some elements present or officer lacks name      | unclear  | Lists missing elements/officer
IN-SPDI-001  | Privacy policy found; 0 elements and no officer found                  | not-met  | None of elements found
IN-SPDI-001  | Privacy policy not found, crawl complete                               | not-met  | Not found among crawled pages
IN-SPDI-001  | Privacy policy not found, crawl incomplete/truncated                   | unclear  | Incomplete crawl
-----------------------------------------------------------------------------------------------------------------------

Not legal advice. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

# Regular expressions
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# Phone regex: matches standard Indian (+91 optional, 10 digits starting 6-9) or North American / intl format
PHONE_REGEX = re.compile(
    r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}\b|(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)

ROLE_NAMES_PATTERN = re.compile(
    r"\b(?:data\s+protection\s+officer|dpo|grievance\s+officer|authorized\s+contact(?:\s+person)?)\b",
    re.IGNORECASE,
)

REJECTED_NAME_PLACEHOLDERS = {
    "tbd",
    "tba",
    "n/a",
    "na",
    "none",
    "nil",
    "xxx",
    "name",
    "your name",
    "to be announced",
    "fictional",
    "placeholder",
    "test",
}

# DPDP-002 topics
WITHDRAW_REGEX = re.compile(r"\bwithdraw(?:al)?\b", re.IGNORECASE)
RIGHTS_REGEX = re.compile(r"\brights?\b", re.IGNORECASE)
BOARD_COMPLAINT_REGEX = re.compile(
    r"(?i)(?:\bcomplaint\b[^\n.?!]{0,100}\bboard\b|\bboard\b[^\n.?!]{0,100}\bcomplaint\b)"
)

# DPDP-009 5 statutory rights groups
RIGHTS_GROUPS = {
    "access": re.compile(r"\baccess\b", re.IGNORECASE),
    "correction": re.compile(r"\bcorrect(?:ion)?\b|\bupdat(?:e|ion)\b", re.IGNORECASE),
    "erasure": re.compile(r"\beras(?:e|ure)\b|\bdelet(?:e|ion)\b", re.IGNORECASE),
    "nomination": re.compile(r"\bnominat(?:e|ion)\b", re.IGNORECASE),
    "authentication": re.compile(
        r"\b(?:identit(?:y|ies)|verif(?:y|ication)|authenticat(?:e|ion)?|proof)\b",
        re.IGNORECASE,
    ),
}

# DPDP-010 Timeline within context window of request/respond/within/grievance/rights
TIMELINE_WINDOW_REGEX = re.compile(
    r"(?i)(?:\b(?:request|respond(?:ed|ing)?|response|within|grievance|rights?)\b[^\n.?!]{0,100}?"
    r"\b(\d+\s+(?:working\s+)?days?|one\s+month|\d+\s+months?|\d+\s+weeks?)\b"
    r"|\b(\d+\s+(?:working\s+)?days?|one\s+month|\d+\s+months?|\d+\s+weeks?)\b[^\n.?!]{0,100}?"
    r"\b(?:request|respond(?:ed|ing)?|response|within|grievance|rights?)\b)"
)

# SPDI-001 Heading pattern: checks if a line looks like a heading
HEADING_LINE_REGEX = re.compile(r"^\s*(?:[#=]{1,6}\s*|\d+[\.\)]\s*)?([^\n]{3,90})$")


def get_url_path(url: str) -> str:
    """Extract path from URL, defaulting to '/' if empty."""
    p = urllib.parse.urlparse(url).path
    return p if p else "/"


def normalize_path(path: str) -> str:
    """Normalize path by stripping trailing slashes except for root."""
    if not path or path == "/":
        return "/"
    p = path.rstrip("/")
    return p if p else "/"


def normalize_url_for_depth_check(url: str) -> str:
    """Remove #fragment and trailing slash for depth link comparison."""
    defragged, _ = urllib.parse.urldefrag(url)
    if defragged.endswith("/"):
        defragged = defragged[:-1]
    return defragged


def is_same_origin_link(link_url: str, base_url: str) -> bool:
    """Check if link_url has the same origin (scheme and netloc) as base_url."""
    p_link = urllib.parse.urlparse(link_url)
    p_base = urllib.parse.urlparse(base_url)
    if p_link.scheme in ("mailto", "tel", "javascript"):
        return False
    if not p_link.netloc and not p_base.netloc:
        return True
    return (
        p_link.scheme.lower() == p_base.scheme.lower()
        and p_link.netloc.lower() == p_base.netloc.lower()
    )


def strip_copyright_lines(text: str) -> str:
    """Strip lines containing copyright notices and 'all rights reserved'."""
    clean_lines = []
    for line in text.splitlines():
        ll = line.lower()
        if "all rights reserved" in ll or "copyright" in ll or "©" in line or "&copy;" in ll:
            continue
        clean_lines.append(line)
    return "\n".join(clean_lines)


def classify_page_kinds(pages: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """
    Classify page kinds for every page in crawl.
    A page can belong to multiple kinds simultaneously.
    Matching is case-insensitive on URL path filename, title, or inbound link text.
    """
    page_kinds: Dict[str, Set[str]] = {p["url"]: set() for p in pages}

    # Inbound link texts map: target_url -> set of anchor texts
    inbound_links: Dict[str, Set[str]] = {p["url"]: set() for p in pages}
    for src_page in pages:
        for link in src_page.get("links", []):
            target = link.get("href")
            txt = link.get("text", "")
            if target in inbound_links:
                inbound_links[target].add(txt.lower())

    for p in pages:
        url = p["url"]
        path = get_url_path(url).lower()
        filename = Path(path).name.lower()
        title = (p.get("title") or "").lower()
        anchors = " ".join(inbound_links.get(url, set()))
        search_blob = f"{filename} {title} {anchors}"

        # notice
        if "notice" in search_blob:
            page_kinds[url].add("notice")

        # rights
        if "rights" in search_blob:
            page_kinds[url].add("rights")

        # grievance
        if "grievance" in search_blob or "redress" in search_blob:
            page_kinds[url].add("grievance")

        # privacy policy: filename contains 'privacy' or blob contains 'privacy policy'
        if "privacy" in filename or "privacy policy" in title or "privacy policy" in anchors:
            page_kinds[url].add("privacy policy")

        # contact
        if "contact" in filename or "contact" in title or "contact" in anchors:
            page_kinds[url].add("contact")

    return page_kinds


def check_r4_elements(text: str) -> Tuple[Dict[str, bool], List[str]]:
    """
    Check the five Rule 4 elements in a privacy policy page:
    1. practices
    2. data types
    3. purpose
    4. disclosure
    5. security
    Checks headings first; falls back to body text only with nearby context verbs/phrases.
    Bare words like 'policy', 'purpose', or 'security' alone do not satisfy an element.
    """
    lines = text.splitlines()
    heading_candidates = [
        line.strip() for line in lines if len(line.strip()) < 90 and len(line.strip()) > 3
    ]

    elements_found = {
        "practices": False,
        "data_types": False,
        "purpose": False,
        "disclosure": False,
        "security": False,
    }

    # 1. Short lines check (elements matched on short lines of page text, not HTML headings)
    for h in heading_candidates:
        hl = h.lower()
        if not elements_found["practices"]:
            if re.search(r"\bpractic(?:e|es)\b", hl):
                elements_found["practices"] = True

        if not elements_found["data_types"]:
            if (
                re.search(r"\b(?:types?|categories|kinds?)\s+of\s+(?:personal\s+)?(?:data|information)\b", hl)
                or "information we collect" in hl
                or "what is collected" in hl
                or "data we collect" in hl
            ):
                elements_found["data_types"] = True

        if not elements_found["purpose"]:
            if (
                re.search(r"\bpurpose(?:s)?\s+of\s+(?:collection|usage|processing)\b", hl)
                or "collection and usage" in hl
                or "why we collect" in hl
                or re.search(r"\bpurpose\b.{1,30}\b(?:collection|usage|processing)\b", hl)
                or re.search(r"\bhow\s+we\s+use\b.*?\b(?:information|data|your)\b", hl)
            ):
                elements_found["purpose"] = True

        if not elements_found["disclosure"]:
            if (
                re.search(r"\bdisclos(?:e|ure|ures)\b", hl)
                or "third-party" in hl
                or "third party" in hl
                or re.search(r"\bsharing\s+(?:of\s+)?(?:personal\s+)?(?:data|information)\b", hl)
                or re.search(r"\btransfer\s+of\s+(?:personal\s+)?(?:data|information)\b", hl)
            ):
                elements_found["disclosure"] = True

        if not elements_found["security"]:
            if (
                re.search(r"\b(?:reasonable\s+)?security\s+practices(?:\s+and\s+procedures)?\b", hl)
                or "security practices" in hl
                or "security safeguards" in hl
                or "data security" in hl
            ):
                elements_found["security"] = True

    # 2. Body fallback with context phrases (not bare words)
    if not elements_found["practices"]:
        if re.search(
            r"(?i)\b(?:adopt|follow|maintain|publish|outline)s?\s+(?:our\s+|the\s+)?practic(?:e|es)\b|\bdata\s+handling\s+practic(?:e|es)\b",
            text,
        ):
            elements_found["practices"] = True

    if not elements_found["data_types"]:
        if re.search(
            r"(?i)\bcollect(?:s|ed|ing)?\s+(?:the\s+following\s+)?(?:categories|types|kinds)\s+of\s+(?:personal\s+)?(?:data|information)\b",
            text,
        ):
            elements_found["data_types"] = True

    if not elements_found["purpose"]:
        if re.search(
            r"(?i)\b(?:collected|used|processed)\s+(?:only\s+|exclusively\s+)?for\s+(?:the\s+)?purposes?\s+of\b|\bpurposes?\s+for\s+which\b",
            text,
        ):
            elements_found["purpose"] = True

    if not elements_found["disclosure"]:
        if re.search(
            r"(?i)\b(?:disclos(?:e|ed|ing|ure)|share|transfer)(?:s)?\s+(?:personal\s+)?(?:data|information)\s+to\b|\bdisclosure\s+(?:to|of)\b",
            text,
        ):
            elements_found["disclosure"] = True

    if not elements_found["security"]:
        if re.search(
            r"(?i)\b(?:implement|maintain)s?\s+(?:reasonable\s+)?security\s+(?:measures|practices|controls|procedures)\b",
            text,
        ):
            elements_found["security"] = True

    missing = [elem for elem, found in elements_found.items() if not found]
    return elements_found, missing


def extract_named_grievance_officer(text: str) -> Optional[Tuple[str, str]]:
    """
    Extract named Grievance Officer and contact details.
    Requires:
    1. Words 'Grievance Officer' followed within the same sentence/line by:
       - An explicit 'Name:' label (e.g. 'Name: Alex Sharma') OR
       - A case-sensitive capitalized personal-name pattern (e.g. 'Jane Doe').
       Role titles alone (e.g. 'Grievance Officer (Fictional Role)', 'Grievance Redressal Officer')
       do NOT count as a personal name.
    2. Contact details (email or phone) on the page.
    Returns (officer_name, contact_info) if found, else None.
    """
    lines = text.splitlines()
    officer_name: Optional[str] = None

    DISALLOWED_NAME_WORDS = {
        "designated", "grievance", "officer", "redressal", "data", "protection",
        "dpo", "authorized", "contact", "person", "fictional", "role", "title",
        "official", "mr", "ms", "dr"
    }

    for line in lines:
        if "grievance officer" in line.lower():
            # 1. Check for explicit "Name:" label
            m_label = re.search(r"(?i)\bname\s*:\s*([^,\n.?!]+)", line)
            if m_label:
                candidate = m_label.group(1).strip().strip("-–—:()[]")
                candidate_lower = candidate.lower()
                letters_only = re.sub(r"[^A-Za-z]", "", candidate)
                if len(letters_only) >= 3 and candidate_lower not in REJECTED_NAME_PLACEHOLDERS:
                    words = [w.lower() for w in re.findall(r"[A-Za-z]+", candidate)]
                    if words and any(
                        w not in DISALLOWED_NAME_WORDS and w not in REJECTED_NAME_PLACEHOLDERS
                        for w in words
                    ):
                        officer_name = candidate
                        break

            # 2. Check for personal name after "Grievance Officer" or colon
            parts = re.split(r"(?i)\bgrievance\s+officer\b", line, maxsplit=1)
            after_text = parts[1] if len(parts) > 1 else line

            cap_matches = re.finditer(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", after_text)
            for m in cap_matches:
                candidate = m.group(0).strip().strip("-–—:()[]")
                candidate_lower = candidate.lower()
                letters_only = re.sub(r"[^A-Za-z]", "", candidate)
                if len(letters_only) >= 3 and candidate_lower not in REJECTED_NAME_PLACEHOLDERS:
                    words = [w.lower() for w in candidate.split()]
                    if all(
                        w not in DISALLOWED_NAME_WORDS and w not in REJECTED_NAME_PLACEHOLDERS
                        for w in words
                    ):
                        officer_name = candidate
                        break
            if officer_name:
                break

    if not officer_name:
        return None

    # Check for contact details on the page
    email_match = EMAIL_REGEX.search(text)
    phone_match = PHONE_REGEX.search(text)
    contact_str = ""
    if email_match:
        contact_str = email_match.group(0)
    elif phone_match:
        contact_str = phone_match.group(0)

    if not contact_str:
        return None

    return officer_name, contact_str


def is_timeline_greater_than_one_month(timeline_str: str) -> bool:
    """Check if a stated timeline strictly exceeds one month (30 days)."""
    tl = timeline_str.lower()
    m_days = re.search(r"(\d+)\s+(?:working\s+)?days?", tl)
    if m_days:
        return int(m_days.group(1)) > 30

    m_months = re.search(r"(\d+)\s+months?", tl)
    if m_months:
        return int(m_months.group(1)) > 1

    m_weeks = re.search(r"(\d+)\s+weeks?", tl)
    if m_weeks:
        return int(m_weeks.group(1)) > 4

    return False


def evaluate_pages(crawl_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate pages from a crawl.json artifact for:
    IN-DPDP-002, IN-DPDP-008, IN-DPDP-009, IN-DPDP-010, IN-SPDI-001.
    Returns findings compliant with references/findings-schema.md.
    """
    metadata = crawl_data.get("metadata", {})
    pages = crawl_data.get("pages", [])

    pages_crawled = metadata.get("pages_crawled", len(pages))
    max_depth_reached = metadata.get("max_depth_reached", 0)
    pages_skipped = metadata.get("pages_skipped", 0)
    pages_failed = metadata.get("pages_failed", 0)
    interactions = metadata.get(
        "interactions", "none (no clicks except same-origin links, no forms submitted, no login)"
    )
    max_pages = metadata.get("max_pages")
    max_depth = metadata.get("max_depth")

    has_uncrawled_depth_links = False
    if max_depth is not None:
        crawled_urls = {
            normalize_url_for_depth_check(p.get("url", ""))
            for p in pages
            if p.get("url")
        }
        for p in pages:
            if p.get("depth", 0) >= max_depth:
                p_url = p.get("url", "")
                for link in p.get("links", []):
                    raw_href = link.get("href", "")
                    if not raw_href:
                        continue
                    resolved = urllib.parse.urljoin(p_url, raw_href) if p_url else raw_href
                    if not is_same_origin_link(resolved, p_url):
                        continue
                    norm_link = normalize_url_for_depth_check(resolved)
                    if norm_link not in crawled_urls:
                        has_uncrawled_depth_links = True
                        break
                if has_uncrawled_depth_links:
                    break

    # Incomplete crawl flag: failed pages, skipped pages, page limit, or uncrawled links at depth limit
    is_incomplete_crawl = (
        (pages_failed > 0)
        or (pages_skipped > 0)
        or (max_pages is not None and pages_crawled >= max_pages)
        or has_uncrawled_depth_links
    )
    incomplete_crawl_note = (
        "the crawl may not have reached every page "
        "(links beyond the depth limit, skipped or failed pages, or the page limit)"
    )

    scan_obj = {
        "pages_crawled": pages_crawled,
        "max_depth_reached": max_depth_reached,
        "pages_skipped": pages_skipped,
        "pages_failed": pages_failed,
        "interactions": interactions,
    }

    page_kinds = classify_page_kinds(pages)
    pages_by_url = {p["url"]: p for p in pages}
    pages_by_norm_path: Dict[str, List[Dict[str, Any]]] = {}
    for p in pages:
        norm_p = normalize_path(get_url_path(p["url"]))
        pages_by_norm_path.setdefault(norm_p, []).append(p)

    privacy_pages = [p for p in pages if "privacy policy" in page_kinds[p["url"]]]

    findings: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # 1. IN-DPDP-002: Notice linked from consent requests with withdrawal, rights, complaints
    # -------------------------------------------------------------------------
    notice_pages = [p for p in pages if "notice" in page_kinds[p["url"]]]
    consent_pages = [p for p in pages if len(p.get("consent_controls", [])) > 0]

    if not notice_pages:
        if is_incomplete_crawl:
            findings.append({
                "check_id": "IN-DPDP-002",
                "result": "unclear",
                "evidence": ["not found among crawled pages (crawl incomplete)"],
                "notes": f"Notice page not found among crawled pages; {incomplete_crawl_note}. (pages crawled: {pages_crawled})",
            })
        elif privacy_pages:
            fb_page = privacy_pages[0]
            fb_path = get_url_path(fb_page["url"])
            fb_text = strip_copyright_lines(fb_page.get("text", ""))
            fb_short_lines = [
                line.strip() for line in fb_text.splitlines()
                if 4 <= len(line.strip()) <= 89
            ]
            has_notice_heading = any(
                re.search(r"\b(?:rights?|withdraw(?:al)?)\b", line, re.IGNORECASE)
                for line in fb_short_lines
            )
            has_board = bool(BOARD_COMPLAINT_REGEX.search(fb_text))
            if has_notice_heading or has_board:
                matched_signals = []
                if has_notice_heading:
                    matched_signals.append("rights or withdrawal short lines")
                if has_board:
                    matched_signals.append("complaint to Board")
                findings.append({
                    "check_id": "IN-DPDP-002",
                    "result": "unclear",
                    "evidence": [f"{fb_path}: notice topics ({', '.join(matched_signals)}) detected in privacy policy content"],
                    "notes": f"Dedicated notice page not found; privacy policy was checked as fallback and matched notice topics. (pages crawled: {pages_crawled})",
                    "confidence": "medium",
                })
            else:
                findings.append({
                    "check_id": "IN-DPDP-002",
                    "result": "not-met",
                    "evidence": ["not found among the crawled pages"],
                    "suggested_fix": "Publish a dedicated data protection notice and link it directly from all consent request screens.",
                    "notes": f"Notice page not found among the crawled pages. The privacy policy page was also checked by keyword; no matching topics were found. (pages crawled: {pages_crawled})",
                    "confidence": "medium",
                })
        else:
            findings.append({
                "check_id": "IN-DPDP-002",
                "result": "not-met",
                "evidence": ["not found among the crawled pages"],
                "suggested_fix": "Publish a dedicated data protection notice and link it directly from all consent request screens.",
                "notes": f"Notice page not found among the crawled pages. Pages are classified by URL, title and link text; page content was not searched for pages that were not classified this way. (pages crawled: {pages_crawled})",
                "confidence": "medium",
            })
    else:
        # Check each notice page candidates
        best_result = "not-met"
        best_ev: List[str] = []
        best_notes = ""

        for n_page in notice_pages:
            n_path = get_url_path(n_page["url"])
            n_norm_path = normalize_path(n_path)
            n_text = n_page.get("text", "")

            # (a) linked from at least one consent page
            referring_consent_pages = sorted(list({
                get_url_path(cp["url"])
                for cp in consent_pages
                if any(normalize_path(get_url_path(link.get("href", ""))) == n_norm_path for link in cp.get("links", []))
            }))

            has_link_from_consent = len(referring_consent_pages) > 0

            # (b) notice text mentions withdraw, rights, board complaint
            has_withdraw = bool(WITHDRAW_REGEX.search(n_text))
            has_rights = bool(RIGHTS_REGEX.search(n_text))
            has_board = bool(BOARD_COMPLAINT_REGEX.search(n_text))
            has_topics = has_withdraw and has_rights and has_board

            # (c) notice text contains email/phone or links to contact/grievance
            has_email = bool(EMAIL_REGEX.search(n_text))
            has_phone = bool(PHONE_REGEX.search(n_text))
            links_to_contact_or_grievance = False
            for link in n_page.get("links", []):
                target_url = link.get("href", "")
                target_kinds = page_kinds.get(target_url, set())
                if "contact" in target_kinds or "grievance" in target_kinds:
                    links_to_contact_or_grievance = True
                    break

            has_contact_route = has_email or has_phone or links_to_contact_or_grievance

            conditions_met = sum([has_link_from_consent, has_topics, has_contact_route])

            if conditions_met == 3:
                best_result = "met"
                best_ev = [
                    f"{n_path}: linked from consent screen ({', '.join(referring_consent_pages)})",
                    f"{n_path}: describes withdrawal routes, data principal rights, and complaint to the Board",
                    f"{n_path}: provides communication link / contact route for inquiries",
                ]
                best_notes = f"Notice page satisfies linkage from consent request, statutory topics, and contact route. (pages crawled: {pages_crawled})"
                break
            elif conditions_met in (1, 2):
                if best_result != "met":
                    best_result = "unclear"
                    missing_parts = []
                    if not has_link_from_consent:
                        missing_parts.append("link from consent request screen")
                    if not has_topics:
                        missing_topics = []
                        if not has_withdraw:
                            missing_topics.append("withdrawal")
                        if not has_rights:
                            missing_topics.append("rights")
                        if not has_board:
                            missing_topics.append("complaint to Board")
                        missing_parts.append(f"notice topics ({', '.join(missing_topics)})")
                    if not has_contact_route:
                        missing_parts.append("contact route / communication link")

                    best_ev = [f"{n_path}: missing required notice elements ({'; '.join(missing_parts)})"]
                    best_notes = f"Notice page found but missing required statutory elements: {', '.join(missing_parts)}. (pages crawled: {pages_crawled})"
            else:
                if best_result == "not-met":
                    best_ev = [f"{n_path}: none of the 3 required notice elements were found"]
                    best_notes = f"Notice page found but none of the required elements were found. (pages crawled: {pages_crawled})"

        findings.append({
            "check_id": "IN-DPDP-002",
            "result": best_result,
            "evidence": best_ev,
            "notes": best_notes,
            **({"suggested_fix": "Ensure data protection notice describes withdrawal, rights, and Board complaints, is linked from consent screens, and includes contact details."} if best_result == "not-met" else {}),
        })

    # -------------------------------------------------------------------------
    # 2. IN-DPDP-008: Contact details for data inquiries in consent requests
    # -------------------------------------------------------------------------
    # Rule scopes strictly to consent pages. Notes explicitly state this narrowing.
    if not consent_pages:
        findings.append({
            "check_id": "IN-DPDP-008",
            "result": "unclear",
            "evidence": ["no consent controls detected across crawled pages"],
            "notes": f"No consent pages found among the crawled pages. (evaluation covers consent pages only, excluding general footer, notice or bare webforms) (pages crawled: {pages_crawled})",
        })
    else:
        passing_consent_ev: List[str] = []
        failing_consent_ev: List[str] = []

        for cp in consent_pages:
            cp_path = get_url_path(cp["url"])
            cp_text = cp.get("text", "")

            # Direct check in page text
            has_email = bool(EMAIL_REGEX.search(cp_text))
            has_phone = bool(PHONE_REGEX.search(cp_text))
            has_role = bool(ROLE_NAMES_PATTERN.search(cp_text))

            if has_email or has_phone or has_role:
                passing_consent_ev.append(f"{cp_path}: contains direct contact details or named role in page content")
                continue

            # Link check: links directly to a page whose text contains one
            linked_contact_found = False
            for link in cp.get("links", []):
                target_url = link.get("href", "")
                target_page = pages_by_url.get(target_url)
                if target_page:
                    t_text = target_page.get("text", "")
                    if EMAIL_REGEX.search(t_text) or PHONE_REGEX.search(t_text) or ROLE_NAMES_PATTERN.search(t_text):
                        linked_contact_found = True
                        target_path = get_url_path(target_url)
                        passing_consent_ev.append(f"{cp_path}: links directly to {target_path} containing contact details")
                        break

            if not linked_contact_found:
                failing_consent_ev.append(f"{cp_path}: contact details or direct contact link not found")

        if failing_consent_ev:
            findings.append({
                "check_id": "IN-DPDP-008",
                "result": "not-met",
                "evidence": failing_consent_ev,
                "suggested_fix": "Publish business contact details (email, phone, or named DPO/Grievance Officer) directly on consent request screens or link directly to them.",
                "notes": f"Contact details or direct link to contact details not found among the crawled pages for consent page(s). (evaluation covers consent pages only, excluding general footer, notice or bare webforms) (pages crawled: {pages_crawled})",
            })
        else:
            findings.append({
                "check_id": "IN-DPDP-008",
                "result": "met",
                "evidence": passing_consent_ev,
                "notes": f"All consent request pages publish or directly link to contact details. (evaluation covers consent pages only, excluding general footer, notice or bare webforms) (pages crawled: {pages_crawled})",
            })

    # -------------------------------------------------------------------------
    # 3. IN-DPDP-009: Mechanism for exercising data principal rights
    # -------------------------------------------------------------------------
    rights_pages = [p for p in pages if "rights" in page_kinds[p["url"]]]

    if not rights_pages:
        if is_incomplete_crawl:
            findings.append({
                "check_id": "IN-DPDP-009",
                "result": "unclear",
                "evidence": ["not found among crawled pages (crawl incomplete)"],
                "notes": f"Rights page not found among crawled pages; {incomplete_crawl_note}. (pages crawled: {pages_crawled})",
            })
        elif privacy_pages:
            fb_page = privacy_pages[0]
            fb_path = get_url_path(fb_page["url"])
            fb_text = strip_copyright_lines(fb_page.get("text", ""))
            fb_short_lines = [
                line.strip() for line in fb_text.splitlines()
                if 4 <= len(line.strip()) <= 89
            ]
            has_rights_heading = any(
                re.search(r"\brights?\b", line, re.IGNORECASE)
                for line in fb_short_lines
            )
            matched_groups = [
                g_name for g_name, g_regex in RIGHTS_GROUPS.items()
                if g_regex.search(fb_text)
            ]
            if has_rights_heading or len(matched_groups) >= 2:
                matched_desc = f"matched: {', '.join(matched_groups)}" if matched_groups else "rights heading"
                findings.append({
                    "check_id": "IN-DPDP-009",
                    "result": "unclear",
                    "evidence": [f"{fb_path}: data principal rights topics detected in privacy policy content ({matched_desc})"],
                    "notes": f"Dedicated rights page not found; privacy policy was checked as fallback and matched rights topics ({', '.join(matched_groups) if matched_groups else 'rights heading'}). (pages crawled: {pages_crawled})",
                    "confidence": "medium",
                })
            else:
                findings.append({
                    "check_id": "IN-DPDP-009",
                    "result": "not-met",
                    "evidence": ["not found among the crawled pages"],
                    "suggested_fix": "Provide a dedicated rights portal or page covering access, correction, erasure, and nomination with authentication requirements.",
                    "notes": f"Rights page not found among the crawled pages. The privacy policy page was also checked by keyword; no matching topics were found. (pages crawled: {pages_crawled})",
                    "confidence": "medium",
                })
        else:
            findings.append({
                "check_id": "IN-DPDP-009",
                "result": "not-met",
                "evidence": ["not found among the crawled pages"],
                "suggested_fix": "Provide a dedicated rights portal or page covering access, correction, erasure, and nomination with authentication requirements.",
                "notes": f"Rights page not found among the crawled pages. Pages are classified by URL, title and link text; page content was not searched for pages that were not classified this way. (pages crawled: {pages_crawled})",
                "confidence": "medium",
            })
    else:
        best_result = "not-met"
        best_ev: List[str] = []
        best_notes = ""

        for rp in rights_pages:
            rp_path = get_url_path(rp["url"])
            rp_text = rp.get("text", "")

            # Check 5 statutory groups
            matched_groups = []
            missing_groups = []
            for g_name, g_regex in RIGHTS_GROUPS.items():
                if g_regex.search(rp_text):
                    matched_groups.append(g_name)
                else:
                    missing_groups.append(g_name)

            if len(matched_groups) == 5:
                best_result = "met"
                best_ev = [
                    f"{rp_path}: covers statutory rights of access, correction, erasure, nomination, and authentication particulars"
                ]
                best_notes = f"Rights mechanism covers all four statutory rights (access, correction, erasure, nomination) with authentication particulars. (pass threshold: 5/5 groups present) (pages crawled: {pages_crawled})"
                break
            elif len(matched_groups) >= 1:
                if best_result != "met":
                    best_result = "unclear"
                    best_ev = [
                        f"{rp_path}: present: {', '.join(matched_groups)}; missing statutory groups: {', '.join(missing_groups)}"
                    ]
                    best_notes = f"Rights page found but missing required statutory rights groups: {', '.join(missing_groups)}. (pass threshold: 5/5 groups present) (pages crawled: {pages_crawled})"
            else:
                if best_result == "not-met":
                    best_ev = [f"{rp_path}: none of the 5 statutory rights groups were found"]
                    best_notes = f"Rights page found but none of the statutory rights groups were found. (pass threshold: 5/5 groups present) (pages crawled: {pages_crawled})"

        findings.append({
            "check_id": "IN-DPDP-009",
            "result": best_result,
            "evidence": best_ev,
            "notes": best_notes,
            **({"suggested_fix": "Ensure rights mechanism explicitly covers access, correction, erasure, and nomination with identity verification particulars."} if best_result == "not-met" else {}),
        })

    # -------------------------------------------------------------------------
    # 4. IN-DPDP-010: Grievance redressal mechanism and response timelines
    # -------------------------------------------------------------------------
    grievance_pages = [p for p in pages if "grievance" in page_kinds[p["url"]]]

    dual_clock_note = (
        "Dual clock: SPDI r.5(9) requires resolution within one month; "
        "DPDP r.14(3) sets a maximum period not exceeding ninety days (grievances only). "
        "Recommendation: adhere to the stricter one-month (30-day) clock while both regimes apply."
    )

    if not grievance_pages:
        if is_incomplete_crawl:
            findings.append({
                "check_id": "IN-DPDP-010",
                "result": "unclear",
                "evidence": ["not found among crawled pages (crawl incomplete)"],
                "notes": f"Grievance redressal page not found among crawled pages; {incomplete_crawl_note}. {dual_clock_note} (pages crawled: {pages_crawled})",
            })
        elif privacy_pages:
            fb_page = privacy_pages[0]
            fb_path = get_url_path(fb_page["url"])
            fb_text = strip_copyright_lines(fb_page.get("text", ""))
            has_grievance = ("grievance" in fb_text.lower() or "redress" in fb_text.lower())
            if has_grievance:
                findings.append({
                    "check_id": "IN-DPDP-010",
                    "result": "unclear",
                    "evidence": [f"{fb_path}: grievance/redressal keywords detected in privacy policy content"],
                    "notes": f"Dedicated grievance page not found; privacy policy was checked as fallback and mentions grievance or redressal topics. {dual_clock_note} (pages crawled: {pages_crawled})",
                    "confidence": "medium",
                })
            else:
                findings.append({
                    "check_id": "IN-DPDP-010",
                    "result": "not-met",
                    "evidence": ["not found among the crawled pages"],
                    "suggested_fix": "Publish an internal grievance redressal mechanism specifying a response timeline (stricter benchmark: one month).",
                    "notes": f"Grievance redressal page not found among the crawled pages. The privacy policy page was also checked by keyword; no matching topics were found. {dual_clock_note} (pages crawled: {pages_crawled})",
                    "confidence": "medium",
                })
        else:
            findings.append({
                "check_id": "IN-DPDP-010",
                "result": "not-met",
                "evidence": ["not found among the crawled pages"],
                "suggested_fix": "Publish an internal grievance redressal mechanism specifying a response timeline (stricter benchmark: one month).",
                "notes": f"Grievance redressal page not found among the crawled pages. Pages are classified by URL, title and link text; page content was not searched for pages that were not classified this way. {dual_clock_note} (pages crawled: {pages_crawled})",
                "confidence": "medium",
            })
    else:
        best_result = "unclear"
        best_ev: List[str] = []
        best_notes = ""

        for gp in grievance_pages:
            gp_path = get_url_path(gp["url"])
            gp_text = gp.get("text", "")

            # Look for stated timeline within ~100 chars of context keywords
            m_timeline = TIMELINE_WINDOW_REGEX.search(gp_text)
            if m_timeline:
                matched_tl = m_timeline.group(1) or m_timeline.group(2)
                best_result = "met"
                best_ev = [f"{gp_path}: published grievance redressal route with stated timeline '{matched_tl}'"]

                exceeds_note = ""
                if is_timeline_greater_than_one_month(matched_tl):
                    exceeds_note = f" Note: Stated response timeline ({matched_tl}) exceeds the SPDI r.5(9) one-month clock."

                best_notes = f"Grievance redressal route found with stated timeline '{matched_tl}'.{exceeds_note} {dual_clock_note} (pages crawled: {pages_crawled})"
                break
            else:
                best_ev = [f"{gp_path}: grievance route present but no stated response timeline found within context window"]
                best_notes = f"Grievance redressal route found but no stated timeline within context window. {dual_clock_note} (pages crawled: {pages_crawled})"

        findings.append({
            "check_id": "IN-DPDP-010",
            "result": best_result,
            "evidence": best_ev,
            "notes": best_notes,
        })

    # -------------------------------------------------------------------------
    # 5. IN-SPDI-001: Privacy policy publication and named Grievance Officer
    # -------------------------------------------------------------------------
    privacy_pages = [p for p in pages if "privacy policy" in page_kinds[p["url"]]]

    if not privacy_pages:
        if is_incomplete_crawl:
            findings.append({
                "check_id": "IN-SPDI-001",
                "result": "unclear",
                "evidence": ["not found among crawled pages (crawl incomplete)"],
                "notes": f"Privacy policy not found among crawled pages; {incomplete_crawl_note}. (pages crawled: {pages_crawled})",
            })
        else:
            findings.append({
                "check_id": "IN-SPDI-001",
                "result": "not-met",
                "evidence": ["not found among the crawled pages"],
                "suggested_fix": "Publish a privacy policy covering the five Rule 4 elements and designate a named Grievance Officer with working contact information.",
                "notes": f"Privacy policy not found among the crawled pages. Pages are classified by URL, title and link text; page content was not searched for pages that were not classified this way. (pages crawled: {pages_crawled})",
                "confidence": "medium",
            })
    else:
        best_result = "not-met"
        best_ev: List[str] = []
        best_notes = ""

        for pp in privacy_pages:
            pp_path = get_url_path(pp["url"])
            pp_text = pp.get("text", "")

            elements_found, missing_elems = check_r4_elements(pp_text)
            officer_info = extract_named_grievance_officer(pp_text)

            all_elems_present = len(missing_elems) == 0
            officer_present = officer_info is not None

            # Path-first evidence for elements and officer
            r4_order = ["practices", "data_types", "purpose", "disclosure", "security"]
            elem_status = [
                f"{e} (detected)" if elements_found[e] else f"{e} (not detected by keyword rules)"
                for e in r4_order
            ]
            elem_ev = f"{pp_path}: Rule 4 elements: {', '.join(elem_status)}"

            if officer_present:
                officer_ev = f"{pp_path}: designated Grievance Officer '{officer_info[0]}' with contact '{officer_info[1]}'"
            elif "grievance officer" in pp_text.lower():
                officer_ev = f"{pp_path}: Grievance Officer lacks explicit name or contact details (not detected by keyword rules)"
            else:
                officer_ev = f"{pp_path}: designated Grievance Officer (not detected by keyword rules)"

            if all_elems_present and officer_present:
                officer_name, officer_contact = officer_info
                best_result = "met"
                best_ev = [
                    f"{pp_path}: covers practices, data types, purpose, disclosure, and security",
                    officer_ev,
                ]
                best_notes = f"Privacy policy published covering all five Rule 4 elements with a designated named Grievance Officer and contact details. Elements checked by keyword presence signals; not a judgment of adequacy. (pages crawled: {pages_crawled})"
                break
            elif any(elements_found.values()) or "grievance officer" in pp_text.lower():
                if best_result != "met":
                    best_result = "unclear"
                    best_ev = [elem_ev, officer_ev]
                    best_notes = f"Privacy policy found; some elements or designated officer not detected by keyword rules. Elements checked by keyword presence signals; not a judgment of adequacy. (pages crawled: {pages_crawled})"
            else:
                if best_result == "not-met":
                    best_ev = [elem_ev, officer_ev]
                    best_notes = f"Privacy policy found but Rule 4 elements and designated officer not detected by keyword rules. Elements checked by keyword presence signals; not a judgment of adequacy. (pages crawled: {pages_crawled})"

        findings.append({
            "check_id": "IN-SPDI-001",
            "result": best_result,
            "evidence": best_ev,
            "notes": best_notes,
            **({"suggested_fix": "Publish a comprehensive privacy policy addressing Rule 4 elements and designate a named Grievance Officer with published email or phone."} if best_result == "not-met" else {}),
        })

    return {
        "scan": scan_obj,
        "findings": findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Privacy Preflight - Page Content Analyzer")
    parser.add_argument("crawl_json", help="Path to input crawl.json from crawl.py")
    parser.add_argument(
        "--findings-out",
        default="reports/pages-findings.json",
        help="Path to output findings JSON (default: reports/pages-findings.json)",
    )

    args = parser.parse_args()

    input_path = Path(args.crawl_json)
    if not input_path.is_file():
        sys.exit(f"Error: crawl file not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        crawl_data = json.load(f)

    result_doc = evaluate_pages(crawl_data)

    out_path = Path(args.findings_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result_doc, f, indent=2)

    print(f"Pages findings written to {out_path}")


if __name__ == "__main__":
    main()

