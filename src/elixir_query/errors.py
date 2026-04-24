"""Exception hierarchy for elixir-query."""

from __future__ import annotations


class ElixirError(Exception):
    """Base class for all elixir-query errors."""


class UnknownDatabaseError(ElixirError):
    """Raised when get() is called with a database name that isn't registered."""

    def __init__(self, name: str, suggestion: str | None = None) -> None:
        msg = f"Unknown ELIXIR database: {name!r}."
        if suggestion:
            msg += f" Did you mean {suggestion!r}?"
        msg += " Use elixir_query.list_databases() to see available databases."
        super().__init__(msg)
        self.name = name
        self.suggestion = suggestion


class ElixirConfigError(ElixirError):
    """Base class for configuration errors (missing creds, tools, etc.)."""


class MissingCredentialError(ElixirConfigError):
    """A required credential for a database adapter could not be located."""

    def __init__(self, db: str, field: str, *, env_var: str, config_path: str, signup_url: str | None = None) -> None:
        lines = [
            f"Missing credential {field!r} for ELIXIR database {db!r}.",
            "Provide it in one of the following ways:",
            f"  1. Set the environment variable {env_var}.",
            f"  2. Add a [{db}] section to {config_path} with '{field} = \"...\"'.",
            f"  3. Store it in the OS keyring under service 'elixir-query:{db}' with username '{field}'.",
            "  4. Run interactively; elixir-query will prompt and offer to save the value.",
        ]
        if signup_url:
            lines.append(f"If you do not yet have credentials, register at: {signup_url}")
        super().__init__("\n".join(lines))
        self.db = db
        self.field = field
        self.env_var = env_var
        self.config_path = config_path
        self.signup_url = signup_url


class MissingToolError(ElixirConfigError):
    """A required third-party CLI tool is not installed / not on PATH."""

    def __init__(self, db: str, tool: str, *, install_hint: str) -> None:
        msg = (
            f"Database {db!r} requires the external tool {tool!r} on PATH. "
            f"Install it: {install_hint}"
        )
        super().__init__(msg)
        self.db = db
        self.tool = tool
        self.install_hint = install_hint


class AdapterError(ElixirError):
    """Raised when an adapter cannot fulfil a query (bad params, upstream error, parse error).

    Adapters MUST NOT swallow upstream errors silently or return fabricated data. If the
    upstream response cannot be parsed, raise AdapterError (or let the underlying exception
    propagate) so tests and callers see a loud failure.
    """


class UpstreamError(AdapterError):
    """Raised when an upstream ELIXIR endpoint returns an unexpected response."""

    def __init__(self, db: str, url: str, status: int | None, detail: str) -> None:
        msg = f"[{db}] upstream error from {url}"
        if status is not None:
            msg += f" (HTTP {status})"
        msg += f": {detail}"
        super().__init__(msg)
        self.db = db
        self.url = url
        self.status = status


class ParseError(AdapterError):
    """Raised when an upstream payload cannot be parsed into a DataFrame."""

    def __init__(self, db: str, detail: str) -> None:
        super().__init__(f"[{db}] parse error: {detail}")
        self.db = db
