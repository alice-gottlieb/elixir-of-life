# EGA adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API: `https://ega-archive.org/metadata/v2/`
- Portal: https://ega-archive.org

## Authentication

EGA requires a registered account and OAuth2 tokens for data access.
Set env var `ELIXIR_EGA_API_KEY` or configure via TOML / OS keyring.

Signup URL: https://ega-archive.org/register

## Adapter

Credentialed stub — raises `MissingCredentialError` from `query()`.
Full implementation would use the EGA metadata API endpoints:
- `GET /datasets` — list datasets (requires JWT)
- `GET /studies/{accession}` — study metadata

## Citation

Freeberg MA, et al. The European Genome-phenome Archive in 2021.
Nucleic Acids Res. 50:D980–D987 (2022).

**Consulted:** 2026-05-02
