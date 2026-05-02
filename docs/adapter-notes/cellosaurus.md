# Cellosaurus adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API: `https://api.cellosaurus.org`
- Quick start: https://api.cellosaurus.org/

## Endpoints used

- `GET /cell-line/{accession}?format=json` — single cell line by CVCL accession.
- `GET /search/cell-line?q={query}&format=json&limit=50&offset=0` — full-text search.

## Response format

JSON (`format=json`), XML, TSV, TXT.  We request JSON.

Key fields in a cell line record:
- `Ac` — primary accession (e.g. CVCL_0004)
- `Id` — recommended name  
- `Category` — cell line category (e.g. "Cancer cell line")
- `Ox` — organism/species list
- `Di` — disease association list  
- `Sy` — synonym list
- `Age`, `Sex`, `Dt` (creation/update dates)

## Pagination

`limit` + `offset` for `/search`; stop when returned count < limit.

## Rate limits / auth

No auth required.

## Reproducible example

```
GET https://api.cellosaurus.org/cell-line/CVCL_0004?format=json
```

Sentinel: `accession == "CVCL_0004"`, name contains "HeLa".

## Citation

Bairoch A. The Cellosaurus, a cell-line knowledge resource.
J. Proteome Res. 17:4408–4417 (2018).
