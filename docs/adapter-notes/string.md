# STRING adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API: `https://string-db.org/api`

## Endpoints used

- `GET /tsv/get_string_ids?identifiers={name}&species={taxon}&caller_identity={app}` —
  resolve protein name → STRING ID.
- `GET /tsv/network?identifiers={protein_list}&species={taxon}&caller_identity={app}` —
  protein–protein interaction network for a set of proteins.
- `GET /tsv/interaction_partners?identifiers={protein}&species={taxon}&limit=10&caller_identity={app}` —
  interaction partners for one protein.
- `GET /tsv/enrichment?identifiers={list}&species={taxon}&caller_identity={app}` —
  functional enrichment.

## Response format

TSV (tab-separated).  We use `read_tsv()` and persist as CSV+Parquet.

Network TSV columns: `stringId_A`, `stringId_B`, `preferredName_A`,
`preferredName_B`, `ncbiTaxonId`, `score`, `nscore`, `fscore`, `pscore`,
`ascore`, `escore`, `dscore`, `tscore`.

## Pagination

No pagination — specify `limit` param for `interaction_partners`.

## Rate limits / auth

No auth required.  Caller identity (`caller_identity`) string is encouraged for
responsible use.

## Reproducible example

```
GET https://string-db.org/api/tsv/interaction_partners?identifiers=TP53&species=9606&limit=5&caller_identity=elixir-query
```

Sentinel: `preferredName_A == "TP53"` in at least one returned row.

## Citation

Szklarczyk D, et al. The STRING database in 2023: protein–protein association
networks and functional enrichment analyses for any sequenced genome of interest.
Nucleic Acids Res. 51:D638–D646 (2023).
