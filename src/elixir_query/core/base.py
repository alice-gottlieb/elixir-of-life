"""Base classes and shared context for all database adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

import polars as pl

if TYPE_CHECKING:
    from elixir_query.core.cache import Cache
    from elixir_query.core.credentials import CredentialStore
    from elixir_query.core.http import HttpClient


@dataclass(frozen=True)
class AdapterMeta:
    name: str  # canonical, lowercase: "uniprot"
    aliases: tuple[str, ...] = ()
    homepage: str = ""
    citation: str = ""
    requires_credentials: bool = False
    credential_fields: tuple[str, ...] = ()
    requires_tools: tuple[str, ...] = ()
    supports_bulk: bool = False
    example_params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class ElixirContext:
    """Shared resources handed to every adapter: HTTP client, cache, credentials."""

    http: HttpClient
    cache: Cache
    credentials: CredentialStore


class BaseAdapter(ABC):
    """Abstract base for all ELIXIR database adapters.

    Subclasses MUST define a class-level ``meta: AdapterMeta`` and implement
    ``query(**params) -> pl.DataFrame``. ``bulk`` is optional; adapters that support
    bulk downloads override it and set ``meta.supports_bulk = True``.

    Adapters must not return fabricated or empty data on error — they must raise.
    """

    meta: ClassVar[AdapterMeta]

    def __init__(self, ctx: ElixirContext) -> None:
        self.ctx = ctx

    @abstractmethod
    def query(self, **params: Any) -> pl.DataFrame:
        """Targeted query. Return a Polars DataFrame (may be small)."""

    def bulk(self, **params: Any) -> pl.LazyFrame:
        """Optional bulk-download path returning a LazyFrame over cached Parquet.

        Default implementation raises NotImplementedError; adapters that support bulk
        must override. ``meta.supports_bulk`` controls whether the registry exposes
        this capability.
        """
        raise NotImplementedError(
            f"adapter {self.meta.name!r} does not support bulk downloads; "
            f"call eq.get({self.meta.name!r}, ...) without bulk=True."
        )
