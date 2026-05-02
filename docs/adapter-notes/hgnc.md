# HGNC adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API: `https://rest.genenames.org`

## Endpoints used

- `GET /fetch/symbol/{symbol}` — fetch full record by HGNC symbol (e.g. `EGFR`).
- `GET /fetch/hgnc_id/{hgnc_id}` — fetch by numeric or full HGNC ID (e.g. `3236` or `HGNC:3236`).
- `GET /search/symbol/{symbol}` — lightweight search; returns hgnc_id + symbol + score only.
- `GET /search/{field}/{value}` — search by any indexed field.

## Response format

JSON via `Accept: application/json`.

```json
{
  "responseHeader": {"status": 0, "QTime": 5},
  "response": {
    "numFound": 1,
    "docs": [{
      "hgnc_id": "HGNC:3236",
      "symbol": "EGFR",
      "name": "epidermal growth factor receptor",
      "locus_group": "protein-coding gene",
      "locus_type": "gene with protein product",
      "status": "Approved",
      "location": "7p11.2",
      "entrez_id": "1956",
      "ensembl_gene_id": "ENSG00000146648",
      "uniprot_ids": ["P00533"]
    }]
  }
}
```

## Pagination

No server-side pagination — all results returned at once (up to the full gene
index, typically ≤10 results for a focused search).

## Rate limits / auth

No auth required.  Public service at genenames.org.

## Reproducible example

```
GET https://rest.genenames.org/fetch/symbol/EGFR
Accept: application/json
```

Sentinel: `symbol == "EGFR"`, `hgnc_id == "HGNC:3236"`.

## Citation

Tweedie S, et al. Genenames.org: the HGNC resources in 2021.
Nucleic Acids Res. 49:D939–D946 (2021).
