# Reactome adapter notes

**Consulted:** 2026-04-27 via the Reactome ContentService docs.

## Base URL

- ContentService REST API: `https://reactome.org/ContentService`
- Swagger: `https://reactome.org/ContentService/`

## Endpoints used

- `GET /data/query/{id}` — generic lookup; works for pathways, reactions,
  events, species, and stable identifiers like `R-HSA-69620`.
- `GET /data/pathway/{id}/containedEvents` — the events inside a pathway.
- `GET /data/pathways/top/{species}` — top-level pathways for a species
  (e.g. `9606` for *Homo sapiens*).
- `GET /data/participants/{id}` — participating physical entities of an event.

## Response formats

JSON only. We negotiate via `Accept: application/json`. There is no native
CSV/TSV export; we flatten one level into a Polars DataFrame and let
`core.cache` persist CSV+Parquet.

## Pagination

None of the endpoints used here paginate — each returns a single record or a
bounded list.

## Rate limits / UA

- No documented hard rate limit; ContentService returns 429 on excess. Our
  `HttpClient` honours `Retry-After`.
- A descriptive User-Agent is requested. We send `elixir-query/<version>`.
- No authentication.

## Example request

`GET https://reactome.org/ContentService/data/query/R-HSA-69620`
`Accept: application/json`

Response (excerpt):
```json
{
  "dbId": 69620,
  "stId": "R-HSA-69620",
  "displayName": "Cell Cycle Checkpoints",
  "schemaClass": "Pathway",
  "speciesName": "Homo sapiens",
  "isInDisease": false,
  "isInferred": false,
  "name": ["Cell Cycle Checkpoints"]
}
```

Test sentinel: `R-HSA-69620` has `displayName == "Cell Cycle Checkpoints"`,
`speciesName == "Homo sapiens"`, `schemaClass == "Pathway"`.

## Bulk dump

Reactome ships flat-file pathway exports (TSV) at
`https://reactome.org/download/current/`. We expose a bulk path that fetches
`ReactomePathways.txt` (3 columns: `stId`, `displayName`, `speciesName`) and
materialises Parquet.

## Citation

Milacic M, et al. The Reactome Pathway Knowledgebase 2024.
Nucleic Acids Res. 52:D672–D678 (2024).
