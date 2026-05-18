"""Provider base protocol and re-exports."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.models import SourceResult


@runtime_checkable
class SourceProvider(Protocol):
    """Protocol that every source provider must implement.

    All providers are async, accept ``chain`` and ``address``,
    and return a ``SourceResult`` or ``None`` if the contract
    is not verified on that provider.
    """

    name: str

    async def fetch(self, chain: str, address: str) -> SourceResult | None:
        """Fetch verified source code for a contract.

        Args:
            chain: Blockchain name (e.g. "ethereum").
            address: Contract address.

        Returns:
            SourceResult if the contract is verified on this provider,
            None if the contract is not found.
        """
        ...


__all__ = ["SourceProvider"]
