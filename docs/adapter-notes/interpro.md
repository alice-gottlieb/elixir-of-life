# InterPro adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API: `https://www.ebi.ac.uk/interpro/api`
- Interactive docs / explorer: https://www.ebi.ac.uk/interpro/

## Endpoints used

- `GET /entry/interpro/{accession}/` — single InterPro entry metadata.
- `GET /entry/interpro/?format=json` — paginated list of all InterPro entries.
- `GET /entry/interpro/protein/uniprot/{protein_accession}/?format=json` — InterPro entries
  that match a given UniProt protein.
- `GET /protein/uniprot/{protein_accession}/?format=json` — protein metadata.

## Response formats

JSON only.  Nested objects (`member_databases`, `go_terms`, etc.) are JSON-stringified
for flat DataFrame storage.

## Pagination

`next`-link-in-body style (NOT a Link HTTP header):
```json
{
  "count": 51489,
  "next": "https://www.ebi.ac.uk/interpro/api/entry/interpro?cursor=cD1JUFIwMDAwMzA=",
  "previous": null,
  "results": [ ... ]
}
```
Follow `next` until it is `null`.

## Rate limits / auth

No auth required.  No hard limit documented; retry on 429.

## Example response fields (single entry)

```json
{
  "accession": "IPR000001",
  "name": {"name": "Kringle", "short": "Kringle"},
  "source_database": "interpro",
  "type": "Domain",
  "integrated": null,
  "member_databases": {...},
  "go_terms": [...]
}
```

## Reproducible example

```
GET https://www.ebi.ac.uk/interpro/api/entry/interpro/IPR000001/?format=json
```

Sentinel: `accession == "IPR000001"`, name contains "Kringle".

## Citation

Blum M, et al. The InterPro protein families and domains database: 20 years on.
Nucleic Acids Res. 49:D344–D354 (2021).
