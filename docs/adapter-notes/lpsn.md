# LPSN adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API: `https://lpsn.dsmz.de/api/`
- Portal: https://lpsn.dsmz.de

## Authentication

LPSN requires account registration for programmatic API access.
Set `ELIXIR_LPSN_PASSWORD` and `ELIXIR_LPSN_USERNAME` or configure
via TOML / OS keyring.

Signup URL: https://lpsn.dsmz.de/user/register

## Adapter

Credentialed stub — raises `MissingCredentialError` from `query()`.

## Citation

Parte AC, et al. List of Prokaryotic names with Standing in Nomenclature
(LPSN) moves to the DSMZ.
Int. J. Syst. Evol. Microbiol. 70:5607–5612 (2020).

**Consulted:** 2026-05-02
