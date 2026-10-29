# Check Schema Specification

> **Engineering and research specification. Not legal advice.**
> Passing checks defined under this schema does not constitute legal compliance with the Digital Personal Data Protection Act, 2023, the Information Technology Act, 2000, or any other statute.

---

## 1. Overview

This document specifies the required schema for automated and assisted privacy preflight checks. Checks are structured to ensure full traceability back to official primary texts, prevent unverified claims, and strictly separate statutory duties (`LAW`) from engineering recommendations (`BEST PRACTICE`).

---

## 2. Required Fields per Check

Every check definition must provide the following fields inside a single YAML block:

| Field | Type | Allowed Values / Format | Description & Constraints |
|---|---|---|---|
| `id` | string | `^[A-Z]{2}-[A-Z0-9]+-[0-9]{3}$` | Unique identifier (e.g. `IN-DPDP-002`, `IN-BP-001`). |
| `title` | string | Non-empty string | Short, human-readable summary of the check. |
| `label` | string | `LAW` \| `BEST PRACTICE` | Distinction between statutory mandate and engineering practice. **No mixed labels permitted.** Mixed checks must be split into distinct entries. |
| `provision` | string | Citation string or `"none (engineering practice)"` | Citation to statute/rule (e.g. `Act s.5(1); Rules r.3(c)`). If `label` is `BEST PRACTICE`, `provision` must be exactly `"none (engineering practice)"`. If `label` is `LAW`, a valid citation is mandatory. |
| `applies_from` | string | Key into `config/effective-dates.yaml` or `"none"` | For `LAW` entries: dot-notation key path into `config/effective-dates.yaml` (e.g. `dpdp.stage_3`, `spdi.in_force`, `certin.in_force`). Never a literal date. Status (`IN FORCE NOW` vs `READINESS`) is computed dynamically at runtime from today's date. For `BEST PRACTICE` entries: must be exactly `"none"`. |
| `applies_until` | string (optional) | Key into `config/effective-dates.yaml` | Allowed **ONLY** on `LAW` entries. Dot-notation key into `config/effective-dates.yaml` (e.g. `spdi.s43a_omitted`). Must resolve to a valid key in the config and must represent a date later than `applies_from`. Not permitted on `BEST PRACTICE` entries. |
| `last_verified` | string | `YYYY-MM-DD` | Date of last verification against the cited source (e.g. `2026-10-29`). |
| `verified_against` | string | `official-text` \| `mirror` \| `secondary` \| `not-verified` \| `n/a` | Source type examined. For `BEST PRACTICE` entries, must be `"n/a"`. |
| `verified_by` | string | `ai-read` \| `human-read` | **Strict Rule:** Must be `ai-read` by default. Set to `human-read` **ONLY** if the jurisdiction's verification log explicitly records a human spot-check for that item. Never upgrade automatically. |
| `confidence` | string | `high` \| `medium` \| `low` | Confidence in provision traceability and objective automation feasibility. Not a legal opinion. |
| `caveats` | string | Non-empty string | Statutory carve-outs, unverified notifications, ambiguities, or scope qualifiers. |
| `open_question_refs` | array of strings | List of refs (e.g. `["Q1", "Q2"]`) | Unresolved legal questions from `open-questions.md`. Empty list `[]` if none. |
| `detection_type` | string | `automated` \| `assisted` \| `human-judgment` | Operational classification of detection mechanism. |
| `detection` | string | Non-empty string | Concrete steps or heuristics used by tools or engineers to inspect the codebase/system. |
| `pass_criteria` | string | Non-empty string | Pass/fail criteria or informational output instructions. |

### Optional Operational Fields
- `research_ref`: string (e.g. `"IN-DPDP-017/018"`). Cross-reference to candidate check IDs from earlier research files.
- `status`: Lifecycle status (`active` \| `proposed` \| `deprecated`). Defaults to `active`.

### Dynamic Status and Report Behaviour
- Status (`IN FORCE NOW` vs `READINESS` vs `UNRESOLVED`) is computed dynamically at runtime relative to today's date:
  - If today < `applies_from`: status is `READINESS`.
  - If today >= `applies_from` and no `applies_until`: status is `IN FORCE NOW`.
  - If an entry specifies `applies_until` (e.g. `IN-SPDI-001` with `spdi.s43a_omitted`):
    - While today < `applies_until`: status is `IN FORCE NOW`.
    - Once today >= `applies_until`: status transitions to `UNRESOLVED (Q8, Q23)`, **not** `IN FORCE NOW`.

---

## 3. Validation Rules

1. **Mandatory Fields:** Every check must contain all required fields in its YAML block.
2. **Date Key Integrity:**
   - If `label: LAW`, `applies_from` must resolve to a valid key in `config/effective-dates.yaml` (must not be `"none"`). If `applies_until` is present, it must resolve to a valid key in `config/effective-dates.yaml` and the date must be later than `applies_from`.
   - If `label: BEST PRACTICE`, `applies_from` must be exactly `"none"`, and `applies_until` must not be present.
3. **Legal Citation & Best Practice Rules:**
   - If `label: LAW`, `provision` must not be `"none (engineering practice)"` or empty, and `verified_against` must not be `"n/a"`.
   - If `label: BEST PRACTICE`, `provision` must be exactly `"none (engineering practice)"`, `verified_against` must be `"n/a"`, `applies_from` must be `"none"`, and `applies_until` is not permitted.
4. **Verification Log Parity:** Any check with `verified_against: official-text` must have a matching row in the per-jurisdiction verification log (`research/{jurisdiction}/verification-log.md`, e.g. `research/india/verification-log.md`). Entries with `verified_against: n/a` do not require a log row.
5. **No Mixed Checks:** Mixed statutory and engineering recommendations must be split into separate entries (e.g. a `LAW` check for statutory requirements and an `IN-BP-xxx` check for best practices).
6. **No "Compliant" Output:** Tool outputs and check documentation must never state that an application or entity is "compliant".

---

## 4. Machine-Readable Schema (JSON Schema Draft-07)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PrivacyPreflightCheck",
  "type": "object",
  "required": [
    "id",
    "title",
    "label",
    "provision",
    "applies_from",
    "last_verified",
    "verified_against",
    "verified_by",
    "confidence",
    "caveats",
    "open_question_refs",
    "detection_type",
    "detection",
    "pass_criteria"
  ],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[A-Z]{2}-[A-Z0-9]+-[0-9]{3}$"
    },
    "title": {
      "type": "string",
      "minLength": 5
    },
    "label": {
      "type": "string",
      "enum": ["LAW", "BEST PRACTICE"]
    },
    "provision": {
      "type": "string",
      "minLength": 3
    },
    "applies_from": {
      "type": "string",
      "pattern": "^(none|[a-z0-9_]+(\\.[a-z0-9_]+)*)$"
    },
    "applies_until": {
      "type": "string",
      "pattern": "^[a-z0-9_]+(\\.[a-z0-9_]+)*$"
    },
    "last_verified": {
      "type": "string",
      "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    },
    "verified_against": {
      "type": "string",
      "enum": ["official-text", "mirror", "secondary", "not-verified", "n/a"]
    },
    "verified_by": {
      "type": "string",
      "enum": ["ai-read", "human-read"]
    },
    "confidence": {
      "type": "string",
      "enum": ["high", "medium", "low"]
    },
    "caveats": {
      "type": "string"
    },
    "open_question_refs": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^Q[0-9]+$"
      }
    },
    "detection_type": {
      "type": "string",
      "enum": ["automated", "assisted", "human-judgment"]
    },
    "detection": {
      "type": "string"
    },
    "pass_criteria": {
      "type": "string"
    },
    "research_ref": {
      "type": "string"
    },
    "status": {
      "type": "string",
      "enum": ["active", "proposed", "deprecated"],
      "default": "active"
    }
  },
  "allOf": [
    {
      "if": {
        "properties": { "label": { "const": "LAW" } }
      },
      "then": {
        "properties": {
          "provision": {
            "not": { "const": "none (engineering practice)" }
          },
          "verified_against": {
            "not": { "const": "n/a" }
          },
          "applies_from": {
            "not": { "const": "none" }
          }
        }
      }
    },
    {
      "if": {
        "properties": { "label": { "const": "BEST PRACTICE" } }
      },
      "then": {
        "properties": {
          "provision": {
            "const": "none (engineering practice)"
          },
          "verified_against": {
            "const": "n/a"
          },
          "applies_from": {
            "const": "none"
          }
        },
        "not": {
          "required": ["applies_until"]
        }
      }
    }
  ]
}
```

