"""Reactome adapter (pathway knowledgebase).

Docs: https://reactome.org/ContentService/
Notes: docs/adapter-notes/reactome.md (consulted 2026-04-27).

REST base: https://reactome.org/ContentService
  - /data/query/{id}                 -> generic lookup
  - /data/pathway/{id}/containedEvents
  - /data/pathways/top/{species}
  - /data/participants/{id}
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import read_tsv, records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://reactome.org/ContentService"
_QUERY = _BASE + "/data/query/{id}"
_CONTAINED = _BASE + "/data/pathway/{id}/containedEvents"
_TOP_PATHWAYS = _BASE + "/data/pathways/top/{species}"
_PARTICIPANTS = _BASE + "/data/participants/{id}"

_BULK_URL = "https://reactome.org/download/current/ReactomePathways.txt"

_JSON_HEADERS = {"Accept": "application/json"}
_TTL_QUERY_SECONDS = 7 * 24 * 3600


def _flatten(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, (dict, list)):
            out[k] = _json.dumps(v)
        else:
            out[k] = v
    return out


@register
class ReactomeAdapter(BaseAdapter):
    """Reactome ContentService REST adapter."""

    meta = AdapterMeta(
        name="reactome",
        aliases=("reactomedb",),
        homepage="https://reactome.org",
        citation=(
            "Milacic M, et al. The Reactome Pathway Knowledgebase 2024. "
            "Nucleic Acids Res. 52:D672–D678 (2024)."
        ),
        supports_bulk=True,
        example_params={"id": "R-HSA-69620"},
        description=(
            "Reactome — open-source curated pathway database. Call with "
            "id='R-HSA-69620' for a pathway/event lookup, contained_in='R-HSA-...' "
            "for child events, top_for=9606 for top-level human pathways, or "
            "bulk=True for the full ReactomePathways.txt dump."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        id: str | None = None,
        contained_in: str | None = None,
        top_for: str | int | None = None,
        participants_of: str | None = None,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch records from the Reactome ContentService.

        Args:
            id: Reactome stable identifier (e.g. ``"R-HSA-69620"``) or numeric
                ``dbId``. Triggers ``/data/query/{id}``.
            contained_in: Pathway stable ID; returns all contained events.
            top_for: Species, either a numeric NCBI taxon ID (e.g. ``9606``)
                or species name (e.g. ``"Homo sapiens"``); returns top-level
                pathways for that species.
            participants_of: Event stable ID; returns participating entities.
        """
        if id is None and contained_in is None and top_for is None and participants_of is None:
            raise ValueError(
                "pass id=..., contained_in=..., top_for=..., or participants_of=..."
            )

        if id is not None:
            return self._single(_QUERY.format(id=id), {"kind": "query", "id": id})

        if contained_in is not None:
            return self._list(
                _CONTAINED.format(id=contained_in),
                {"kind": "containedEvents", "id": contained_in},
            )

        if top_for is not None:
            sp = str(top_for)
            return self._list(
                _TOP_PATHWAYS.format(species=sp),
                {"kind": "topPathways", "species": sp},
            )

        assert participants_of is not None
        return self._list(
            _PARTICIPANTS.format(id=participants_of),
            {"kind": "participants", "id": participants_of},
        )

    def _single(self, url: str, key: dict[str, Any]) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("reactome", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="reactome")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("reactome", f"expected dict, got {type(data).__name__}")
        df = records_to_df([_flatten(data)], db="reactome")
        if df.height == 0:
            raise ParseError("reactome", f"no record returned from {url}")
        self.ctx.cache.put_query("reactome", key, df, url=str(resp.request.url))
        return df

    def _list(self, url: str, key: dict[str, Any]) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("reactome", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="reactome")
        data = resp.json()
        if not isinstance(data, list):
            raise ParseError("reactome", f"expected list from {url}, got {type(data).__name__}")
        df = records_to_df((_flatten(r) for r in data), db="reactome")
        if df.height == 0:
            raise ParseError("reactome", f"no rows returned from {url}")
        self.ctx.cache.put_query("reactome", key, df, url=str(resp.request.url))
        return df

    # -------------------------------------------------------------------- bulk
    def bulk(self, **_: Any) -> pl.LazyFrame:
        """Stream the ReactomePathways.txt dump and return a LazyFrame.

        Three columns: ``stId``, ``displayName``, ``speciesName``.
        """
        key = {"kind": "ReactomePathways"}
        parquet = self.ctx.cache.bulk_ready("reactome", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        raw, parquet_path, _meta = self.ctx.cache.bulk_paths("reactome", key)
        self.ctx.http.stream_to_file(_BULK_URL, raw, db="reactome")
        text = raw.read_text(encoding="utf-8")
        df = read_tsv(
            text,
            db="reactome",
            has_header=False,
            new_columns=["stId", "displayName", "speciesName"],
        )
        if df.height == 0:
            raise ParseError("reactome", f"bulk download {_BULK_URL} parsed to zero rows")
        df.write_parquet(parquet_path)
        df.write_csv(raw.with_suffix(".csv"))
        self.ctx.cache.record_bulk(
            "reactome",
            key,
            url=_BULK_URL,
            rows=df.height,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)
