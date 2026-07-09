"""Shared test fixtures.

Respects the project-wide real-data-only policy: core plumbing tests may use tmp
directories and in-memory structures (they test the library itself), but adapter
tests MUST hit real endpoints and may not use mocks or synthetic fixture data.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-bulk",
        action="store_true",
        default=False,
        help="Run slow bulk-download tests that materialise multi-MB/GB dumps.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-bulk"):
        return
    skip_bulk = pytest.mark.skip(reason="need --run-bulk to run bulk-download tests")
    for item in items:
        if "bulk" in item.keywords:
            item.add_marker(skip_bulk)


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the cache and config paths at a tmpdir for every test.

    This keeps real user caches untouched and makes each test idempotent.
    """
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    monkeypatch.setenv("ELIXIR_QUERY_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("ELIXIR_QUERY_CONFIG", str(cfg_dir / "config.toml"))
    monkeypatch.setenv("ELIXIR_QUERY_NO_PROMPT", "1")
    # Force re-initialisation of the config + context singletons per test.
    import elixir_query.api as _api
    import elixir_query.config as _cfg

    _cfg._SINGLETON = None
    _api._reset_context_for_tests()
    yield cache_dir
    _cfg._SINGLETON = None
    _api._reset_context_for_tests()
