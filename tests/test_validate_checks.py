"""
Tests for Check Validator (scripts/validate_checks.py).
Ensures that the real jurisdiction pack passes, and that mutation tests
on temporary copies (tmp_path) accurately trigger expected rule failures or warnings.
"""

from __future__ import annotations

import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.validate_checks import (
    format_validation_output,
    validate_jurisdiction,
)


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Creates a temporary isolated copy of the workspace files needed for validation."""
    # Copy references/
    ref_dir = tmp_path / "references" / "jurisdictions"
    ref_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(WORKSPACE_ROOT / "references" / "jurisdictions" / "india.md", ref_dir / "india.md")
    shutil.copy(WORKSPACE_ROOT / "references" / "check-schema.md", tmp_path / "references" / "check-schema.md")

    # Copy config/
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(WORKSPACE_ROOT / "config" / "effective-dates.yaml", cfg_dir / "effective-dates.yaml")
    if (WORKSPACE_ROOT / "config" / "restricted-countries.yaml").exists():
        shutil.copy(WORKSPACE_ROOT / "config" / "restricted-countries.yaml", cfg_dir / "restricted-countries.yaml")

    # Copy research/
    res_dir = tmp_path / "research" / "india"
    res_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(WORKSPACE_ROOT / "research" / "india" / "verification-log.md", res_dir / "verification-log.md")
    shutil.copy(WORKSPACE_ROOT / "research" / "india" / "open-questions.md", res_dir / "open-questions.md")

    return tmp_path


def test_real_pack_passes():
    """First test: the real references/jurisdictions/india.md passes with 0 failures."""
    today = datetime.date(2026, 10, 29)
    result = validate_jurisdiction(jurisdiction="india", today=today, base_dir=WORKSPACE_ROOT)
    output = format_validation_output(result)

    assert result.is_valid, f"Real pack failed validation:\n{output}"
    assert len(result.failures) == 0
    assert result.active_law_count == 8
    assert result.active_bp_count == 4
    assert result.proposed_count == 1
    assert result.total_checks == 13


def test_mutation_missing_required_field(temp_workspace: Path):
    """Expect failure when a required field (e.g. detection_type) is missing."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    mutated = content.replace("detection_type: automated", "")
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.rule == "required-fields" and "detection_type" in f.message
        for f in result.failures
    )


def test_mutation_unknown_applies_from_key(temp_workspace: Path):
    """Expect failure when applies_from references an unknown key."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    mutated = content.replace("applies_from: dpdp.stage_3", "applies_from: dpdp.stage_unknown", 1)
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.rule == "law-applies-from" and "dpdp.stage_unknown" in f.message
        for f in result.failures
    )


def test_mutation_law_with_none_provision(temp_workspace: Path):
    """Expect failure when a LAW check has provision 'none (engineering practice)'."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    mutated = content.replace('provision: "Act s.6(1), 6(2)"', 'provision: "none (engineering practice)"')
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.check_id == "IN-DPDP-004" and f.rule == "law-provision"
        for f in result.failures
    )


def test_mutation_best_practice_with_real_applies_from(temp_workspace: Path):
    """Expect failure when a BEST PRACTICE check has a real applies_from instead of 'none'."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    mutated = content.replace(
        "id: IN-BP-001\ntitle: Self-host static assets (fonts, scripts, and CDNs)\nlabel: BEST PRACTICE\nprovision: \"none (engineering practice)\"\napplies_from: none",
        "id: IN-BP-001\ntitle: Self-host static assets (fonts, scripts, and CDNs)\nlabel: BEST PRACTICE\nprovision: \"none (engineering practice)\"\napplies_from: dpdp.stage_3",
    )
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.check_id == "IN-BP-001" and f.rule == "bp-applies-from"
        for f in result.failures
    )


def test_mutation_applies_until_on_best_practice(temp_workspace: Path):
    """Expect failure when a BEST PRACTICE check contains applies_until."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    mutated = content.replace(
        "id: IN-BP-001\ntitle: Self-host static assets (fonts, scripts, and CDNs)\nlabel: BEST PRACTICE\nprovision: \"none (engineering practice)\"\napplies_from: none",
        "id: IN-BP-001\ntitle: Self-host static assets (fonts, scripts, and CDNs)\nlabel: BEST PRACTICE\nprovision: \"none (engineering practice)\"\napplies_from: none\napplies_until: spdi.s43a_omitted",
    )
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.check_id == "IN-BP-001" and f.rule == "bp-applies-until-absent"
        for f in result.failures
    )


def test_mutation_applies_until_earlier_than_applies_from(temp_workspace: Path):
    """Expect failure when applies_until date is earlier than applies_from date."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    # IN-DPDP-004 has applies_from: dpdp.stage_3 (2027-05-13); set applies_until to dpdp.stage_1 (2025-11-13)
    mutated = content.replace(
        "applies_from: dpdp.stage_3",
        "applies_from: dpdp.stage_3\napplies_until: dpdp.stage_1",
        1,
    )
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.rule == "applies-until-later"
        for f in result.failures
    )


def test_mutation_official_text_no_log_row(temp_workspace: Path):
    """Expect failure when a check has verified_against: official-text but no matching row in verification-log.md."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    mutated = content.replace("id: IN-DPDP-004", "id: IN-DPDP-999")
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.check_id == "IN-DPDP-999" and f.rule == "official-text-log-row"
        for f in result.failures
    )


def test_mutation_human_read_without_log_support(temp_workspace: Path):
    """Expect failure when verified_by: human-read is claimed but log records ai-read."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    mutated = content.replace(
        "id: IN-DPDP-004\ntitle: Consent controls (unbundled purposes and no pre-ticked controls)\nlabel: LAW\nprovision: \"Act s.6(1), 6(2)\"\napplies_from: dpdp.stage_3\nlast_verified: 2026-10-29\nverified_against: official-text\nverified_by: ai-read",
        "id: IN-DPDP-004\ntitle: Consent controls (unbundled purposes and no pre-ticked controls)\nlabel: LAW\nprovision: \"Act s.6(1), 6(2)\"\napplies_from: dpdp.stage_3\nlast_verified: 2026-10-29\nverified_against: official-text\nverified_by: human-read",
    )
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.check_id == "IN-DPDP-004" and f.rule == "human-read-log-row"
        for f in result.failures
    )


def test_mutation_duplicate_id(temp_workspace: Path):
    """Expect failure when duplicate check IDs exist in the jurisdiction pack."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    # Rename IN-BP-001 to IN-BP-004
    mutated = content.replace("id: IN-BP-001", "id: IN-BP-004")
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.rule == "id-unique" and "IN-BP-004" in f.message
        for f in result.failures
    )


def test_mutation_unknown_q_ref(temp_workspace: Path):
    """Expect failure when open_question_refs contains a Q-ref not in open-questions.md."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    mutated = content.replace("open_question_refs:\n  - Q7", "open_question_refs:\n  - Q99")
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.check_id == "IN-DPDP-010" and f.rule == "open-questions-exist" and "Q99" in f.message
        for f in result.failures
    )


def test_mutation_compliant_in_pass_criteria(temp_workspace: Path):
    """Expect failure when pass_criteria contains prohibited word 'compliant'."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    pattern = r'(id:\s*IN-DPDP-004\b[\s\S]*?pass_criteria:\s*")([^"]*)(")'
    mutated = re.sub(pattern, r'\1\2 compliant\3', content, count=1)
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.check_id == "IN-DPDP-004" and f.rule == "no-compliant-wording"
        for f in result.failures
    )


def test_mutation_compliant_in_title(temp_workspace: Path):
    """Expect failure when title contains prohibited word 'compliant'."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    mutated = content.replace(
        "title: Consent controls (unbundled purposes and no pre-ticked controls)",
        "title: Compliant consent controls (unbundled)",
    )
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.check_id == "IN-DPDP-004" and f.rule == "no-compliant-wording"
        for f in result.failures
    )


def test_mutation_last_verified_in_future(temp_workspace: Path):
    """Expect failure when last_verified date is in the future relative to --today."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    mutated = content.replace("last_verified: 2026-10-29", "last_verified: 2026-11-15", 1)
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    assert not result.is_valid
    assert any(
        f.rule == "last-verified-future"
        for f in result.failures
    )


def test_mutation_stale_last_verified_produces_warning(temp_workspace: Path):
    """Expect warning (NOT failure, exit code 0) when last_verified is > 90 days before --today."""
    india_md = temp_workspace / "references" / "jurisdictions" / "india.md"
    content = india_md.read_text(encoding="utf-8")
    # Mutate one check to 2026-01-01
    mutated = content.replace("last_verified: 2026-10-29", "last_verified: 2026-01-01", 1)
    assert mutated != content
    india_md.write_text(mutated, encoding="utf-8")

    result = validate_jurisdiction("india", today=datetime.date(2026, 10, 29), base_dir=temp_workspace)
    # Stale date must produce warning, but NOT fail
    assert result.is_valid
    assert len(result.failures) == 0
    assert any(
        w.rule == "last-verified-stale" and "2026-01-01" in w.message
        for w in result.warnings
    )


def test_cli_execution():
    """Verify CLI exit code and output formatting."""
    proc = subprocess.run(
        [sys.executable, "scripts/validate_checks.py", "--today", "2026-10-29"],
        cwd=str(WORKSPACE_ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Active LAW checks:          8" in proc.stdout
    assert "Active BEST PRACTICE checks: 4" in proc.stdout
    assert "Proposed checks:            1" in proc.stdout
    assert "Total failures:             0" in proc.stdout


def test_missing_config_effective_dates_raises_error(temp_workspace: Path):
    """Missing config/effective-dates.yaml raises FileNotFoundError with reinstall guidance."""
    (temp_workspace / "config" / "effective-dates.yaml").unlink()
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_jurisdiction("india", base_dir=temp_workspace)
    assert "Reinstall the skill with all its folders (scripts, references, config, research); do not create this file." in str(exc_info.value)


def test_missing_verification_log_raises_error(temp_workspace: Path):
    """Missing research/india/verification-log.md raises FileNotFoundError with reinstall guidance."""
    (temp_workspace / "research" / "india" / "verification-log.md").unlink()
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_jurisdiction("india", base_dir=temp_workspace)
    assert "Reinstall the skill with all its folders (scripts, references, config, research); do not create this file." in str(exc_info.value)


def test_missing_open_questions_raises_error(temp_workspace: Path):
    """Missing research/india/open-questions.md raises FileNotFoundError with reinstall guidance."""
    (temp_workspace / "research" / "india" / "open-questions.md").unlink()
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_jurisdiction("india", base_dir=temp_workspace)
    assert "Reinstall the skill with all its folders (scripts, references, config, research); do not create this file." in str(exc_info.value)


def test_missing_research_dir_raises_error(temp_workspace: Path):
    """Missing research/india directory raises FileNotFoundError with reinstall guidance."""
    shutil.rmtree(temp_workspace / "research" / "india")
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_jurisdiction("india", base_dir=temp_workspace)
    assert "Reinstall the skill with all its folders (scripts, references, config, research); do not create this file." in str(exc_info.value)


def test_skill_md_contract_and_clean_text():
    """Assert SKILL.md contains required key phrases and no emoji or tick symbols."""
    skill_file = WORKSPACE_ROOT / "SKILL.md"
    content = skill_file.read_text(encoding="utf-8")

    # Short key phrases
    for phrase in [
        "stand-in",
        "model reading, not scanner output",
        "not evaluated",
        "SKILL.md",
        "scripts",
        "references",
        "config",
        "research/india",
    ]:
        assert phrase in content, f"Missing key phrase: '{phrase}'"

    # No emoji or tick characters
    assert "✓" not in content, "SKILL.md must not contain tick symbol '✓'"
    assert "✔" not in content, "SKILL.md must not contain tick symbol '✔'"
    assert "✗" not in content, "SKILL.md must not contain cross symbol '✗'"
    assert "✘" not in content, "SKILL.md must not contain cross symbol '✘'"
    assert not re.search(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF]", content), "SKILL.md must not contain emoji characters"
