# Cellosaurus adapter notes

**Consulted:** 2026-05-02 via api.cellosaurus.org quick start and api-methods docs.

## Base URL

- REST API: `https://api.cellosaurus.org`
- Quick start: `https://api.cellosaurus.org/`
- Method reference: `https://api.cellosaurus.org/api-methods`
- Field reference: `https://api.cellosaurus.org/api-fields`

## Endpoints used

- `GET /cell-line/{accession}` — single cell line by Cellosaurus accession
  (format `CVCL_XXXX`, e.g. `CVCL_0030` = HeLa).
- `GET /cell-line/{accession}?fields=id,ac,sy,ca,sx,ox,di` — specific fields.
- `GET /search/cell-line?q={term}&rows=N&start=N` — search over all text fields.

## Response format

JSON. Single cell-line:
```json
{
  "Cellosaurus": {
    "cell-line-list": [
      {
        "category": "Cancer cell line",
        "sex": "Female",
        "species-of-origin": [{"nomenclature": "Scientific name", "value": "Homo sapiens"}],
        "accession": [{"type": "primary", "value": "CVCL_0030"}],
        "name": [{"type": "identifier", "value": "HeLa"}],
        "disease": [{"accession": "NCIt:C4029", "value": "Endocervical adenocarcinoma"}]
      }
    ]
  }
}
```

Search response: `{"Cellosaurus": {"cell-line-list": [...]}, "total-results": N}`.

## Pagination (search)

`rows` (page size) and `start` (offset). `total-results` in response gives total count.

## Rate limits / UA

- No documented hard limit. UA: `elixir-query/<version>`. No auth.

## Example request

`GET https://api.cellosaurus.org/cell-line/CVCL_0030`

Test sentinel: `CVCL_0030` = HeLa → identifier `"HeLa"`, category `"Cancer cell line"`, 
species `"Homo sapiens"`.

## Bulk

`supports_bulk = True`: full text file at
`https://ftp.expasy.org/databases/cellosaurus/cellosaurus.txt` (~70 MB flat text).
We expose this as a streaming download for users who want the raw file. Parsing
the complex flat-file format is non-trivial; the adapter streams to a raw file
and returns a minimal LazyFrame with accession + name pairs extracted from the
identifier lines.

## Citation

Bairoch A. The Cellosaurus, a cell-line knowledge resource.
J. Biomol. Tech. 29:25–38 (2018).
