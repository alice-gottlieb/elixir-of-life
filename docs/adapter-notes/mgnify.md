# MGnify adapter notes

**Consulted:** 2026-05-03 via emg-docs.readthedocs.io and ebi.ac.uk/metagenomics/api/docs.

## Base URL

- REST API: `https://www.ebi.ac.uk/metagenomics/api/latest`
- Interactive docs: `https://www.ebi.ac.uk/metagenomics/api/docs/`

## Endpoints used

- `GET /studies/{accession}` — single study by ENA-style accession (e.g. `ERP009004`).
- `GET /studies` — paginated list of all studies.
- `GET /studies/{accession}/samples` — samples in a study.
- `GET /samples/{accession}` — single sample.
- `GET /runs/{accession}` — single run.
- `GET /biomes/{lineage}` — biome metadata (e.g. `root:Host-associated:Human`).

## Response format

[JSON:API](https://jsonapi.org/) — every response has shape:

```json
{
  "data": {"type": "studies", "id": "ERP009004", "attributes": {...}, "relationships": {...}},
  "links": {"first": "...", "last": "...", "next": "...", "prev": "..."},
  "meta": {"pagination": {"page": 1, "pages": 100, "count": 5000}}
}
```

For lists, `data` is a list of typed resource dicts; for singletons it's one dict.

## Pagination

Standard JSON:API pagination via `links.next`. Query params `page` and `page_size`
(default 25, max 250).

## Rate limits / UA

- No documented hard limit. UA: `elixir-query/<version>`. No auth.

## Example request

`GET https://www.ebi.ac.uk/metagenomics/api/latest/studies/ERP009004`

Response (excerpt):
```json
{
  "data": {
    "type": "studies",
    "id": "MGYS00000410",
    "attributes": {
      "accession": "MGYS00000410",
      "secondary-accession": "ERP009004",
      "study-name": "...",
      "samples-count": 42
    }
  }
}
```

Test sentinel: `ERP009004` → `data.type == "studies"`, `attributes.accession`
matches a known MGnify accession (the API returns the MGnify-style ID).

## Bulk

`supports_bulk = False` — large per-study analysis files live behind FTP and
have varying schemas; v1 focuses on metadata browsing through the API.

## Citation

Richardson L, et al. MGnify: the microbiome sequence data analysis resource in 2023.
Nucleic Acids Res. 51:D753–D759 (2023).
