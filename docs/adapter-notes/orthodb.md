# OrthoDB adapter notes

**Consulted:** 2026-05-03 via ezlab.org/orthodb_v12_userguide.html.

## Base URL

- REST API v12: `https://data.orthodb.org/v12`

## Endpoints used

- `GET /search?query=...&level=...&take=N&skip=N` — text search returning a
  list of orthologous-group IDs.
- `GET /group?id={og_id}` — orthologous group details (e.g. `4977at9604`).
- `GET /genesearch?query=...` — gene-level search.
- `GET /genesearch?gid={ncbi_gene_id}` — gene lookup by NCBI gene ID.
- `GET /orthologs?id={og_id}` — genes in an OG.
- `GET /tab?id={og_id}` — tab-delimited gene data for an OG.

## OG identifier format

`<cluster_id>at<clade_taxid>` — e.g. `4977at9604` is a Hominidae-level
cluster, `5181at7742` is a Vertebrata-level cluster. Numeric clade taxa
correspond to NCBI taxonomy IDs (`9604` Hominidae, `33208` Metazoa,
`2759` Eukaryota, `9606` Homo sapiens).

## Response format

JSON. List endpoints return:
```json
{"url": "...", "data": ["4977at9604", "..."], "skip": 0, "take": 100, "count": 42}
```

`/group?id=...` returns a flat dict with the OG's metadata (name, level
taxid, gene count, evolutionary rate, copy-number stats, etc.).

## Pagination

`take` (page size, default 100, max 10 000) and `skip` (offset).

## Rate limits / UA

- No documented hard limit. UA: `elixir-query/<version>`. No auth.

## Example request

`GET https://data.orthodb.org/v12/group?id=4977at9604`

Response (excerpt):
```json
{
  "id": "4977at9604",
  "name": "Tumor protein P53",
  "level_name": "Hominidae",
  "level_taxid": 9604,
  "evolutionary_rate": 0.012,
  "gene_count": 6,
  "single_copy": true
}
```

Test sentinel: `4977at9604` exists; `level_taxid == 9604` (Hominidae).
A search for `"p53"` returns at least one OG.

## Bulk

`supports_bulk = False` — OrthoDB ships compressed flat-file releases at
`https://data.orthodb.org/v12/download/` (tens of GB) outside the JSON API
scope. Use `query(search='...')` with a high `take` parameter for
medium-scale aggregation.

## Citation

Kuznetsov D, et al. OrthoDB and BUSCO update: annotation of orthologs with
wider sampling of genomes. Nucleic Acids Res. 53:D516–D523 (2025).
