# Credentialed adapter stubs (EGA, BRENDA, BacDive, LPSN)

**Consulted:** 2026-05-03 — overview of why these databases ship as stubs in v1.

These four ELIXIR Core Data Resources require account registration and an API
key (or username + password) to retrieve any data. v1 of `elixir-query` ships
**stub adapters only**: they register themselves so they appear in
`eq.list_databases()` and `eq.describe(<db>)`, but `query()` always raises
`MissingCredentialError` with the exact env-var name, config-file path,
keyring service, and signup URL the user needs to proceed. A full
implementation will land once we have working credentials in test
infrastructure.

The error message wording is deterministic — every test for a stub adapter
asserts `MissingCredentialError` with a substring of the signup URL. This
gives the policy a concrete contract that future implementations must keep
honouring (or break the test).

| adapter | service                     | signup URL                              | env var                  |
|---|---|---|---|
| ega     | European Genome-phenome Archive | https://ega-archive.org/register      | `ELIXIR_EGA_API_KEY`     |
| brenda  | BRENDA enzyme info system   | https://www.brenda-enzymes.org/register.php | `ELIXIR_BRENDA_PASSWORD` |
| bacdive | bacterial diversity metadatabase | https://api.bacdive.dsmz.de/        | `ELIXIR_BACDIVE_PASSWORD`|
| lpsn    | List of Prokaryotic names with Standing in Nomenclature | https://api.lpsn.dsmz.de/ | `ELIXIR_LPSN_PASSWORD` |

## Behaviour contract

```python
import elixir_query as eq
from elixir_query.errors import MissingCredentialError

# Without the right env var set, all four raise MissingCredentialError:
try:
    eq.get("ega")
except MissingCredentialError as e:
    print(e)
# -> mentions ELIXIR_EGA_API_KEY, the config.toml path, and the signup URL.
```

Each stub adapter's `meta.requires_credentials = True` and
`meta.credential_fields` lists the field names the user needs to supply.

## Future work

When credentials become available in CI:
1. Replace the `query()` body to actually hit the upstream API.
2. Add real-data tests with a sentinel record (the existing
   `MissingCredentialError` test stays valid — just runs with the env var
   unset).
3. Update `supports_bulk` if applicable.
