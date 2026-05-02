# Europe PMC adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API: `https://www.ebi.ac.uk/europepmc/webservices/rest`
- Swagger / interactive docs: https://europepmc.org/RestfulWebService

## Endpoints used

- `GET /search` — full-text & metadata search with cursor pagination.
  Key parameters: `query`, `resultType` (`lite` | `core`), `cursorMark`, `pageSize`, `format=json`.
- `GET /article/{source}/{id}` — single article by source + external ID (source MED = PubMed).

## Response formats

JSON (`format=json`), XML, DC.  We request JSON and persist via cache as
CSV + Parquet.

## Pagination

Cursor-mark based:
1. First request: `cursorMark=*`
2. Each response contains `nextCursorMark`; pass it as `cursorMark` in the next request.
3. Stop when `nextCursorMark == cursorMark` (no advance) or when result list is empty.

## Rate limits / auth

No auth required for public content.  Unofficial soft limit ~10 req/s.
Our `HttpClient` retries on 429.

## Key response fields (`resultType=core`)

```json
{
  "id": "30106370",
  "source": "MED",
  "pmid": "30106370",
  "pmcid": "PMC6137631",
  "doi": "10.1093/nar/gky1127",
  "title": "Europe PMC ...",
  "authorString": "Ferguson A, ...",
  "journalTitle": "Nucleic Acids Res.",
  "pubYear": "2019",
  "abstractText": "...",
  "citedByCount": 42,
  "isOpenAccess": "Y"
}
```

## Reproducible example

```
GET https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:30106370%20AND%20SRC:MED&resultType=core&cursorMark=*&pageSize=1&format=json
```

Sentinel: `pmid == "30106370"`, `doi == "10.1093/nar/gky1127"`.

## Citation

Ferguson A, et al. Europe PMC: a full-text literature database for the life sciences
and platform for innovation. Nucleic Acids Res. 47:D1155–D1162 (2019).
