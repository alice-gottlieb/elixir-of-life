# OMA adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API: `https://omabrowser.org/api`
- Interactive docs: https://omabrowser.org/api/docs

## Endpoints used

- `GET /protein/{entry_id}/` — protein metadata by OMA ID (e.g. `HUMAN17133`)
  or UniProt accession (e.g. `P00533`).
- `GET /protein/{entry_id}/orthologs/` — pairwise orthologs for a protein.
- `GET /group/{oma_group_id}/` — OMA group metadata.
- `GET /group/{oma_group_id}/members/` — all members of an OMA group.

## Response format

JSON.  Protein response fields: `entry_nr`, `omaid`, `canonicalid`, `sequence_md5`,
`oma_group`, `sequence`, `locus`, `genome` (nested).

Orthologs endpoint returns a list of ortholog objects with `entry_1`, `entry_2`,
and `rel_type` fields.

## Pagination

Group members and orthologs: `page` + `per_page` parameters.
Stop when response list is shorter than `per_page`.

## Rate limits / auth

No auth required.

## Reproducible example

```
GET https://omabrowser.org/api/protein/P00533/
```

Sentinel: `canonicalid == "P00533"` or `omaid` contains "HUMAN".

## Citation

Altenhoff AM, et al. OMA orthology in 2021: website overhaul, conserved isoforms,
ancestral gene order and more. Nucleic Acids Res. 49:D373–D379 (2021).
