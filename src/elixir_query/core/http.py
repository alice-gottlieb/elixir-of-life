"""Shared HTTP client with sensible retries, UA, and pagination helpers.

Used by every adapter. Keep this thin — per-API quirks belong in the adapters.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from elixir_query.errors import UpstreamError

log = logging.getLogger(__name__)


def _package_version() -> str:
    try:
        from importlib.metadata import version

        return version("elixir-query")
    except Exception:  # pragma: no cover - best-effort
        return "0.0.0"


_DEFAULT_UA = (
    f"elixir-query/{_package_version()} "
    "(https://github.com/alice-gottlieb/elixir-of-life)"
)


class HttpClient:
    """Thin wrapper around httpx.Client with retries and paging helpers."""

    def __init__(
        self,
        *,
        user_agent: str = _DEFAULT_UA,
        timeout: float = 60.0,
        max_retries: int = 4,
    ) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"},
            timeout=timeout,
            follow_redirects=True,
        )
        self._max_retries = max_retries

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------------ request
    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
        db: str = "",
    ) -> httpx.Response:
        """Issue a request with retries on 429/5xx. Raises UpstreamError on 4xx/5xx."""

        @retry(
            reraise=True,
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=30),
            retry=retry_if_exception_type((httpx.TransportError, _RetryableStatus)),
        )
        def _send() -> httpx.Response:
            resp = self._client.request(
                method, url, params=params, headers=headers, data=data, json=json
            )
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                retry_after = resp.headers.get("retry-after")
                log.warning(
                    "%s %s -> %s (retry-after=%s); retrying",
                    method, url, resp.status_code, retry_after,
                )
                raise _RetryableStatus(resp.status_code, url)
            return resp

        resp = _send()
        if resp.status_code >= 400:
            detail = resp.text[:500] if resp.text else ""
            raise UpstreamError(db or "elixir", str(resp.request.url), resp.status_code, detail)
        return resp

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    # ---------------------------------------------------------------- pagination
    def paginate_offset(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        limit_param: str = "limit",
        offset_param: str = "offset",
        page_size: int = 200,
        max_pages: int | None = None,
        db: str = "",
    ) -> Iterator[httpx.Response]:
        """Yield responses in offset/limit style. Stops when a page is short."""
        params = dict(params or {})
        params.setdefault(limit_param, page_size)
        offset = 0
        page = 0
        while True:
            params[offset_param] = offset
            resp = self.get(url, params=params, headers=headers, db=db)
            yield resp
            page += 1
            if max_pages is not None and page >= max_pages:
                return
            # Caller is responsible for deciding when to stop (e.g. short page).
            offset += params[limit_param]

    def paginate_link(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        max_pages: int | None = None,
        db: str = "",
    ) -> Iterator[httpx.Response]:
        """Yield responses following RFC 5988 ``Link: <...>; rel="next"`` headers.

        UniProt, GWAS Catalog and others use this style.
        """
        next_url: str | None = url
        next_params: dict[str, Any] | None = dict(params or {})
        page = 0
        while next_url:
            resp = self.get(next_url, params=next_params, headers=headers, db=db)
            yield resp
            page += 1
            if max_pages is not None and page >= max_pages:
                return
            next_url = _extract_link_next(resp.headers.get("link"))
            next_params = None  # next URL already contains params

    # ------------------------------------------------------------------- stream
    def stream_to_file(
        self,
        url: str,
        dest: Any,
        *,
        headers: dict[str, str] | None = None,
        db: str = "",
        chunk_size: int = 1 << 20,
    ) -> int:
        """Stream a large response to ``dest`` (a file path). Returns bytes written.

        Uses a fresh (non-retrying) request because partial-content resumption is
        adapter-specific.
        """
        bytes_written = 0
        with self._client.stream("GET", url, headers=headers) as resp:
            if resp.status_code >= 400:
                resp.read()
                raise UpstreamError(db or "elixir", url, resp.status_code, resp.text[:500])
            with open(dest, "wb") as fh:
                for chunk in resp.iter_bytes(chunk_size=chunk_size):
                    fh.write(chunk)
                    bytes_written += len(chunk)
        return bytes_written


class _RetryableStatus(Exception):
    """Internal marker: upstream returned a retryable status code (429/5xx)."""

    def __init__(self, status: int, url: str) -> None:
        super().__init__(f"retryable status {status} for {url}")
        self.status = status
        self.url = url


def _extract_link_next(header: str | None) -> str | None:
    if not header:
        return None
    # header: '<https://...>; rel="next", <https://...>; rel="last"'
    for part in header.split(","):
        segments = [s.strip() for s in part.split(";")]
        if len(segments) < 2:
            continue
        url_part = segments[0]
        rels = [s for s in segments[1:] if s.startswith("rel=")]
        if not rels:
            continue
        rel = rels[0].split("=", 1)[1].strip().strip('"')
        if rel == "next" and url_part.startswith("<") and url_part.endswith(">"):
            return url_part[1:-1]
    return None


__all__ = ["HttpClient"]
