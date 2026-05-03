# HGNC adapter notes

**Consulted:** 2026-05-02 via genenames.org/help/rest and rest.genenames.org/info.

## Base URL

- REST API: `https://rest.genenames.org`

## Endpoints used

- `GET /info` — service metadata (last update, total docs, searchable/stored fields).
- `GET /fetch/{field}/{value}` — exact fetch:
  - `/fetch/symbol/BRCA2` — by approved gene symbol
  - `/fetch/hgnc_id/HGNC:1101` — by HGNC ID
  - `/fetch/uniprot_ids/P51587` — by UniProt accession
  - `/fetch/entrez_id/675` — by NCBI Entrez Gene ID
  - `/fetch/ensembl_gene_id/ENSG00000139618` — by Ensembl gene ID
- `GET /search/{query}` — searches across all searchable fields.
- `GET /search/{field}/{value}` — field-specific search.

## Response format

JSON (with `Accept: application/json`) or XML. We always request JSON.

Response envelope:
```json
{
  "responseHeader": {"status": 0, "QTime": 4},
  "response": {"numFound": 1, "docs": [{...}]}
}
```

Key fields per document:
`hgnc_id`, `symbol`, `name`, `locus_group`, `locus_type`, `status`,
`location`, `entrez_id`, `ensembl_gene_id`, `uniprot_ids`, `omim_id`,
`alias_symbol`, `prev_symbol`, `gene_group`, `gene_group_id`.

## Pagination

No pagination for `/fetch`; `/search` returns up to the full result set.
For large searches, `numFound` is always returned in `response`.

## Rate limits / UA

- No hard rate limit; be courteous. UA: `elixir-query/<version>`.
- No authentication.

## Example request

`GET https://rest.genenames.org/fetch/symbol/BRCA2`
`Accept: application/json`

Response (excerpt):
```json
{
  "response": {
    "numFound": 1,
    "docs": [{"hgnc_id":"HGNC:1101","symbol":"BRCA2","name":"BRCA2 DNA repair associated","locus_type":"gene with protein product","location":"13q12.3","entrez_id":"675"}]
  }
}
```

Test sentinel: `symbol=BRCA2` → `hgnc_id == "HGNC:1101"`, `locus_type == "gene with protein product"`.

## Bulk

HGNC ships a monthly TSV dump at `https://ftp.ebi.ac.uk/pub/databases/genenames/hgnc/tsv/hgnc_complete_set.txt`
(≈4 MB). We implement `bulk()` as a streaming FTP fetch.

## Citation

Tweedie S, et al. Genenames.org: the HGNC and VGNC resources in 2021.
Nucleic Acids Res. 49:D939–D946 (2021).
