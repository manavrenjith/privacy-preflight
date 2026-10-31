# Crawl Output Schema Specification

> **Engineering specification. Not legal advice.**
> This document specifies the JSON document format produced by `scripts/crawl.py` via the `--out <path>` CLI option.

---

## 1. Overview

The crawler produces a structured JSON artifact summarizing application pages, same-origin link graphs, form consent controls, and intercepted/aborted third-party network requests.

---

## 2. Format Structure

The crawl output document is a JSON object with top-level keys:
- `metadata`: Execution parameters and run statistics.
- `pages`: Array of crawled page objects with same-origin links and consent controls.
- `external_requests`: Array of intercepted and aborted external network calls.
- `summary`: Aggregate metrics including external domains, consent flags, and contact depth.

### Field Definitions

#### `metadata` Object
| Field | Type | Description |
|---|---|---|
| `start_url` | string | The initial root URL provided to the crawler. |
| `crawled_at` | string | ISO 8601 UTC timestamp of crawler execution. |
| `max_pages` | integer | Configured page limit. |
| `max_depth` | integer | Configured maximum click depth. |
| `pages_crawled` | integer | Total pages successfully crawled. |
| `max_depth_reached` | integer | Maximum click depth reached during crawl. |
| `pages_skipped` | integer | Total pages skipped (e.g. rate limit, robots.txt). |
| `pages_failed` | integer | Total pages with HTTP errors or load failures. |
| `interactions` | string | Description of crawler interaction boundaries (`"none (no clicks except same-origin links, no forms submitted, no login)"`). |
| `total_pages_crawled` | integer | Actual number of distinct pages crawled. |
| `total_external_requests` | integer | Number of intercepted external requests. |

#### `pages[]` Object
| Field | Type | Description |
|---|---|---|
| `url` | string | Canonical URL of the page. |
| `depth` | integer | Click distance from the start URL (start page has depth 0). |
| `status` | integer | HTTP response status code (e.g. 200, 404). 404s are recorded, not fatal errors. |
| `title` | string | The `<title>` content of the document. |
| `text` | string | Visible body text extracted from the page. |
| `links` | array | Array of same-origin links discovered on the page (`[{"href": "...", "text": "..."}]`). |
| `consent_controls` | array | Array of consent controls detected on the page (see below). |

#### `consent_controls[]` Object
| Field | Type | Description |
|---|---|---|
| `control_id` | string / null | Element ID, name, or generated identifier. |
| `control_type` | string | Form control type (`checkbox`, `radio`, `switch`). |
| `checked` | boolean | Current checked state on page load. |
| `label` | string | Extracted text of the associated label or container. |
| `purposes` | array of strings | Distinct processing purposes detected in label (`marketing`, `analytics`, `personalisation`, `third-party sharing`). |
| `is_pre_checked` | boolean | True if the control is checked/on on page load. |
| `is_bundled` | boolean | True if a single control names two or more distinct processing purposes. |

#### `external_requests[]` Object
| Field | Type | Description |
|---|---|---|
| `url` | string | Full URL of the external request. |
| `domain` | string | Extracted external hostname/domain. |
| `resource_type` | string | Playwright resource type (`stylesheet`, `script`, `font`, `image`, `fetch`, etc.). |
| `page_url` | string | The page URL on which the request was initiated. |
| `fired_on_load` | boolean | True if the request fired on page load before any click or user interaction. |
| `country` | string | Country code or resolution status (`"not resolved"`). |
| `aborted` | boolean | Always `true`. The crawler aborts all external network requests to prevent external communication. |

#### `summary` Object
| Field | Type | Description |
|---|---|---|
| `external_domains` | array of strings | Unique list of all external hostnames intercepted. |
| `pre_checked_controls_count` | integer | Count of pre-checked consent controls. |
| `bundled_controls_count` | integer | Count of bundled multi-purpose consent controls. |
| `min_contact_depth` | integer / null | Minimum click depth to reach a page containing contact details. |
| `contact_pages` | array | List of pages containing contact details (`[{"url": "...", "depth": N}]`). |
| `pages_crawled` | integer | Total pages crawled. |
| `max_depth_reached` | integer | Maximum depth reached. |
| `pages_skipped` | integer | Total pages skipped. |
| `pages_failed` | integer | Total pages failed. |
| `interactions` | string | Description of scanner interaction boundaries. |

---

## 3. Machine-Readable Schema (JSON Schema Draft-07)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PrivacyPreflightCrawl",
  "type": "object",
  "required": ["metadata", "pages", "external_requests", "summary"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["start_url", "crawled_at", "max_pages", "max_depth", "total_pages_crawled", "total_external_requests"],
      "properties": {
        "start_url": { "type": "string" },
        "crawled_at": { "type": "string" },
        "max_pages": { "type": "integer", "minimum": 1 },
        "max_depth": { "type": "integer", "minimum": 0 },
        "pages_crawled": { "type": "integer", "minimum": 0 },
        "max_depth_reached": { "type": "integer", "minimum": 0 },
        "pages_skipped": { "type": "integer", "minimum": 0 },
        "pages_failed": { "type": "integer", "minimum": 0 },
        "interactions": { "type": "string" },
        "total_pages_crawled": { "type": "integer", "minimum": 0 },
        "total_external_requests": { "type": "integer", "minimum": 0 }
      }
    },
    "pages": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["url", "depth", "status", "title", "text", "links", "consent_controls"],
        "properties": {
          "url": { "type": "string" },
          "depth": { "type": "integer", "minimum": 0 },
          "status": { "type": "integer" },
          "title": { "type": "string" },
          "text": { "type": "string" },
          "links": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["href", "text"],
              "properties": {
                "href": { "type": "string" },
                "text": { "type": "string" }
              }
            }
          },
          "consent_controls": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["control_id", "control_type", "checked", "label", "purposes", "is_pre_checked", "is_bundled"],
              "properties": {
                "control_id": { "type": ["string", "null"] },
                "control_type": { "type": "string", "enum": ["checkbox", "radio", "switch"] },
                "checked": { "type": "boolean" },
                "label": { "type": "string" },
                "purposes": {
                  "type": "array",
                  "items": { "type": "string" }
                },
                "is_pre_checked": { "type": "boolean" },
                "is_bundled": { "type": "boolean" }
              }
            }
          }
        }
      }
    },
    "external_requests": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["url", "domain", "resource_type", "page_url", "fired_on_load", "country", "aborted"],
        "properties": {
          "url": { "type": "string" },
          "domain": { "type": "string" },
          "resource_type": { "type": "string" },
          "page_url": { "type": "string" },
          "fired_on_load": { "type": "boolean" },
          "country": { "type": "string" },
          "aborted": { "type": "boolean" }
        }
      }
    },
    "summary": {
      "type": "object",
      "required": ["external_domains", "pre_checked_controls_count", "bundled_controls_count", "min_contact_depth", "contact_pages"],
      "properties": {
        "external_domains": {
          "type": "array",
          "items": { "type": "string" }
        },
        "pre_checked_controls_count": { "type": "integer", "minimum": 0 },
        "bundled_controls_count": { "type": "integer", "minimum": 0 },
        "min_contact_depth": { "type": ["integer", "null"] },
        "contact_pages": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["url", "depth"],
            "properties": {
              "url": { "type": "string" },
              "depth": { "type": "integer" }
            }
          }
        }
      }
    }
  }
}
```

