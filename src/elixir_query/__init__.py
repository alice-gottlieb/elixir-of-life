"""elixir-query: unified Python access to ELIXIR Core Data Resources.

Example:
    >>> import elixir_query as eq
    >>> df = eq.get("uniprot", query="insulin AND reviewed:true", limit=100)
    >>> lf = eq.get("rhea", bulk=True)
"""

from elixir_query import config, errors
from elixir_query.api import clear_cache, describe, get, list_databases

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "clear_cache",
    "config",
    "describe",
    "errors",
    "get",
    "list_databases",
]

# Importing the adapters package triggers adapter registration via side effects.
from elixir_query import adapters as _adapters  # noqa: E402,F401
