"""Credential resolution: env -> config.toml -> keyring -> interactive prompt."""

from __future__ import annotations

import getpass
import logging
import os
import sys
from typing import Any

from elixir_query.config import Config
from elixir_query.errors import MissingCredentialError

log = logging.getLogger(__name__)

_KEYRING_SERVICE_PREFIX = "elixir-query:"


def _env_var(db: str, field: str) -> str:
    return f"ELIXIR_{db.upper()}_{field.upper()}"


class CredentialStore:
    """Resolves credentials in priority order for a given (db, field) pair."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._keyring_mod: Any | None = None  # lazy import — keyring can be slow

    # ------------------------------------------------------------------- lookup
    def get(
        self,
        db: str,
        field: str,
        *,
        signup_url: str | None = None,
        prompt_text: str | None = None,
    ) -> str:
        """Return the credential, trying env → config → keyring → prompt.

        Raises MissingCredentialError if all sources fail or prompting is disabled.
        """
        db = db.lower()

        # 1. runtime override
        runtime = self.config.get_runtime_credential(db, field)
        if runtime:
            return runtime

        # 2. environment variable
        env_name = _env_var(db, field)
        env_val = os.environ.get(env_name)
        if env_val:
            return env_val

        # 3. config file
        data = self.config.load_config_file()
        section = data.get(db)
        if isinstance(section, dict):
            val = section.get(field)
            if isinstance(val, str) and val:
                return val

        # 4. OS keyring
        kr_val = self._keyring_get(db, field)
        if kr_val:
            return kr_val

        # 5. interactive prompt
        if self._can_prompt():
            log.info("prompting user for credential %s/%s", db, field)
            value = self._prompt(db, field, prompt_text)
            if value:
                if self._should_save_to_keyring():
                    self._keyring_set(db, field, value)
                # Cache for the rest of this process so we don't re-prompt.
                self.config.set_credential(db, **{field: value})
                return value

        raise MissingCredentialError(
            db,
            field,
            env_var=env_name,
            config_path=str(self.config.config_path),
            signup_url=signup_url,
        )

    # ------------------------------------------------------------------ keyring
    def _keyring(self) -> Any | None:
        if self._keyring_mod is None:
            try:
                import keyring

                self._keyring_mod = keyring
            except Exception as e:  # pragma: no cover - environment dependent
                log.debug("keyring unavailable: %s", e)
                self._keyring_mod = False  # type: ignore[assignment]
        return self._keyring_mod or None

    def _keyring_get(self, db: str, field: str) -> str | None:
        kr = self._keyring()
        if not kr:
            return None
        try:
            return kr.get_password(f"{_KEYRING_SERVICE_PREFIX}{db}", field)
        except Exception as e:  # pragma: no cover - environment dependent
            log.debug("keyring.get_password failed: %s", e)
            return None

    def _keyring_set(self, db: str, field: str, value: str) -> None:
        kr = self._keyring()
        if not kr:
            return
        try:
            kr.set_password(f"{_KEYRING_SERVICE_PREFIX}{db}", field, value)
        except Exception as e:  # pragma: no cover - environment dependent
            log.warning("could not save credential to keyring: %s", e)

    # ------------------------------------------------------------------- prompt
    def _can_prompt(self) -> bool:
        return bool(self.config.allow_prompt) and sys.stdin.isatty()

    def _prompt(self, db: str, field: str, prompt_text: str | None) -> str:
        label = prompt_text or f"{db} {field}"
        if "password" in field.lower() or "secret" in field.lower() or "token" in field.lower():
            return getpass.getpass(f"Enter {label}: ")
        return input(f"Enter {label}: ")

    def _should_save_to_keyring(self) -> bool:
        # Default yes; user can answer 'n' at prompt.
        try:
            ans = input("Save to OS keyring for future sessions? [Y/n]: ").strip().lower()
        except EOFError:
            return False
        return ans in ("", "y", "yes")


__all__ = ["CredentialStore"]
