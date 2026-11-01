#!/usr/bin/env python3
"""
Privacy Preflight - Web Crawler and Consent Analyzer (Task 5b)

Behaves like a normal visitor crawling same-origin pages in breadth-first order.
Intercepts and aborts all external network requests (zero third-party contact).
Detects consent controls, extracts link graphs, and produces findings for
IN-BP-004, IN-BP-001, IN-DPDP-004, and IN-BP-002.

Not legal advice.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import time
import urllib.parse
import urllib.robotparser
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from playwright.sync_api import Browser, Page, Request, Route, sync_playwright
except ImportError:
    sync_playwright = None

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

STATIC_ASSET_TYPES = {"stylesheet", "script", "font", "image", "media"}
STATIC_ASSET_EXTS = {".css", ".js", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico"}
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Group 1: Explicit allowlist of known static asset CDN / font host domains (or domain suffixes)
SELF_HOSTABLE_STATIC_HOSTS = {
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "cdnjs.cloudflare.com",
    "cdn.jsdelivr.net",
    "unpkg.com",
    "stackpath.bootstrapcdn.com",
    "maxcdn.bootstrapcdn.com",
}


def is_self_hostable_cdn(domain: str) -> bool:
    """Check if domain matches the explicit static asset CDN / font provider allowlist."""
    d = domain.lower().split(":")[0]
    for allowed in SELF_HOSTABLE_STATIC_HOSTS:
        if d == allowed or d.endswith("." + allowed):
            return True
    return False


def is_local_host(hostname: str) -> bool:
    """Determine if a hostname is local or a test fixture."""
    clean_host = hostname.lower().split(":")[0]
    if clean_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    if clean_host.endswith(".test") or clean_host.endswith(".local") or clean_host.endswith(".internal"):
        return True
    return False


def is_same_origin(url: str, start_origin: str) -> bool:
    """Check if target URL shares the exact origin (scheme + host + port) of start_origin."""
    parsed = urllib.parse.urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return origin.lower() == start_origin.lower()


def normalize_url(url: str) -> str:
    """Normalize URL by stripping fragments and resolving relative dots."""
    defragged, _ = urllib.parse.urldefrag(url)
    parsed = urllib.parse.urlparse(defragged)
    path = parsed.path or "/"
    normalized = urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        path,
        parsed.params,
        parsed.query,
        ""
    ))
    return normalized


def extract_consent_controls_js() -> str:
    """JavaScript expression to extract consent controls and classify purposes."""
    return """
    () => {
        const consentKeywords = [
            'consent', 'agree', 'marketing', 'analytics', 'newsletter',
            'personalis', 'terms', 'privacy'
        ];
        const results = [];
        const selector = 'input[type="checkbox"], input[type="radio"], [role="switch"], [role="checkbox"]';
        const elements = Array.from(document.querySelectorAll(selector));

        elements.forEach((el, index) => {
            let controlType = 'checkbox';
            if (el.getAttribute('role') === 'switch') {
                controlType = 'switch';
            } else if (el.type === 'radio') {
                controlType = 'radio';
            }

            let checked = false;
            if (el.tagName === 'INPUT') {
                checked = el.checked;
            } else {
                checked = el.getAttribute('aria-checked') === 'true';
            }

            let labelText = '';
            // 1. Explicit <label for="...">
            if (el.id) {
                const labelEl = document.querySelector(`label[for="${el.id}"]`);
                if (labelEl) {
                    labelText = labelEl.innerText.trim();
                }
            }

            // 2. Wrapping label
            if (!labelText) {
                const parentLabel = el.closest('label');
                if (parentLabel) {
                    labelText = parentLabel.innerText.trim();
                }
            }

            // 3. aria-label or aria-labelledby
            if (!labelText && el.getAttribute('aria-label')) {
                labelText = el.getAttribute('aria-label').trim();
            }
            if (!labelText && el.getAttribute('aria-labelledby')) {
                const labelledBy = document.getElementById(el.getAttribute('aria-labelledby'));
                if (labelledBy) {
                    labelText = labelledBy.innerText.trim();
                }
            }

            // 4. Surrounding parent text container
            if (!labelText) {
                const parentContainer = el.closest('.form-group, .consent-item, .checkbox-group, div, p');
                if (parentContainer) {
                    labelText = parentContainer.innerText.trim();
                }
            }

            const lowerLabel = labelText.toLowerCase();
            const isNearConsent = consentKeywords.some(kw => lowerLabel.includes(kw));
            if (!isNearConsent) {
                return;
            }

            // Classify distinct purposes
            const purposes = [];
            if (lowerLabel.includes('marketing') || lowerLabel.includes('promotion') || lowerLabel.includes('newsletter') || lowerLabel.includes('advertis')) {
                purposes.push('marketing');
            }
            if (lowerLabel.includes('analytic') || lowerLabel.includes('measurement') || lowerLabel.includes('usage data') || lowerLabel.includes('track')) {
                purposes.push('analytics');
            }
            if (lowerLabel.includes('personalis') || lowerLabel.includes('customiz') || lowerLabel.includes('tailor')) {
                purposes.push('personalisation');
            }
            if (lowerLabel.includes('third party') || lowerLabel.includes('third-party') || lowerLabel.includes('partner') || lowerLabel.includes('sharing')) {
                purposes.push('third-party sharing');
            }

            const controlId = el.id || el.getAttribute('name') || `control-${index}`;

            results.push({
                control_id: controlId,
                control_type: controlType,
                checked: Boolean(checked),
                label: labelText,
                purposes: purposes,
                is_pre_checked: Boolean(checked),
                is_bundled: purposes.length >= 2
            });
        });

        return results;
    }
    """


def extract_contact_signals(page: Page, visible_text: str) -> bool:
    """
    A page shows contact details only if its visible text contains an email address
    OR it has an a[href^="mailto:"] or a[href^="tel:"] link.
    The bare word 'contact' never counts.
    """
    if EMAIL_REGEX.search(visible_text):
        return True

    try:
        has_contact_link = page.evaluate("""() => {
            const link = document.querySelector('a[href^="mailto:" i], a[href^="tel:" i]');
            return Boolean(link);
        }""")
        if has_contact_link:
            return True
    except Exception:
        pass

    return False


def crawl_site(
    start_url: str,
    max_pages: int = 30,
    max_depth: int = 4,
) -> Dict[str, Any]:
    """
    Crawl same-origin pages starting from start_url.
    Intercepts and aborts external network requests.
    Returns structured crawl artifact matching references/crawl-schema.md.
    """
    if sync_playwright is None:
        raise RuntimeError("Playwright is not installed. Run 'pip install playwright && playwright install chromium'")

    normalized_start = normalize_url(start_url)
    parsed_start = urllib.parse.urlparse(normalized_start)
    start_origin = f"{parsed_start.scheme}://{parsed_start.netloc}".lower()
    is_local = is_local_host(parsed_start.netloc)

    # Initialize robot parser for non-local hosts
    robot_parser = None
    if not is_local:
        try:
            robot_parser = urllib.robotparser.RobotFileParser()
            robot_parser.set_url(f"{start_origin}/robots.txt")
            robot_parser.read()
        except Exception:
            robot_parser = None

    crawled_pages: List[Dict[str, Any]] = []
    external_requests: List[Dict[str, Any]] = []
    pages_skipped = 0
    pages_failed = 0
    visited_urls: Set[str] = {normalized_start}
    queue: deque[Tuple[str, int]] = deque([(normalized_start, 0)])

    current_crawling_url = normalized_start
    last_request_time = 0.0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Intercept and abort external requests
        def handle_route(route: Route):
            nonlocal external_requests
            req = route.request
            req_url = req.url
            parsed_req = urllib.parse.urlparse(req_url)
            req_origin = f"{parsed_req.scheme}://{parsed_req.netloc}".lower()

            if req_origin == start_origin:
                route.continue_()
            else:
                domain = parsed_req.netloc.split(":")[0]
                record = {
                    "url": req_url,
                    "domain": domain,
                    "resource_type": req.resource_type,
                    "page_url": current_crawling_url,
                    "fired_on_load": True,
                    "country": "not resolved",
                    "aborted": True,
                }
                external_requests.append(record)
                route.abort()

        context.route("**/*", handle_route)

        while queue and len(crawled_pages) < max_pages:
            url, depth = queue.popleft()
            current_crawling_url = url

            # Rate limit non-local hosts
            if not is_local:
                elapsed = time.time() - last_request_time
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)
                last_request_time = time.time()

                if robot_parser and not robot_parser.can_fetch("*", url):
                    pages_skipped += 1
                    continue

            status_code = 200
            failed = False
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                if response:
                    status_code = response.status
                    if status_code >= 400:
                        failed = True
            except Exception:
                status_code = 500
                failed = True

            if failed:
                pages_failed += 1

            title = ""
            visible_text = ""
            same_origin_links: List[Dict[str, str]] = []
            consent_controls: List[Dict[str, Any]] = []
            has_contact = False

            if status_code != 404:
                try:
                    title = page.title()
                except Exception:
                    title = ""

                try:
                    visible_text = page.locator("body").inner_text()
                except Exception:
                    visible_text = ""

                has_contact = extract_contact_signals(page, visible_text)

                # Extract consent controls
                try:
                    raw_controls = page.evaluate(extract_consent_controls_js())
                    if isinstance(raw_controls, list):
                        consent_controls = raw_controls
                except Exception:
                    consent_controls = []

                # Extract links
                try:
                    a_elements = page.query_selector_all("a[href]")
                    for a in a_elements:
                        raw_href = a.get_attribute("href")
                        if not raw_href or raw_href.startswith(("javascript:", "mailto:", "tel:", "#")):
                            continue
                        resolved = urllib.parse.urljoin(url, raw_href)
                        clean_href = normalize_url(resolved)
                        anchor_text = a.inner_text().strip()

                        if is_same_origin(clean_href, start_origin):
                            same_origin_links.append({"href": clean_href, "text": anchor_text})
                            if clean_href not in visited_urls and depth + 1 <= max_depth:
                                visited_urls.add(clean_href)
                                queue.append((clean_href, depth + 1))
                except Exception:
                    pass

            crawled_pages.append({
                "url": url,
                "depth": depth,
                "status": status_code,
                "title": title,
                "text": visible_text,
                "has_contact_details": has_contact,
                "links": same_origin_links,
                "consent_controls": consent_controls,
            })

        browser.close()

    # Build summary
    unique_domains = sorted(list({r["domain"] for r in external_requests}))
    pre_checked_count = sum(
        1 for p in crawled_pages for c in p.get("consent_controls", []) if c.get("is_pre_checked")
    )
    bundled_count = sum(
        1 for p in crawled_pages for c in p.get("consent_controls", []) if c.get("is_bundled")
    )

    contact_pages: List[Dict[str, Any]] = []
    min_contact_depth: Optional[int] = None
    for p in crawled_pages:
        if p.get("has_contact_details"):
            contact_pages.append({"url": p["url"], "depth": p["depth"]})
            if min_contact_depth is None or p["depth"] < min_contact_depth:
                min_contact_depth = p["depth"]

    # Remove internal has_contact_details before serializing
    for p in crawled_pages:
        p.pop("has_contact_details", None)

    max_depth_reached = max((p["depth"] for p in crawled_pages), default=0)
    interactions_str = "none (no clicks except same-origin links, no forms submitted, no login)"

    crawl_artifact = {
        "metadata": {
            "start_url": normalized_start,
            "crawled_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "max_pages": max_pages,
            "max_depth": max_depth,
            "pages_crawled": len(crawled_pages),
            "max_depth_reached": max_depth_reached,
            "pages_skipped": pages_skipped,
            "pages_failed": pages_failed,
            "interactions": interactions_str,
            "total_pages_crawled": len(crawled_pages),
            "total_external_requests": len(external_requests),
        },
        "pages": crawled_pages,
        "external_requests": external_requests,
        "summary": {
            "external_domains": unique_domains,
            "pre_checked_controls_count": pre_checked_count,
            "bundled_controls_count": bundled_count,
            "min_contact_depth": min_contact_depth,
            "contact_pages": contact_pages,
            "pages_crawled": len(crawled_pages),
            "max_depth_reached": max_depth_reached,
            "pages_skipped": pages_skipped,
            "pages_failed": pages_failed,
            "interactions": interactions_str,
        },
    }
    return crawl_artifact


def generate_findings(crawl_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate findings compliant with references/findings-schema.md
    for exactly: IN-BP-004, IN-BP-001, IN-DPDP-004, IN-BP-002.
    Returns a dictionary with 'scan' coverage metadata and 'findings' list.
    """
    meta = crawl_data.get("metadata", {})
    pages_crawled = meta.get("pages_crawled", len(crawl_data.get("pages", [])))
    max_depth_reached = meta.get("max_depth_reached", 0)
    pages_skipped = meta.get("pages_skipped", 0)
    pages_failed = meta.get("pages_failed", 0)
    interactions = meta.get(
        "interactions", "none (no clicks except same-origin links, no forms submitted, no login)"
    )
    coverage_suffix = (
        f" (pages crawled: {pages_crawled}, "
        f"max depth reached: {max_depth_reached}, "
        f"pages skipped: {pages_skipped}, "
        f"pages failed: {pages_failed}, "
        f"interactions: {interactions})"
    )

    external_reqs = crawl_data.get("external_requests", [])
    pages = crawl_data.get("pages", [])
    summary = crawl_data.get("summary", {})

    findings: List[Dict[str, Any]] = []

    # 1. IN-BP-004: Third-party recipient inventory
    # Result: informational. Evidence: one line per external domain ("domain (country: not resolved, fired on load: yes/no)"). Notes: "legal status unclear".
    domain_fired_map: Dict[str, bool] = {}
    for r in external_reqs:
        d = r["domain"]
        domain_fired_map[d] = domain_fired_map.get(d, False) or r.get("fired_on_load", False)

    if domain_fired_map:
        bp_004_evidence = [
            f"{domain} (country: not resolved, fired on load: {'yes' if fired else 'no'})"
            for domain, fired in sorted(domain_fired_map.items())
        ]
    else:
        bp_004_evidence = ["(empty inventory)"]

    findings.append({
        "check_id": "IN-BP-004",
        "result": "informational",
        "evidence": bp_004_evidence,
        "notes": f"legal status unclear{coverage_suffix}",
    })

    # 2. IN-BP-001: Self-host static assets
    # Met if no external static assets, otherwise informational (never not-met), with recommendation to self-host.
    external_static_reqs = [
        r for r in external_reqs
        if r.get("resource_type") in STATIC_ASSET_TYPES
        or any(urllib.parse.urlparse(r.get("url", "")).path.lower().endswith(ext) for ext in STATIC_ASSET_EXTS)
    ]

    group1_reqs = []
    group2_reqs = []
    for r in external_static_reqs:
        rtype = r.get("resource_type", "")
        url_path = urllib.parse.urlparse(r.get("url", "")).path.lower()
        is_stylesheet_or_font = (
            rtype in ("stylesheet", "font")
            or any(url_path.endswith(ext) for ext in [".css", ".woff", ".woff2", ".ttf", ".eot", ".otf"])
        )
        if is_stylesheet_or_font or is_self_hostable_cdn(r.get("domain", "")):
            group1_reqs.append(r)
        else:
            group2_reqs.append(r)

    if group1_reqs or group2_reqs:
        bp_001_evidence_set = set()
        for r in group1_reqs:
            bp_001_evidence_set.add(f"{r['domain']} ({r['resource_type']}): {r['url']}")
        for r in group2_reqs:
            bp_001_evidence_set.add(f"{r['domain']} ({r['resource_type']} loaded from provider): {r['url']}")
        bp_001_evidence = sorted(list(bp_001_evidence_set))

        group1_hosts = sorted(list({r["domain"] for r in group1_reqs}))
        finding: Dict[str, Any] = {
            "check_id": "IN-BP-001",
            "result": "informational",
            "evidence": bp_001_evidence,
            "confidence": "medium",
        }
        if group1_hosts:
            finding["suggested_fix"] = (
                f"Self-host these static assets to avoid sending visitor IP addresses to their hosts: {', '.join(group1_hosts)}"
            )

        if group1_reqs and not group2_reqs:
            finding["notes"] = f"External static assets detected. Recommendation: self-host static assets.{coverage_suffix}"
        elif group2_reqs and not group1_reqs:
            finding["notes"] = f"Scripts from third-party providers are listed for the inventory; whether they can be self-hosted depends on the provider. No self-hosting advice given.{coverage_suffix}"
        else:
            finding["notes"] = (
                f"External static assets detected. Recommendation: self-host static assets. "
                f"Scripts from third-party providers are listed for the inventory; "
                f"whether they can be self-hosted depends on the provider. No self-hosting advice given.{coverage_suffix}"
            )
        findings.append(finding)
    else:
        findings.append({
            "check_id": "IN-BP-001",
            "result": "met",
            "evidence": ["All static assets are self-hosted; zero external static asset requests detected."],
            "notes": f"Self-hosted static assets baseline satisfied.{coverage_suffix}",
        })

    # 3. IN-DPDP-004: Consent controls (unbundled and no pre-ticked controls)
    # Met if no pre-checked or bundled consent controls, not-met if any (evidence URL and label text), unclear if no consent controls found.
    all_controls: List[Tuple[str, Dict[str, Any]]] = []
    for p in pages:
        p_url = p["url"]
        for c in p.get("consent_controls", []):
            all_controls.append((p_url, c))

    violating_controls = [
        (url, c) for url, c in all_controls
        if c.get("is_pre_checked") or c.get("is_bundled")
    ]

    if violating_controls:
        dpdp_004_evidence = [
            f"{url}: [pre-checked: {c.get('is_pre_checked')}, bundled: {c.get('is_bundled')}] label: \"{c.get('label')}\""
            for url, c in violating_controls
        ]
        findings.append({
            "check_id": "IN-DPDP-004",
            "result": "not-met",
            "evidence": dpdp_004_evidence,
            "suggested_fix": "Uncheck default consent checkboxes and provide separate toggles per distinct purpose.",
            "notes": f"Detected pre-checked or bundled consent controls.{coverage_suffix}",
        })
    elif all_controls:
        dpdp_004_evidence = [
            f"{url}: [unchecked, unbundled] label: \"{c.get('label')}\""
            for url, c in all_controls
        ]
        findings.append({
            "check_id": "IN-DPDP-004",
            "result": "met",
            "evidence": dpdp_004_evidence,
            "notes": f"All consent controls are unbundled and unchecked by default.{coverage_suffix}",
        })
    else:
        findings.append({
            "check_id": "IN-DPDP-004",
            "result": "unclear",
            "evidence": ["No consent controls detected across crawled pages."],
            "notes": f"No consent controls found to evaluate.{coverage_suffix}",
        })

    # 4. IN-BP-002: Contact details accessible within two clicks
    # Measure click depth from start page to any page whose text contains contact details (email or mailto/tel),
    # met if depth <= 2, not-met if > 2, unclear if no such page is reachable.
    min_contact_depth = summary.get("min_contact_depth")
    contact_pages = summary.get("contact_pages", [])

    if min_contact_depth is not None:
        matched_pages = [p for p in contact_pages if p["depth"] == min_contact_depth]
        bp_002_evidence = [f"{p['url']} (depth: {p['depth']})" for p in matched_pages]

        if min_contact_depth <= 2:
            click_word = "click" if min_contact_depth == 1 else "clicks"
            findings.append({
                "check_id": "IN-BP-002",
                "result": "met",
                "evidence": bp_002_evidence,
                "notes": f"Contact details reachable within {min_contact_depth} {click_word} from start page.{coverage_suffix}",
            })
        else:
            findings.append({
                "check_id": "IN-BP-002",
                "result": "not-met",
                "evidence": bp_002_evidence,
                "suggested_fix": "Ensure contact details are reachable within at most 2 clicks from the landing screen.",
                "notes": f"Contact details reachable at depth {min_contact_depth}, exceeding recommended 2-click threshold.{coverage_suffix}",
            })
    else:
        findings.append({
            "check_id": "IN-BP-002",
            "result": "unclear",
            "evidence": ["No page containing contact details was reachable within crawl depth limit."],
            "suggested_fix": "Publish contact details prominently on the landing screen or within 2 clicks.",
            "notes": f"No contact details page reached.{coverage_suffix}",
        })

    return {
        "scan": {
            "pages_crawled": pages_crawled,
            "max_depth_reached": max_depth_reached,
            "pages_skipped": pages_skipped,
            "pages_failed": pages_failed,
            "interactions": interactions,
        },
        "findings": findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Privacy Preflight - Web Crawler and Consent Analyzer")
    parser.add_argument("--url", required=True, help="Root URL to start crawling")
    parser.add_argument("--max-pages", type=int, default=30, help="Maximum number of pages to crawl (default: 30)")
    parser.add_argument("--max-depth", type=int, default=4, help="Maximum click depth from start URL (default: 4)")
    parser.add_argument(
        "--out",
        default="reports/crawl.json",
        help="Path to write raw crawl JSON artifact (default: reports/crawl.json)",
    )
    parser.add_argument(
        "--findings-out",
        default="reports/findings.json",
        help="Path to write findings JSON artifact (default: reports/findings.json)",
    )

    args = parser.parse_args()

    crawl_result = crawl_site(
        start_url=args.url,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(crawl_result, f, indent=2)
        print(f"Crawl artifact written to {out_path}")

    if args.findings_out:
        findings_doc = generate_findings(crawl_result)
        findings_path = Path(args.findings_out)
        findings_path.parent.mkdir(parents=True, exist_ok=True)
        with findings_path.open("w", encoding="utf-8") as f:
            json.dump(findings_doc, f, indent=2)
        print(f"Findings artifact written to {findings_path}")

    if not args.out and not args.findings_out:
        print(json.dumps(crawl_result["summary"], indent=2))


if __name__ == "__main__":
    main()
