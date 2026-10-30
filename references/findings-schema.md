# Findings Input Schema Specification

> **Engineering specification. Not legal advice.**
> Input findings provide evidence and detected states for privacy preflight checks. They never certify that an application or entity is adherent to regulations.

---

## 1. Overview

This document specifies the JSON input format consumed by `scripts/report.py`. The input file represents the evaluation output from automated scanners, assisted tools, or engineering reviewers.

---

## 2. Format Structure

The input file must be a JSON document containing either:
- A JSON array of finding objects, or
- A JSON object with a top-level `"findings"` array of finding objects.

### Required and Optional Fields per Finding

| Field | Type | Required? | Allowed Values / Format | Description |
|---|---|---|---|---|
| `check_id` | string | **Yes** | `^[A-Z]{2}-[A-Z0-9]+-[0-9]{3}$` | Check identifier corresponding to an active check in `references/jurisdictions/<jurisdiction>.md` (e.g. `IN-DPDP-002`). |
| `result` | string | **Yes** | `met` \| `not-met` \| `unclear` \| `needs-human` \| `informational` | Outcome of the check evaluation. |
| `evidence` | array of strings | **Yes** | Non-empty list of strings | Direct evidence pointers: source file locations (`file:line`), URLs, network domains, or API routes. |
| `suggested_fix` | string | No | String | Optional recommendation for engineers or product teams to address the finding. |
| `notes` | string | No | String | Optional contextual remarks from the evaluator or scanning tool. |

---

## 3. Result Enums

- `met`: The check's pass criteria were met.
- `not-met`: The check's pass criteria were not met.
- `unclear`: Ambiguous signals detected; automated heuristic could not make a determination.
- `needs-human`: Human or legal reviewer confirmation required (e.g. parental verification sufficiency, contextual necessity).
- `informational`: Output provided for inventory or transparency (e.g. third-party network calls); no pass/fail assigned.

---

## 4. Machine-Readable Schema (JSON Schema Draft-07)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PrivacyPreflightFindings",
  "oneOf": [
    {
      "type": "array",
      "items": { "$ref": "#/definitions/findingItem" }
    },
    {
      "type": "object",
      "required": ["findings"],
      "properties": {
        "findings": {
          "type": "array",
          "items": { "$ref": "#/definitions/findingItem" }
        }
      }
    }
  ],
  "definitions": {
    "findingItem": {
      "type": "object",
      "required": ["check_id", "result", "evidence"],
      "properties": {
        "check_id": {
          "type": "string",
          "pattern": "^[A-Z]{2}-[A-Z0-9]+-[0-9]{3}$"
        },
        "result": {
          "type": "string",
          "enum": ["met", "not-met", "unclear", "needs-human", "informational"]
        },
        "evidence": {
          "type": "array",
          "items": { "type": "string", "minLength": 1 },
          "minItems": 1
        },
        "suggested_fix": {
          "type": "string"
        },
        "notes": {
          "type": "string"
        }
      },
      "additionalProperties": false
    }
  }
}
```

---

## 5. Example Document

```json
[
  {
    "check_id": "IN-DPDP-002",
    "result": "met",
    "evidence": [
      "src/components/NoticeModal.tsx:42",
      "https://example.com/privacy-notice"
    ],
    "suggested_fix": "Verify that withdrawal and grievance mechanisms are tested regularly.",
    "notes": "Verified working routes on web signup flow."
  },
  {
    "check_id": "IN-BP-004",
    "result": "informational",
    "evidence": [
      "fonts.googleapis.com (US)",
      "cdn.segment.com (US)"
    ],
    "notes": "Third-party network call inventory. Legal status unclear (open-questions.md Q2)."
  }
]
```

