"""User-facing configuration for elixir-query.

Loads defaults from environment variables and (optionally) a config.toml file. Exposes a
singleton ``Config`` object whose setters are the only supported way for user code to
override cache location or credentials at runtime.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_cache_dir, user_config_dir

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - py310 fallback
    import tomli as tomllib

_APP = "elixir-query"


def _default_cache_dir() -> Path:
    override = os.environ.get("ELIXIR_QUERY_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    return Path(user_cache_dir(_APP))


def _default_config_path() -> Path:
    override = os.environ.get("ELIXIR_QUERY_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path(user_config_dir(_APP)) / "config.toml"


@dataclass
class Config:
    cache_dir: Path = field(default_factory=_default_cache_dir)
    config_path: Path = field(default_factory=_default_config_path)
    allow_prompt: bool = field(default_factory=lambda: os.environ.get("ELIXIR_QUERY_NO_PROMPT", "") != "1")
    # In-memory credential overrides keyed by (db, field).
    _runtime_credentials: dict[tuple[str, str], str] = field(default_factory=dict)

    def set_cache_dir(self, path: str | Path) -> None:
        self.cache_dir = Path(path).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def set_config_path(self, path: str | Path) -> None:
        self.config_path = Path(path).expanduser()

    def set_credential(self, db: str, **fields: str) -> None:
        """Set one or more credential fields for ``db`` in-memory for this process."""
        for field_name, value in fields.items():
            self._runtime_credentials[(db.lower(), field_name)] = value

    def get_runtime_credential(self, db: str, field_name: str) -> str | None:
        return self._runtime_credentials.get((db.lower(), field_name))

    def load_config_file(self) -> dict:
        """Return the parsed TOML config file contents, or {} if it doesn't exist."""
        path = self.config_path
        if not path.exists():
            return {}
        with open(path, "rb") as fh:
            return tomllib.load(fh)


_SINGLETON: Config | None = None


def get_config() -> Config:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = Config()
    return _SINGLETON


def set_cache_dir(path: str | Path) -> None:
    get_config().set_cache_dir(path)


def set_config_path(path: str | Path) -> None:
    get_config().set_config_path(path)


def set_credential(db: str, **fields: str) -> None:
    get_config().set_credential(db, **fields)


__all__ = [
    "Config",
    "get_config",
    "set_cache_dir",
    "set_config_path",
    "set_credential",
]
