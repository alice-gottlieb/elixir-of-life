"""Unit tests for the credential-resolution pipeline (env -> config -> keyring -> prompt)."""

from __future__ import annotations

from pathlib import Path

import pytest

from elixir_query.config import Config
from elixir_query.core.credentials import CredentialStore
from elixir_query.errors import MissingCredentialError


@pytest.fixture
def config(tmp_path: Path) -> Config:
    cfg = Config()
    cfg.cache_dir = tmp_path / "cache"
    cfg.config_path = tmp_path / "config.toml"
    cfg.allow_prompt = False  # always non-interactive in tests
    return cfg


def test_env_var_wins(config: Config, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ELIXIR_FOO_API_KEY", "env-value")
    store = CredentialStore(config)
    assert store.get("foo", "api_key") == "env-value"


def test_config_toml_fallback(config: Config, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ELIXIR_FOO_API_KEY", raising=False)
    config.config_path.write_text('[foo]\napi_key = "toml-value"\n')
    store = CredentialStore(config)
    # Avoid using a real keyring backend: stub it out.
    store._keyring_mod = False  # type: ignore[assignment]
    assert store.get("foo", "api_key") == "toml-value"


def test_runtime_credential_wins(config: Config, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ELIXIR_FOO_API_KEY", "env-loses")
    config.set_credential("foo", api_key="runtime-wins")
    store = CredentialStore(config)
    assert store.get("foo", "api_key") == "runtime-wins"


def test_missing_everywhere_raises(config: Config, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ELIXIR_FOO_API_KEY", raising=False)
    store = CredentialStore(config)
    store._keyring_mod = False  # type: ignore[assignment]
    with pytest.raises(MissingCredentialError) as exc:
        store.get("foo", "api_key", signup_url="https://example.org/register")
    msg = str(exc.value)
    assert "ELIXIR_FOO_API_KEY" in msg
    assert str(config.config_path) in msg
    assert "https://example.org/register" in msg


def test_missing_tool_message_format():
    from elixir_query.core.tools import require
    from elixir_query.errors import MissingToolError

    with pytest.raises(MissingToolError) as exc:
        require("ega", "definitely-not-installed", install_hint="pip install nothing")
    assert "definitely-not-installed" in str(exc.value)
    assert "pip install nothing" in str(exc.value)
