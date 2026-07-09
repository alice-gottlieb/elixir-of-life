# JASPAR adapter notes

**Consulted:** 2026-05-03 via jaspar.elixir.no/api/overview and jaspar2020.genereg.net/api/v1/docs/.

## Base URL

- REST API: `https://jaspar.genereg.net/api/v1` (also mirrored at `https://jaspar.elixir.no/api/v1`)
- Interactive docs: `https://jaspar.genereg.net/api/v1/docs/`

## Endpoints used

- `GET /matrix/{matrix_id}/?format=json` — single binding profile (e.g. `MA0002.1`).
- `GET /matrix/?format=json&page_size=20` — paginated list of all matrices.
- `GET /matrix/?tax_group=vertebrates&collection=CORE&page_size=N` — filtered list.
- `GET /species/?format=json` — list of species.
- `GET /collections/?format=json` — list of collections.
- `GET /tffm/{tffm_id}/` — TFFM model.

## Response format

Multiple formats: `json`, `jsonp`, `yaml`, `jaspar`, `transfac`, `pfm`, `meme`,
`bed`. We always request `format=json`.

Single matrix response (excerpt):
```json
{
  "matrix_id": "MA0002.1",
  "name": "RUNX1",
  "tax_group": ["vertebrates"],
  "tax_id": [9606, 10090, ...],
  "class": ["Runt-related factors"],
  "family": ["Runt domain factors"],
  "species": [{"tax_id": "9606", "name": "Homo sapiens"}],
  "pfm": {"A": [10, 12, ...], "C": [...], "G": [...], "T": [...]}
}
```

List response uses Django REST Framework pagination:
```json
{"count": 1956, "next": "https://...?page=2", "previous": null, "results": [...]}
```

## Pagination

`page` (1-based) and `page_size` query parameters. `next` URL when more pages exist.

## Rate limits / UA

- No documented hard limit. UA: `elixir-query/<version>`. No auth.

## Example request

`GET https://jaspar.genereg.net/api/v1/matrix/MA0002.1/?format=json`

Test sentinel: `MA0002.1` → `name == "RUNX1"`, `tax_group` includes
`"vertebrates"`. PFM has 4 rows (A, C, G, T).

## Bulk

`supports_bulk = True`: pages all matrices in a chosen `tax_group` /
`collection` and writes the metadata to Parquet. (Full PFM/PWM matrix dumps
are tens of MB and live behind the website's flat-file downloads.)

## Citation

Rauluseviciute I, et al. JASPAR 2024: 20th anniversary of the open-access
database of transcription factor binding profiles. Nucleic Acids Res.
52:D174–D182 (2024).
