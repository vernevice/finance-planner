"""Tests for the §2.4 and §9 config gates.

These are the invariants written as executable checks. The tax file is
currently 100% unverified, so the gate in :class:`TaxTable` is the only thing
standing between a candidate figure and a recommendation that looks sound.
"""

from pathlib import Path

import pytest
import yaml

from config.loader import (
    Config,
    ConfigError,
    ConfigNotFound,
    Policy,
    TaxTable,
    ValueNotSet,
    ValueUnverified,
)

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def policy(tmp_path):
    (tmp_path / "policy.yaml").write_text(
        yaml.safe_dump(
            {
                "buffer": {"months": 3, "basis": "REQUIRED"},
                "investment": {"risk_premium_bps": 250},
                "reporting": {"block_on_unverified_tax_values": True},
            }
        )
    )
    return Policy.load(tmp_path / "policy.yaml")


@pytest.fixture
def tax(tmp_path):
    (tmp_path / "tax.yaml").write_text(
        yaml.safe_dump(
            {
                "financial_year": "FY2027",
                "super": {
                    "concessional_cap": {
                        "value": None,
                        "status": "UNVERIFIED",
                        "candidate": 32500,
                        "source_url": "https://example.invalid",
                    },
                    "contributions_tax_rate": {
                        "value": 0.15,
                        "status": "VERIFIED",
                        "verified_on": "2026-08-04",
                    },
                },
            }
        )
    )
    return TaxTable.load(tmp_path / "tax.yaml")


# ── §9 / 0001: REQUIRED is an unmade decision, not a value ──────────────────


def test_set_value_is_returned(policy):
    assert policy.get("buffer.months") == 3
    assert policy.get("investment.risk_premium_bps") == 250


def test_required_sentinel_raises_rather_than_returning_the_string(policy):
    with pytest.raises(ValueNotSet, match="buffer.basis"):
        policy.get("buffer.basis")


def test_required_sentinel_is_not_silently_truthy(policy):
    """The failure this prevents: "REQUIRED" is a truthy string that compares
    and formats fine, and only breaks once it reaches arithmetic — where the
    traceback points at the engine instead of at the unmade decision."""
    try:
        value = policy.get("buffer.basis")
    except ValueNotSet:
        value = None
    assert value is None


def test_is_set_reports_without_raising(policy):
    assert policy.is_set("buffer.months")
    assert not policy.is_set("buffer.basis")
    assert not policy.is_set("nonexistent.field")


def test_unset_fields_lists_every_pending_decision(policy):
    assert policy.unset_fields() == ["buffer.basis"]


def test_missing_field_raises_unless_defaulted(policy):
    with pytest.raises(ConfigError, match="no field"):
        policy.get("buffer.nonexistent")
    assert policy.get("buffer.nonexistent", default="fallback") == "fallback"


def test_a_default_never_masks_an_unmade_decision(policy):
    """A default is for a field that is absent, not for one that is REQUIRED —
    otherwise the gate could be bypassed by passing a default."""
    with pytest.raises(ValueNotSet):
        policy.get("buffer.basis", default="all")


# ── §2.4: an UNVERIFIED tax value is never handed out ───────────────────────


def test_verified_value_is_returned(tax):
    assert tax.get("super.contributions_tax_rate") == 0.15


def test_unverified_value_raises(tax):
    with pytest.raises(ValueUnverified, match="concessional_cap"):
        tax.get("super.concessional_cap")


def test_candidate_is_never_substituted_for_a_value(tax):
    """The candidate/value split is the whole point of the file. If get() ever
    falls back to a candidate, tax/FY2027.yaml starts looking verified."""
    with pytest.raises(ValueUnverified):
        tax.get("super.concessional_cap")
    assert tax.get("super.concessional_cap", allow_unverified=True) is None


def test_the_error_carries_the_candidate_and_source_for_the_verifier(tax):
    with pytest.raises(ValueUnverified) as exc:
        tax.get("super.concessional_cap")
    message = str(exc.value)
    assert "32500" in message
    assert "example.invalid" in message
    assert "0002" in message


def test_unverified_fields_are_enumerable(tax):
    assert tax.unverified_fields() == ["super.concessional_cap"]
    assert not tax.is_fully_verified()


# ── The real repo files ─────────────────────────────────────────────────────
# These pin the current state. They are expected to change as config is
# filled in and verified — a failure here means progress, not a bug.


def test_the_committed_tax_table_is_entirely_unverified():
    table = TaxTable.load(REPO / "tax" / "FY2027.yaml")
    assert table.financial_year == "FY2027"
    stamps = table.stamps()
    assert stamps, "expected stamped values in tax/FY2027.yaml"
    assert table.unverified_fields() == [path for path, _ in stamps]


def test_no_committed_tax_value_can_be_read():
    """ato.gov.au was unreachable, so nothing in the file may be used (0002)."""
    table = TaxTable.load(REPO / "tax" / "FY2027.yaml")
    for path, _ in table.stamps():
        with pytest.raises(ValueUnverified):
            table.get(path)


def test_committed_policy_has_the_two_settled_values():
    policy = Policy.load(REPO / "policy.yaml")
    assert policy.get("buffer.months") == 3
    assert policy.get("investment.risk_premium_bps") == 250


def test_committed_policy_still_gates_the_undecided_fields():
    policy = Policy.load(REPO / "policy.yaml")
    unset = policy.unset_fields()
    assert "buffer.basis" in unset
    assert "super.hurdle_bps" in unset
    assert "ownership.optimise_for_marginal_rate" in unset


def test_repo_cannot_yet_produce_a_recommendation():
    config = Config.load(REPO)
    assert not config.can_recommend()
    blockers = config.blockers()
    assert any("REQUIRED" in line for line in blockers)
    assert any("UNVERIFIED" in line for line in blockers)
    assert any("accounts.yaml" in line for line in blockers)


def test_blockers_are_empty_only_when_everything_is_resolved(tmp_path):
    (tmp_path / "policy.yaml").write_text(
        yaml.safe_dump({"reporting": {"block_on_unverified_tax_values": True}})
    )
    (tmp_path / "tax").mkdir()
    (tmp_path / "tax" / "FY2027.yaml").write_text(
        yaml.safe_dump(
            {"cgt": {"discount_rate": {"value": 0.5, "status": "VERIFIED"}}}
        )
    )
    (tmp_path / "accounts.yaml").write_text(
        yaml.safe_dump({"accounts": [{"account_id": "offset_main"}]})
    )
    assert Config.load(tmp_path).can_recommend()


def test_missing_config_file_is_a_clear_error(tmp_path):
    with pytest.raises(ConfigNotFound, match="not found"):
        Policy.load(tmp_path / "absent.yaml")


# ── Layer separation (§2.2) ─────────────────────────────────────────────────


def test_engine_reads_no_files_and_hits_no_network():
    """§2.2 — nothing in engine/ reads a file or hits a network.

    Cheap to check now while engine/ is empty, and it fails the moment
    somebody adds an import that breaks the rule.
    """
    forbidden = ("open(", "yaml.", "requests", "urllib", "httpx", "pathlib", "socket")
    for source in (REPO / "engine").rglob("*.py"):
        text = source.read_text()
        for token in forbidden:
            assert token not in text, f"{source.name} appears to use {token!r} (§2.2)"


def test_ledger_does_not_import_config_or_engine():
    """§2.2 — ledger/ holds facts, and must not depend on judgement."""
    for source in (REPO / "ledger").rglob("*.py"):
        text = source.read_text()
        assert "import config" not in text
        assert "from config" not in text
        assert "import engine" not in text
        assert "from engine" not in text
