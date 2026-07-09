# Europe PMC adapter notes

**Consulted:** 2026-05-02 via Europe PMC REST API docs at europepmc.org/RestfulWebService.

## Base URL

- REST API: `https://www.ebi.ac.uk/europepmc/webservices/rest`
- Swagger/docs: `https://europepmc.org/RestfulWebService`

## Endpoints used

- `GET /search` — full-text + field-specific search over PubMed/PMC/preprints/etc.
- `GET /article/{source}/{id}` — single article by external ID. `source` values:
  `MED` (PubMed), `PMC`, `PPR` (preprint), `CTX`, etc.

## Key query parameters (`/search`)

| param        | meaning                                                        |
|---|---|
| `query`      | Lucene-like: `insulin`, `TITLE:crispr`, `PMID:28209558`        |
| `format`     | `json` or `xml` — we request `json`                            |
| `resultType` | `lite` (id/title/authors) or `core` (full metadata)            |
| `pageSize`   | 1–1000; default 25                                             |
| `cursorMark` | Pagination cursor; first request `*`, next from `nextCursorMark` in response |

Response structure:
```json
{
  "hitCount": 123456,
  "nextCursorMark": "AoE=...",
  "resultList": {
    "result": [{...}, ...]
  }
}
```

## Response format preference

No native CSV/TSV — API returns JSON or XML. We accept JSON, flatten records into
a Polars DataFrame, and let `core.cache` persist CSV + Parquet.

## Pagination

`cursorMark`-based. First request: `cursorMark=*`. Each response carries
`nextCursorMark`; stop when that field equals the previous cursor (meaning the
last page has been received).

## Rate limits / UA

- No documented hard limit; 429 returned on abuse. `HttpClient` honours Retry-After.
- User-Agent: `elixir-query/<version>`.
- No authentication.

## Example request

`GET https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:28209558+AND+SRC:MED&resultType=lite&format=json&pageSize=1&cursorMark=*`

Expected fields in a `lite` result row:
`id`, `source`, `pmid`, `doi`, `title`, `authorString`, `journalTitle`, `pubYear`, `isOpenAccess`

Test sentinel: PMID 28209558 (Polaris-HGT, famous height GWAS paper) →
`title` contains "genome-wide", `pubYear` in range 2017–2018.

## Bulk

Europe PMC does not ship a single manageable bulk dump. `supports_bulk = False`.

## Citation

Europe PMC Consortium. Europe PMC: a full-text literature database for the life
sciences and platform for innovation. Nucleic Acids Res. 43:D1042–D1048 (2015).
