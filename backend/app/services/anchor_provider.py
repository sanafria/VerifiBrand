# Anchor Provider abstraction for Merkle anchoring
"""Provides a minimal pluggable interface to an external Merkle-anchor service.
The code intentionally contains **only a mock implementation** – the real
provider will be supplied later by Member 4.  The factory reads the environment
variable ``ANCHOR_ENV``:

* ``test`` (default when the variable is unset) → :class:`MockAnchorProvider` –
  returns a deterministic synthetic receipt and marks the source as ``"mock"``.
* ``production`` → raises :exc:`NotImplementedError` because no real provider
  implementation exists yet.
* **Any other value** (e.g. ``prod``, ``staging``, a typo) → raises
  :exc:`ValueError` so that mis-configured deployments fail loudly instead
  of silently falling back to the mock.

All callers must treat a ``"mock"`` receipt as *unverified*: the DAO rejects
any attempt to transition an anchor with ``receipt_source == "mock"`` to the
``"anchored"`` state.
"""

from __future__ import annotations

import os
from typing import Protocol, Dict, Any


class AnchorProvider(Protocol):
    """Abstract protocol for an external anchoring service.

    The method must return a mapping containing at least ``external_id`` and
    ``receipt`` (opaque string).  Additional fields such as ``timestamp`` are
    optional but useful for audit trails.
    """

    def anchor(self, root_hash: str) -> Dict[str, Any]:
        ...


class MockAnchorProvider:
    """Testing stub – deterministic, never contacts the network.

    The returned receipt is deliberately synthetic; the DAO will never promote
    a record with ``receipt_source='mock'`` to the ``anchored`` state.
    """

    def anchor(self, root_hash: str) -> Dict[str, Any]:
        # Produce a short deterministic external identifier based on the hash
        external_id = f"mock-{root_hash[:8]}"
        return {
            "external_id": external_id,
            "receipt": "mock-receipt-base64",
            "timestamp": "2000-01-01T00:00:00Z",
        }


def get_anchor_provider() -> AnchorProvider:
    """Factory that returns the appropriate provider for the current environment.

    Allowed values for the ``ANCHOR_ENV`` environment variable:

    * ``test`` (default when the variable is unset) → :class:`MockAnchorProvider`.
    * ``production`` → raises :exc:`NotImplementedError` because no real
      provider implementation exists yet.
    * **Any other value** (e.g. ``prod``, ``staging``, a typo) → raises
      :exc:`ValueError` so that mis-configured deployments fail loudly instead
      of silently falling back to the mock.

    This function is intentionally fail-closed: an unrecognised environment name
    is treated as a configuration error, not as a safe default.
    """
    env = os.getenv("ANCHOR_ENV", "test").strip().lower()

    if env == "test":
        return MockAnchorProvider()

    if env == "production":
        # Placeholder – concrete implementation must be added by Member 4.
        raise NotImplementedError(
            "Real AnchorProvider not configured for production. "
            "A concrete implementation must be supplied before production anchoring can proceed."
        )

    # Any other explicit value is a configuration error; fail closed.
    raise ValueError(
        f"Unknown ANCHOR_ENV value '{env}'. "
        "Accepted values are 'test' (default) or 'production'."
    )
