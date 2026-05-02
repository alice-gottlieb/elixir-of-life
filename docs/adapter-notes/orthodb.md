# OrthoDB adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API v11: `https://data.orthodb.org/v11.0`
- User guide: https://www.ezlab.org/orthodb_v11_userguide.html

## Endpoints used

- `GET /search?query={term}&take=100&skip=0` — search for orthologous groups (OGs)
  matching a gene name, protein accession, or keyword.  Returns OG IDs.
- `GET /group?id={og_id}` — detailed info for a single OG.
- `GET /members?id={og_id}` — gene members of an OG.

## Response format

JSON.

Search response:
```json
{
  "message": "ok",
  "query": "TP53",
  "count": 12,
  "data": ["9606_0:002c41", ...],
  "bigdata": [{"id": "...", "name": "...", "level_taxid": 9606, ...}, ...]
}
```

## Pagination

`skip` + `take` offset/limit style.

## Rate limits / auth

No auth required.

## Reproducible example

```
GET https://data.orthodb.org/v11.0/search?query=TP53&take=5
```

Sentinel: `count > 0` and OG IDs returned in `data`.

## Citation

Kuznetsov D, et al. OrthoDB v11: annotation of orthologs in the widest
sampling of organismal diversity. Nucleic Acids Res. 51:D445–D451 (2023).
