# ENA (European Nucleotide Archive) adapter notes

**Consulted:** 2026-05-02 via ENA Portal API docs at ena-docs.readthedocs.io.

## Base URLs

- ENA Portal API: `https://www.ebi.ac.uk/ena/portal/api`
  - `GET /search` — main search endpoint
  - `GET /returnFields?result=<result_type>` — discover available fields
- ENA Browser API (XML): `https://www.ebi.ac.uk/ena/browser/api/xml/{accession}`
- FASTA fetch: `https://www.ebi.ac.uk/ena/browser/api/fasta/{accession}`

## Key result types

`sequence`, `read_run`, `study`, `sample`, `experiment`, `analysis`,
`read_experiment`, `wgs_set`, `noncoding` (and more).

## Key query parameters (`/search`)

| param    | meaning                                                             |
|---|---|
| `query`  | Lucene-like filter: `tax_eq(9606)`, `study_accession="ERP000001"` |
| `result` | Result type (required); e.g. `read_run`, `sample`, `study`         |
| `fields` | Comma-joined field names; omit for defaults (accession+description) |
| `format` | `tsv` (default, preferred) or `json`                               |
| `limit`  | Max rows (server max ~100000); 0 = unlimited                       |
| `offset` | Pagination offset                                                   |

## Response format preference

The API natively returns **TSV** when `format=tsv`, which is the project-preferred
format for persisting text. We accept TSV over the wire and normalise via
`core.io.read_tsv`; `core.cache.put_query` then writes CSV + Parquet.

## Pagination

`limit` + `offset`. We page through by incrementing offset in page-size steps.
When a page returns fewer rows than requested, we've reached the end.

## Rate limits / UA

- No documented hard limit; behaves well up to hundreds of requests/minute.
- No authentication required for public data.
- User-Agent: `elixir-query/<version>`.

## Example request

`GET https://www.ebi.ac.uk/ena/portal/api/search?query=study_accession%3DERP000001&result=read_run&fields=accession,study_accession,sample_accession,scientific_name&format=tsv&limit=5&offset=0`

Response (excerpt, TSV):
```
accession\tstudy_accession\tsample_accession\tscientific_name
ERR000001\tERP000001\tERS000001\tHomo sapiens
```

Test sentinel: study `ERP000001` returns at least one `read_run` row with
`study_accession == "ERP000001"`.

## Bulk

`supports_bulk = True`: for large result sets the portal API itself is the bulk
path — stream with large `limit` (or `limit=0`) and persist as Parquet via
`bulk_paths`. Also, pre-built flat-file releases are at
`https://ftp.ebi.ac.uk/pub/databases/ena/`.

## Citation

Sayers EW, et al. Database resources of the National Center for Biotechnology
Information. Nucleic Acids Res. 50:D20–D26 (2022).
(ENA is the European mirror of INSDC; the ENA citation is
Harrison PW, et al. Nucleic Acids Res. 2021.)
