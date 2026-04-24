# UniProt adapter notes

**Consulted:** 2026-04-24 via UniProt help and API documentation pages.

## Base URLs

- REST search: `https://rest.uniprot.org/uniprotkb/search`
- Single-entry fetch: `https://rest.uniprot.org/uniprotkb/{accession}` (append `?format=tsv` or `.tsv`)
- FTP bulk dumps: `https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/`
  - Swiss-Prot: `uniprot_sprot.dat.gz` and `uniprot_sprot.xml.gz`
  - TrEMBL:    `uniprot_trembl.dat.gz`

## Query parameters (REST search)

| param    | meaning                                                                 |
|----------|-------------------------------------------------------------------------|
| `query`  | Lucene-like query: `insulin AND reviewed:true`, `organism_id:9606`, ... |
| `fields` | Comma-separated column list: `accession,id,organism_id,gene_names,length` |
| `format` | `tsv`, `json`, `xml`, `fasta`, `list`, `gff`, ...                        |
| `size`   | Page size (default 25, **max 500**)                                      |

## Pagination

- Returns `Link: <url>; rel="next"` header when more pages exist. Follow that URL to paginate.
- `X-Total-Results` header reports total hit count.
- `X-UniProt-Release` + `X-UniProt-Release-Date` identify the data release.

## Response formats (tabular preference)

UniProt offers **JSON, XML, TSV, FASTA, List, GFF, RDF** — no native CSV. Per the
project-wide preference we accept TSV over the wire (typed columns, smallest text
payload) and persist the cached DataFrame as CSV + Parquet via `core.cache`.

## Rate limits / UA policy

- No documented hard rate limit for REST search; 429 is returned on abuse. Our
  `HttpClient` honours `Retry-After`.
- UniProt requests a descriptive User-Agent — we send `elixir-query/<version>`.

## Example request + expected payload

`GET https://rest.uniprot.org/uniprotkb/P00533?format=tsv&fields=accession,organism_id,gene_names,length`

Response (header + one row):

```
Entry	Organism (ID)	Gene Names	Length
P00533	9606	EGFR ERBB ERBB1 HER1	1210
```

Test sentinel: P00533 must have `organism_id == 9606` (human) and `length == 1210`.

## Bulk dump shape

`uniprot_sprot.dat.gz` is a flat-file EMBL-style format, not tabular — we do NOT
try to parse it as CSV/TSV. For a tabular bulk path we stream a large TSV search
(`reviewed:true`) with all useful fields, write to Parquet, and return a LazyFrame.

## Citation

The UniProt Consortium. UniProt: the Universal Protein Knowledgebase in 2025.
Nucleic Acids Res. 53:D609–D617 (2025).
