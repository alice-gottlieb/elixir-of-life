"""Adapter package. Importing this module triggers registration of every adapter.

Adapters use ``@elixir_query.registry.register`` at class-definition time, so we just
need to import each submodule to register it.
"""

from __future__ import annotations

import importlib
import pkgutil

_SUBMODULES: list[str] = []

for _modinfo in pkgutil.iter_modules(__path__):
    if _modinfo.name.startswith("_"):
        continue
    _SUBMODULES.append(_modinfo.name)
    importlib.import_module(f"{__name__}.{_modinfo.name}")

__all__ = ["_SUBMODULES"]
