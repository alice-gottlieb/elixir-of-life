# BacDive adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API: `https://bacdive.dsmz.de/api/`
- Portal: https://bacdive.dsmz.de

## Authentication

BacDive requires an account registration for API access (free for research).
Set `ELIXIR_BACDIVE_PASSWORD` and `ELIXIR_BACDIVE_USERNAME` or configure
via TOML / OS keyring.

Signup URL: https://api.bacdive.dsmz.de/user/register/

## Adapter

Credentialed stub — raises `MissingCredentialError` from `query()`.

## Citation

Reimer LC, et al. BacDive in 2022: the knowledge base for
standardized bacterial and archaeal data.
Nucleic Acids Res. 50:D741–D746 (2022).

**Consulted:** 2026-05-02
