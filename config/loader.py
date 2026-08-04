"""Load and gate the config layer: policy.yaml, accounts.yaml, tax/FY*.yaml.

This package exists because §2.2 forbids `engine/` from reading files or
hitting a network, and `ledger/` holds facts rather than config. Something
has to turn YAML into values; it lives here, outside both. See
docs/decisions/0007-code-before-config-complete.md.

The point of this module is not convenience. It is to make two invariants
fail loudly instead of quietly:

* **§2.4** — an `UNVERIFIED` tax value is never handed out as if it were a
  fact. :class:`TaxTable` raises on access and can list what is missing, so
  the value can be *surfaced* rather than used.
* **§9 / 0001** — a `REQUIRED` sentinel in policy.yaml is an unmade decision,
  not a value. :class:`Policy` raises rather than returning the string
  ``"REQUIRED"``, which would otherwise sail into a calculation and produce
  a number that looks real.

Both gates exist because the alternative is a recommendation that appears
sound and rests on a guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

#: Marks a decision the household has not made yet. See policy.yaml.
REQUIRED = "REQUIRED"

#: A tax value that has not been checked against ATO guidance (§2.4).
UNVERIFIED = "UNVERIFIED"
VERIFIED = "VERIFIED"

_MISSING = object()


class ConfigError(Exception):
    """Base for config-layer failures."""


class ValueNotSet(ConfigError):
    """A policy field is still the REQUIRED sentinel."""


class ValueUnverified(ConfigError):
    """A tax value has not been verified against source (§2.4)."""


class ConfigNotFound(ConfigError):
    """A config file is missing."""


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigNotFound(f"config file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a YAML mapping at the top level")
    return data


def _walk(node: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """Yield (dotted_path, value) for every leaf in a nested mapping."""
    out: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                out.extend(_walk(value, path))
            else:
                out.append((path, value))
    return out


def _dig(data: dict[str, Any], path: str) -> Any:
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


@dataclass(frozen=True)
class Policy:
    """policy.yaml, with unmade decisions gated."""

    data: dict[str, Any]
    path: Path | None = None

    @classmethod
    def load(cls, path: str | Path) -> Policy:
        path = Path(path)
        return cls(data=_read_yaml(path), path=path)

    def get(self, path: str, default: Any = _MISSING) -> Any:
        """Fetch a dotted path, raising if the decision has not been made.

        Returning ``"REQUIRED"`` here would be worse than raising: it is a
        truthy string that compares fine, formats fine, and only fails once
        it reaches arithmetic — by which point the traceback points at the
        engine rather than at the unmade decision.
        """
        value = _dig(self.data, path)
        if value is _MISSING:
            if default is not _MISSING:
                return default
            raise ConfigError(f"policy has no field {path!r}")
        if value == REQUIRED:
            raise ValueNotSet(
                f"policy.{path} is still REQUIRED — this is a decision for the "
                f"household, not a default. See docs/decisions/0001-policy-values-pending.md"
            )
        return value

    def is_set(self, path: str) -> bool:
        value = _dig(self.data, path)
        return value is not _MISSING and value != REQUIRED

    def unset_fields(self) -> list[str]:
        """Every field still awaiting a decision. Sorted, for stable output."""
        return sorted(path for path, value in _walk(self.data) if value == REQUIRED)

    @property
    def blocks_on_unverified_tax(self) -> bool:
        return bool(self.get("reporting.block_on_unverified_tax_values", default=True))

    @property
    def blocks_on_unclassified(self) -> bool:
        return bool(self.get("reporting.block_on_unclassified", default=True))


@dataclass(frozen=True)
class TaxTable:
    """tax/FY<year>.yaml, with unverified values gated (§2.4).

    Values in this file are stamped: each is a mapping carrying ``value``,
    ``status``, and provenance. A ``candidate`` alongside is a lead for a
    human verifier and is never returned by :meth:`get` — that separation is
    the whole point, and collapsing it would make the file look verified
    while it is not.
    """

    data: dict[str, Any]
    path: Path | None = None

    @classmethod
    def load(cls, path: str | Path) -> TaxTable:
        path = Path(path)
        return cls(data=_read_yaml(path), path=path)

    @property
    def financial_year(self) -> str | None:
        return self.data.get("financial_year")

    @staticmethod
    def _is_stamp(node: Any) -> bool:
        return isinstance(node, dict) and "status" in node and "value" in node

    def get(self, path: str, *, allow_unverified: bool = False) -> Any:
        """Fetch a stamped value, raising unless it has been verified.

        `allow_unverified` exists only so a caller can deliberately show an
        unverified figure *labelled as such*. It never silently substitutes a
        candidate; if the value is null it stays null.
        """
        node = _dig(self.data, path)
        if node is _MISSING:
            raise ConfigError(f"tax table has no field {path!r}")
        if not self._is_stamp(node):
            return node
        status = node.get("status")
        if status != VERIFIED and not allow_unverified:
            raise ValueUnverified(
                f"tax.{path} is {status} — value not checked against source. "
                f"§2.4 forbids asserting it. "
                f"candidate={node.get('candidate')!r} "
                f"source={node.get('source_url')!r}. "
                f"See docs/decisions/0002-tax-values-unverified.md"
            )
        return node.get("value")

    def stamps(self) -> list[tuple[str, dict[str, Any]]]:
        """Every stamped value in the file, as (dotted_path, stamp)."""
        found: list[tuple[str, dict[str, Any]]] = []

        def visit(node: Any, prefix: str) -> None:
            if self._is_stamp(node):
                found.append((prefix, node))
                return
            if isinstance(node, dict):
                for key, value in node.items():
                    visit(value, f"{prefix}.{key}" if prefix else str(key))

        visit(self.data, "")
        return sorted(found, key=lambda pair: pair[0])

    def unverified_fields(self) -> list[str]:
        return [path for path, stamp in self.stamps() if stamp.get("status") != VERIFIED]

    def is_fully_verified(self) -> bool:
        return not self.unverified_fields()


@dataclass(frozen=True)
class Config:
    """The three config files, loaded together."""

    policy: Policy
    tax: TaxTable
    accounts: dict[str, Any]

    @classmethod
    def load(cls, root: str | Path = ".", *, financial_year: str = "FY2027") -> Config:
        root = Path(root)
        return cls(
            policy=Policy.load(root / "policy.yaml"),
            tax=TaxTable.load(root / "tax" / f"{financial_year}.yaml"),
            accounts=_read_yaml(root / "accounts.yaml"),
        )

    def blockers(self) -> list[str]:
        """Everything preventing a §5 recommendation, as human-readable lines.

        §2.4 requires unverified values to be *surfaced* in the output rather
        than silently used. This is what gets surfaced.
        """
        lines: list[str] = []

        unset = self.policy.unset_fields()
        if unset:
            lines.append(f"{len(unset)} policy field(s) still REQUIRED:")
            lines.extend(f"  policy.{name}" for name in unset)

        if self.policy.blocks_on_unverified_tax:
            unverified = self.tax.unverified_fields()
            if unverified:
                fy = self.tax.financial_year or "tax table"
                lines.append(f"{len(unverified)} {fy} value(s) UNVERIFIED:")
                lines.extend(f"  tax.{name}" for name in unverified)

        if not self.accounts.get("accounts"):
            lines.append(
                "accounts.yaml defines no accounts — no mortgage rate, so the "
                "§5.4 hurdle (mortgage_rate + risk_premium_bps) cannot be evaluated."
            )

        return lines

    def can_recommend(self) -> bool:
        """True only when nothing in :meth:`blockers` stands in the way."""
        return not self.blockers()
