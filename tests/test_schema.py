"""Tests for the §4 transaction contract."""

import datetime as dt
from decimal import Decimal

import pytest

from ledger.schema import (
    UNCLASSIFIED,
    Account,
    AccountKind,
    Ledger,
    Owner,
    SchemaError,
    Transaction,
    to_decimal,
)

DATE = dt.date(2026, 7, 15)


def make(**overrides):
    kwargs = dict(
        date=DATE,
        account_id="offset_main",
        amount="-42.50",
        description="WOOLWORTHS 1234 SYDNEY",
        owner=Owner.JOINT,
    )
    kwargs.update(overrides)
    return Transaction.create(**kwargs)


# ── §4: amount is Decimal, never float ──────────────────────────────────────


def test_float_amount_is_rejected():
    with pytest.raises(SchemaError, match="not float"):
        make(amount=42.50)


def test_float_rejection_message_suggests_the_fix():
    with pytest.raises(SchemaError) as exc:
        make(amount=0.1)
    assert "Decimal('0.1')" in str(exc.value)


def test_string_amount_is_exact():
    """The reason floats are banned: str→Decimal is exact, float→Decimal is not."""
    assert to_decimal("0.1") == Decimal("0.1")
    assert to_decimal("0.1") != Decimal(0.1)


def test_decimal_and_int_amounts_pass_through():
    assert make(amount=Decimal("-42.50")).amount == Decimal("-42.50")
    assert make(amount=-42).amount == Decimal(-42)


def test_bool_amount_is_rejected():
    """bool is an int subclass, so this would otherwise coerce to 0 or 1."""
    with pytest.raises(SchemaError, match="bool"):
        make(amount=True)


def test_unparseable_string_amount_is_rejected():
    with pytest.raises(SchemaError, match="not a valid decimal"):
        make(amount="forty two")


def test_constructor_rejects_non_decimal_amount():
    """The raw constructor is stricter than create() — it does not coerce."""
    with pytest.raises(SchemaError, match="must be Decimal"):
        Transaction(
            date=DATE,
            account_id="offset_main",
            amount="-42.50",
            description="x",
            owner=Owner.JOINT,
        )


# ── §2.5: owner is mandatory on every line ──────────────────────────────────


def test_owner_accepts_the_three_enum_values():
    for owner in ("person_a", "person_b", "joint"):
        assert make(owner=owner).owner is Owner(owner)


def test_unknown_owner_is_rejected():
    with pytest.raises(ValueError):
        make(owner="person_c")


def test_constructor_rejects_bare_string_owner():
    with pytest.raises(SchemaError, match="never inferred"):
        Transaction(
            date=DATE,
            account_id="offset_main",
            amount=Decimal("1"),
            description="x",
            owner="joint",
        )


# ── §4: category defaults to UNCLASSIFIED ───────────────────────────────────


def test_category_defaults_to_unclassified():
    txn = make()
    assert txn.category == UNCLASSIFIED
    assert not txn.is_classified


def test_classified_as_returns_a_new_object_and_preserves_the_raw_line():
    raw = make()
    classified = raw.classified_as("groceries")
    assert classified.category == "groceries"
    assert classified.is_classified
    # The original is untouched — a wrong rule stays traceable to what it saw.
    assert raw.category == UNCLASSIFIED
    assert classified.description == raw.description


def test_empty_category_is_rejected():
    with pytest.raises(SchemaError, match="UNCLASSIFIED"):
        make(category="")


# ── §4: is_transfer ─────────────────────────────────────────────────────────


def test_is_transfer_defaults_false_and_must_be_bool():
    assert make().is_transfer is False
    with pytest.raises(SchemaError, match="is_transfer"):
        make(is_transfer="yes")


def test_classified_as_can_set_transfer_without_touching_category_default():
    txn = make().classified_as("internal", is_transfer=True)
    assert txn.is_transfer is True
    assert txn.category == "internal"


# ── §4: date is a date, not a datetime ──────────────────────────────────────


def test_datetime_is_rejected():
    """Transaction date, not settlement — and a datetime invites timezone drift
    across the month boundary where surplus is measured."""
    with pytest.raises(SchemaError, match="not datetime"):
        make(date=dt.datetime(2026, 7, 15, 9, 30))


# ── §2.3: append-only ───────────────────────────────────────────────────────


def test_transaction_is_frozen():
    txn = make()
    with pytest.raises(Exception):
        txn.amount = Decimal("1")


def test_adjustment_records_a_correction_without_mutating():
    original = make(amount="-100.00", description="DUPLICATE CHARGE")
    fix = original.adjustment(amount="100.00", description="Reversal of duplicate")
    assert fix.amount == Decimal("100.00")
    assert fix.adjusts == "DUPLICATE CHARGE"
    assert fix.owner is original.owner
    assert original.amount == Decimal("-100.00")


def test_ledger_append_returns_a_new_ledger():
    ledger = Ledger()
    grown = ledger.append(make(), make(amount="-1.00"))
    assert len(ledger) == 0
    assert len(grown) == 2


def test_ledger_has_no_removal_api():
    """§2.3 — corrections are adjustment entries, not deletions."""
    for forbidden in ("remove", "delete", "pop", "clear", "update"):
        assert not hasattr(Ledger(), forbidden)


def test_ledger_surfaces_unclassified_lines():
    ledger = Ledger().append(
        make().classified_as("groceries"),
        make(description="UNKNOWN EFTPOS 99"),
    )
    unclassified = ledger.unclassified
    assert len(unclassified) == 1
    assert unclassified[0].description == "UNKNOWN EFTPOS 99"


# ── Accounts ────────────────────────────────────────────────────────────────


def test_account_requires_enum_kind_and_owner():
    account = Account(
        account_id="offset_main",
        display_name="Everyday Offset",
        kind=AccountKind.OFFSET,
        owner=Owner.JOINT,
        offsets_account="mortgage_main",
    )
    assert account.kind is AccountKind.OFFSET

    with pytest.raises(SchemaError, match="kind"):
        Account(
            account_id="x", display_name="x", kind="offset", owner=Owner.JOINT
        )


def test_blank_account_id_is_rejected():
    with pytest.raises(SchemaError, match="account_id"):
        make(account_id="   ")
