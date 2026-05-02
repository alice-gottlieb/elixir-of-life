# BRENDA adapter notes

**Consulted:** 2026-05-02

## Base URL

- SOAP / REST API: https://www.brenda-enzymes.org/brenda_download/
- API endpoint: https://www.brenda-enzymes.org/soap/brenda_server.php

## Authentication

BRENDA requires registration and a password for API access.
Set `ELIXIR_BRENDA_PASSWORD` or configure via TOML / OS keyring.
Email address (login) must also be supplied.

Signup URL: https://www.brenda-enzymes.org/register.php

## Adapter

Credentialed stub — raises `MissingCredentialError` from `query()`.

## Citation

Jeske L, et al. BRENDA in 2019: a European ELIXIR core data resource.
Nucleic Acids Res. 47:D542–D549 (2019).

**Consulted:** 2026-05-02
