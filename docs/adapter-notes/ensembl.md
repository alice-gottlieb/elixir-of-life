# Ensembl adapter notes

**Consulted:** 2026-04-27 via Ensembl REST API documentation (https://rest.ensembl.org).

## Base URLs

- REST API: `https://rest.ensembl.org`
  - `/lookup/id/{id}` — single feature lookup by stable ID (genes, transcripts, exons, etc.)
  - `/lookup/symbol/{species}/{symbol}` — lookup by gene symbol
  - `/overlap/region/{species}/{region}` — features overlapping a genomic region
  - `/overlap/id/{id}` — features overlapping a feature
  - `/sequence/id/{id}` — sequence retrieval
  - `/xrefs/id/{id}` — cross-references
  - `/info/species` — list of species available
- FTP bulk dumps: `https://ftp.ensembl.org/pub/current_gtf/<species>/` (GTF) and
  `https://ftp.ensembl.org/pub/current_fasta/<species>/` (FASTA).

## Response formats

The REST API negotiates via the `Accept` header. Supported formats include
`application/json`, `text/xml`, `text/x-gff3`, `text/x-fasta`, `application/vnd.ensembl.v1+json`.
We request JSON (the canonical form) and flatten one level.

There is **no native CSV/TSV** for the REST endpoints — we accept JSON, build
records, then persist via `core.cache` as CSV + Parquet.

## Pagination

The Ensembl REST API does **not** paginate; each endpoint either returns a single
record (lookup) or a complete list (overlap). Limits are enforced server-side
(typical max body 10 MB; over that the server returns 400). Bulk needs are met
via FTP GTF/FASTA dumps.

## Rate limits / UA

- Soft rate limit: ~15 requests/sec per IP. Server returns `X-RateLimit-Remaining`
  and `X-RateLimit-Reset` headers; HTTP 429 on excess. Our `HttpClient` honours
  `Retry-After`.
- A descriptive User-Agent is requested. We send `elixir-query/<version>`.
- No authentication required.

## Example request

`GET https://rest.ensembl.org/lookup/id/ENSG00000139618?expand=0`
`Accept: application/json`

Response (truncated):
```json
{
  "id": "ENSG00000139618",
  "display_name": "BRCA2",
  "biotype": "protein_coding",
  "species": "homo_sapiens",
  "assembly_name": "GRCh38",
  "seq_region_name": "13",
  "start": 32315474,
  "end": 32400266,
  "strand": 1,
  "object_type": "Gene"
}
```

Test sentinel: `species == "homo_sapiens"` and `biotype == "protein_coding"`.

## Bulk dump shape

Per-species GTF gene annotation file:
`https://ftp.ensembl.org/pub/current_gtf/homo_sapiens/Homo_sapiens.GRCh38.<release>.gtf.gz`

Each row is a 9-column GTF feature; we parse to a DataFrame keeping `seqname,
source, feature, start, end, score, strand, frame, attributes` and persist
Parquet.

## Citation

Harrison PW, et al. Ensembl 2024. Nucleic Acids Res. 52(D1):D891–D899 (2024).
