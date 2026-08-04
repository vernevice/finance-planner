"""Transaction and account models — the §4 data contract.

This module is the `ledger/` layer: facts and structure only. It contains no
judgement (§2.2). There are no thresholds here, no categorisation logic, and
no opinion about what a transaction means — only what shape it must have and
which shapes are rejected outright.

It reads no files and imports nothing from `engine/` or `config/`.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import Enum
from typing import Any

#: A transaction that no rule in ledger/rules.yaml has matched. Not a
#: category in its own right — it means "not yet known", and §5 output is
#: blocked while any remain (policy.reporting.block_on_unclassified).
UNCLASSIFIED = "UNCLASSIFIED"


class SchemaError(ValueError):
    """A value violates the §4 contract."""


class Owner(str, Enum):
    """§2.5 — `owner` is a first-class field on every income line.

    Cashflow rolls up to the household, but tax, super and asset-ownership
    decisions drop back to the individual (§8), and that split is impossible
    to reconstruct after the fact. Hence: mandatory, never inferred.
    """

    PERSON_A = "person_a"
    PERSON_B = "person_b"
    JOINT = "joint"


class AccountKind(str, Enum):
    OFFSET = "offset"
    TRANSACTION = "transaction"
    SAVINGS = "savings"
    MORTGAGE = "mortgage"
    SUPER = "super"
    BROKER = "broker"


def to_decimal(value: Any, *, field_name: str = "amount") -> Decimal:
    """Coerce to Decimal, rejecting float.

    §4 says amounts are Decimal and **never float**, and this is the one
    place that rule can actually be enforced. The failure mode is quiet:
    ``Decimal(0.1)`` is 0.1000000000000000055511151231257827021181583404541,
    so a float that slips in here does not raise anything — it just makes
    every downstream total slightly wrong, in a way that looks like a
    rounding artefact rather than a bug. Since Phase 0's exit criterion is a
    2% reconciliation, a systematic error small enough to hide inside that
    tolerance is exactly the kind that survives to production.

    Accepts Decimal, int, or str. A str is the correct way to carry a value
    in from a CSV — ``Decimal("12.34")`` is exact.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        # bool is an int subclass; a bool amount is always a bug.
        raise SchemaError(f"{field_name} must not be a bool, got {value!r}")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        try:
            return Decimal(value.strip())
        except Exception as exc:  # noqa: BLE001 - re-raised with context
            raise SchemaError(f"{field_name} is not a valid decimal: {value!r}") from exc
    if isinstance(value, float):
        raise SchemaError(
            f"{field_name} must be Decimal, not float (got {value!r}). "
            f"Pass a string instead: Decimal({str(value)!r}). See §4."
        )
    raise SchemaError(f"{field_name} must be Decimal, int or str, got {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class Account:
    """An account as declared in accounts.yaml.

    `account_id` must be stable across exports. Bank exports change column
    order, date format and display names freely; they rarely change the
    account number.
    """

    account_id: str
    display_name: str
    kind: AccountKind
    owner: Owner
    institution: str | None = None
    currency: str = "AUD"
    #: For an offset account, the loan it offsets. Used to detect internal
    #: movement between the pair.
    offsets_account: str | None = None

    def __post_init__(self) -> None:
        if not self.account_id or not self.account_id.strip():
            raise SchemaError("account_id must be a non-empty string")
        if not isinstance(self.kind, AccountKind):
            raise SchemaError(f"kind must be an AccountKind, got {self.kind!r}")
        if not isinstance(self.owner, Owner):
            raise SchemaError(f"owner must be an Owner, got {self.owner!r}")


@dataclass(frozen=True, slots=True)
class Transaction:
    """A normalised transaction — the §4 contract.

    Frozen, because §2.3 makes the ledger append-only. A correction is an
    adjustment entry, not a mutation; see :meth:`adjustment`.
    """

    #: Transaction date, not settlement date (§4). The two differ by days
    #: around month boundaries, which is where surplus is measured.
    date: _dt.date
    account_id: str
    amount: Decimal
    #: Raw and unmodified (§4). Rules match against it; they never rewrite it.
    #: Keeping the original is what makes a misclassification reviewable later.
    description: str
    owner: Owner
    category: str = UNCLASSIFIED
    #: §4: the highest-risk field in the system. Both incomes land in the
    #: offset and are moved out again, so this sees heavy traffic. A missed
    #: transfer inflates BOTH income and expenses; the error nets out of the
    #: balance, so it is invisible in a reconciliation against statements —
    #: but it does not net out of surplus.
    is_transfer: bool = False
    #: Set on adjustment entries to point at what they correct.
    adjusts: str | None = None
    #: Free-form provenance, e.g. the source export filename.
    source: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.date, _dt.date) or isinstance(self.date, _dt.datetime):
            raise SchemaError(
                f"date must be a datetime.date (not datetime), got {type(self.date).__name__}"
            )
        if not self.account_id or not self.account_id.strip():
            raise SchemaError("account_id must be a non-empty string")
        if not isinstance(self.owner, Owner):
            raise SchemaError(
                f"owner must be an Owner enum member, got {self.owner!r}. "
                f"§2.5 requires it on every line; it is never inferred."
            )
        if not isinstance(self.is_transfer, bool):
            raise SchemaError(f"is_transfer must be a bool, got {self.is_transfer!r}")
        if not isinstance(self.amount, Decimal):
            raise SchemaError(
                f"amount must be Decimal, got {type(self.amount).__name__}. "
                f"Use Transaction.create() or to_decimal() to coerce safely."
            )
        if not self.category:
            raise SchemaError("category must be non-empty; use UNCLASSIFIED if unknown")

    @classmethod
    def create(
        cls,
        *,
        date: _dt.date,
        account_id: str,
        amount: Any,
        description: str,
        owner: Owner | str,
        category: str = UNCLASSIFIED,
        is_transfer: bool = False,
        adjusts: str | None = None,
        source: str | None = None,
    ) -> Transaction:
        """Build a Transaction, coercing `amount` and `owner` safely.

        Prefer this over the constructor at ingest boundaries: it is the only
        path that rejects a float amount with a useful message.
        """
        return cls(
            date=date,
            account_id=account_id,
            amount=to_decimal(amount),
            description=description,
            owner=Owner(owner),
            category=category,
            is_transfer=is_transfer,
            adjusts=adjusts,
            source=source,
        )

    @property
    def is_classified(self) -> bool:
        return self.category != UNCLASSIFIED

    def classified_as(self, category: str, *, is_transfer: bool | None = None) -> Transaction:
        """Return a copy with a category applied.

        Classification produces a new object rather than mutating: the raw
        line as imported stays intact, so a wrong rule can be traced back to
        what it saw.
        """
        return replace(
            self,
            category=category,
            is_transfer=self.is_transfer if is_transfer is None else is_transfer,
        )

    def adjustment(
        self, *, amount: Any, description: str, category: str | None = None
    ) -> Transaction:
        """Build a correcting entry against this transaction.

        §2.3: corrections are adjustment entries, not mutations. Raw exports
        are never edited, so an error found in month N is fixed by an entry,
        leaving both the original and the correction visible.
        """
        return Transaction.create(
            date=self.date,
            account_id=self.account_id,
            amount=amount,
            description=description,
            owner=self.owner,
            category=category or self.category,
            is_transfer=self.is_transfer,
            adjusts=self.description,
            source="adjustment",
        )


@dataclass(frozen=True, slots=True)
class Ledger:
    """An append-only collection of transactions (§2.3).

    Deliberately offers no remove/update. `append` returns a new Ledger
    rather than mutating, so a caller cannot quietly drop a line.
    """

    transactions: tuple[Transaction, ...] = field(default_factory=tuple)

    def append(self, *txns: Transaction) -> Ledger:
        return Ledger(self.transactions + tuple(txns))

    def __len__(self) -> int:
        return len(self.transactions)

    def __iter__(self):
        return iter(self.transactions)

    @property
    def unclassified(self) -> tuple[Transaction, ...]:
        """Lines no rule matched.

        §5 output is blocked while any exist: an unclassified line may be
        income, an expense, or an internal transfer, and those three produce
        very different surpluses.
        """
        return tuple(t for t in self.transactions if not t.is_classified)
