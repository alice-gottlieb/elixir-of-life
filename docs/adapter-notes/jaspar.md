# JASPAR adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API v1: `https://jaspar.elixir.no/api/v1`
- Docs / Swagger: https://jaspar.elixir.no/api/v1/docs/

## Endpoints used

- `GET /matrix/{id}/` — single TF binding matrix (profile) by ID (e.g. `MA0139.1`).
- `GET /matrix/?collection=CORE&format=json&page=1&page_size=50&tax_group=vertebrates` —
  paginated list of matrices with optional filters.

## Response format

JSON.  Paginated list response:
```json
{
  "count": 2346,
  "next": "https://jaspar.elixir.no/api/v1/matrix/?page=2",
  "previous": null,
  "results": [{
    "matrix_id": "MA0139.1",
    "name": "CTCF",
    "collection": "CORE",
    "tax_group": "vertebrates",
    "class": ["C2H2 zinc finger factors"],
    "family": ["CTCF-like"],
    "species": [{"name": "Homo sapiens", "tax_id": 9606}],
    "pfm": {"A": [...], "C": [...], "G": [...], "T": [...]}
  }]
}
```

## Pagination

Standard DRF pagination: `next` URL in response body.

## Rate limits / auth

No auth required.

## Reproducible example

```
GET https://jaspar.elixir.no/api/v1/matrix/MA0139.1/
```

Sentinel: `matrix_id == "MA0139.1"`, `name == "CTCF"`.

## Citation

Castro-Mondragon JA, et al. JASPAR 2022: the 9th release of the open-access
database of transcription factor binding profiles.
Nucleic Acids Res. 50:D165–D173 (2022).
