# InterPro adapter notes

**Consulted:** 2026-05-02 via interpro7-api GitHub README and InterPro API docs.

## Base URL

- REST API: `https://www.ebi.ac.uk/interpro/api/`

## Key endpoints

- `GET /entry/interpro/{accession}` — single InterPro entry (e.g. `IPR001680`).
- `GET /entry/pfam/{accession}` — single Pfam entry (e.g. `PF00001`).
- `GET /entry/all/` — list all entries (paginated).
- `GET /entry/{db}/` — list entries from one member DB (`interpro`, `pfam`,
  `smart`, `prints`, `prosite`, `cathgene3d`, `tigrfams`, etc.).
- `GET /protein/uniprot/{accession}/entry/interpro/` — entries annotating a protein.
- `GET /structure/pdb/{pdb_id}/entry/interpro/` — entries annotating a PDB structure.
- `GET /taxonomy/uniprot/{taxon_id}/entry/interpro/` — entries in a taxon.

## Response format

JSON only. Each list response has shape:
```json
{"count": N, "next": "https://...", "previous": null, "results": [{...}, ...]}
```

Single-entry responses are a single metadata dict. We flatten one level into
a Polars DataFrame and let `core.cache` persist CSV + Parquet.

## Pagination

`next` field in every list response. `None` when on the last page. We follow
`next` links until `None`. Default page size is 20.

## Rate limits / UA

- No documented hard limit; server returns 429 on excess. Our `HttpClient`
  honours `Retry-After`.
- User-Agent: `elixir-query/<version>`.
- No authentication.

## Example request

`GET https://www.ebi.ac.uk/interpro/api/entry/interpro/IPR001680`
`Accept: application/json`

Response (excerpt):
```json
{
  "metadata": {
    "accession": "IPR001680",
    "name": {"name": "WD40 repeat", "short": "WD_repeat"},
    "source_database": "interpro",
    "type": "Repeat",
    "integrated": null
  }
}
```

Test sentinel: `IPR001680` is the WD40/G-beta repeat — `type == "Repeat"` and
`accession == "IPR001680"`.

## Bulk

InterPro ships flat-file releases at
`https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/`. We implement
`supports_bulk = True` by streaming from the API `/entry/{db}/` paginated list
(manageable with limit/offset) and writing Parquet.

## Citation

Paysan-Lafosse T, et al. InterPro in 2022. Nucleic Acids Res. 51:D418–D427 (2023).
