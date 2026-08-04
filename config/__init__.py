"""Config layer: loads policy.yaml, accounts.yaml and tax/FY*.yaml.

Kept outside `engine/` because §2.2 forbids engine code from reading files.
"""

from config.loader import (  # noqa: F401
    Config,
    ConfigError,
    ConfigNotFound,
    Policy,
    TaxTable,
    ValueNotSet,
    ValueUnverified,
)
