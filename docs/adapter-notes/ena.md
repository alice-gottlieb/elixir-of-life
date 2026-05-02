# ENA adapter notes

**Consulted:** 2026-05-02

## Base URL

- Portal API: `https://www.ebi.ac.uk/ena/portal/api`
- Swagger docs: https://www.ebi.ac.uk/ena/portal/api/swagger-ui/index.html

## Endpoints used

- `GET /search` — search across ENA result types (sequence, study, experiment, run, sample).
  Parameters: `result`, `query`, `fields`, `format=tsv`, `limit`, `offset`.
- `GET /returnFields?result={type}` — discover available fields for a result type.

## Response formats

TSV (default) and JSON.  We request TSV and parse with `read_tsv()`.

## Pagination

Offset/limit based:
- `limit` (default 100 000 server-side; set explicitly)
- `offset` (0-indexed)
- Stop when a page returns fewer rows than requested.

## Rate limits / auth

No auth for public data.  Unofficial limit ~10 req/s.

## Available result types

`sequence`, `study`, `experiment`, `run`, `sample`, `analysis`, `wgs_set`,
`tls_set`, `coding_release`, `noncoding_release`, `assembly`, `genome`.

## Default fields for `sequence`

`accession`, `description`

## Extended fields used by adapter

`accession`, `description`, `scientific_name`, `tax_id`, `sequence_length`,
`base_count`, `mol_type`

## Reproducible example

```
GET https://www.ebi.ac.uk/ena/portal/api/search?result=sequence&query=accession%3DAB000001&fields=accession%2Cdescription%2Cscientific_name%2Ctax_id%2Csequence_length&format=tsv&limit=1
```

Sentinel: `accession == "AB000001"`.

## Citation

Burgin J, et al. The European Nucleotide Archive in 2022.
Nucleic Acids Res. 51:D121–D125 (2023).
