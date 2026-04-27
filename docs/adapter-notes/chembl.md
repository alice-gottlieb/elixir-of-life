# ChEMBL adapter notes

**Consulted:** 2026-04-27 via ChEMBL web services documentation.

## Base URL

- REST API: `https://www.ebi.ac.uk/chembl/api/data`
- Swagger docs: `https://www.ebi.ac.uk/chembl/api/data/docs`

## Endpoints used

- `GET /molecule/{chembl_id}` — single molecule by ChEMBL ID (e.g. `CHEMBL25` for aspirin).
- `GET /molecule.json?molecule_chembl_id__in={ids}` — batch lookup (comma-joined IDs).
- `GET /molecule.json?<filters>&limit=&offset=` — paginated search.
- `GET /target/{target_chembl_id}` — single target.
- `GET /activity.json?molecule_chembl_id={id}` — bioactivities for a molecule.

## Response formats

JSON, XML, YAML, SDF, PNG, SVG. We request `application/json` via the `Accept`
header (or `.json` suffix on the path); persist text artifacts as CSV+Parquet
through `core.cache`.

## Pagination

- Query parameters `limit` (default 20, max 1000) and `offset`.
- Each response carries a top-level `page_meta` block with `next`, `previous`,
  `total_count`, `offset`, `limit`. The adapter follows `page_meta.next` when set.

## Rate limits / UA

- No documented hard rate limit; 429 returned on excessive use. Our `HttpClient`
  honours `Retry-After`.
- `User-Agent: elixir-query/<version>`.

## Example request

`GET https://www.ebi.ac.uk/chembl/api/data/molecule/CHEMBL25.json`

Response (excerpt):
```json
{
  "molecule_chembl_id": "CHEMBL25",
  "pref_name": "ASPIRIN",
  "molecule_type": "Small molecule",
  "max_phase": 4,
  "first_approval": 1950,
  "molecule_properties": {"full_mwt": 180.16, "alogp": 1.19, ...}
}
```

Test sentinel: `pref_name == "ASPIRIN"` and `molecule_chembl_id == "CHEMBL25"` for `CHEMBL25`.

## Bulk dumps

Full SQLite + flat-file releases at
`https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/`. Multi-GB; not
implemented in v1 (use `query()` with a wide filter instead). `supports_bulk = False`.

## Citation

Zdrazil B, et al. The ChEMBL Database in 2023: a drug discovery platform spanning
multiple bioactivity data types and time periods. Nucleic Acids Res. 51:D1180–D1192 (2023).
