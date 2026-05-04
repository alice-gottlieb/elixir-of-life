"""Tests for v1 credentialed-stub adapters: ega, brenda, bacdive, lpsn.

Policy: these stubs raise ``MissingCredentialError`` when no credential is
available. The test runs without network access — it exercises the
credential-resolution + error-message contract, not any upstream endpoint.

When a stub is replaced by a real implementation, the same test must keep
passing (with no env var set) because the credential-missing path is still
the documented behaviour.
"""

from __future__ import annotations

import pytest

import elixir_query as eq
from elixir_query.errors import MissingCredentialError

STUBS = [
    # (db_name, env_var_name, signup_url_substring)
    ("ega", "ELIXIR_EGA_API_KEY", "ega-archive.org"),
    ("brenda", "ELIXIR_BRENDA_PASSWORD", "brenda-enzymes.org"),
    ("bacdive", "ELIXIR_BACDIVE_PASSWORD", "bacdive.dsmz.de"),
    ("lpsn", "ELIXIR_LPSN_PASSWORD", "lpsn.dsmz.de"),
]


@pytest.mark.parametrize("db,env_var,signup_url_part", STUBS)
def test_stub_raises_missing_credential_without_env(
    db: str, env_var: str, signup_url_part: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each stub raises MissingCredentialError naming env_var + signup URL."""
    monkeypatch.delenv(env_var, raising=False)

    with pytest.raises(MissingCredentialError) as exc:
        eq.get(db)

    msg = str(exc.value)
    assert env_var in msg, f"expected {env_var!r} in error message, got: {msg!r}"
    assert signup_url_part in msg, (
        f"expected signup URL substring {signup_url_part!r} in message, got: {msg!r}"
    )


@pytest.mark.parametrize("db,env_var,_", STUBS)
def test_stub_appears_in_list_databases(db: str, env_var: str, _: str) -> None:
    """Each stub registers itself so it appears in eq.list_databases()."""
    assert db in eq.list_databases(), (
        f"stub {db!r} not in list_databases(): {eq.list_databases()}"
    )


@pytest.mark.parametrize("db,_env,_url", STUBS)
def test_stub_describe_advertises_credential_requirement(
    db: str, _env: str, _url: str
) -> None:
    """describe() reports requires_credentials=True for every stub."""
    info = eq.describe(db)
    assert info["requires_credentials"] is True, (
        f"stub {db!r} describe() should report requires_credentials=True, got {info}"
    )
    assert info["credential_fields"], (
        f"stub {db!r} should declare at least one credential field"
    )


def test_stub_with_credential_set_raises_not_implemented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Providing a credential should swap MissingCredentialError for NotImplementedError.

    This is the v1 stub contract: 'credential plumbing works; the upstream
    implementation is the gap.'
    """
    eq.config.set_credential("ega", api_key="dummy")
    with pytest.raises(NotImplementedError, match="ega"):
        eq.get("ega")
