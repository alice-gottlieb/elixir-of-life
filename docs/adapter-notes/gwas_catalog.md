# GWAS Catalog adapter notes

**Consulted:** 2026-05-02 via the GWAS Catalog REST API docs at ebi.ac.uk/gwas/rest/docs/api.

## Base URL

- REST API v2: `https://www.ebi.ac.uk/gwas/rest/api`
- API docs: `https://www.ebi.ac.uk/gwas/rest/docs/api`

## Endpoints used

- `GET /studies/{accession}` — single study by GWAS Catalog accession (e.g. `GCST000001`).
- `GET /studies?page=0&size=20` — paginated list of all studies.
- `GET /associations/{id}` — single association by internal ID.
- `GET /studies/{accession}/associations?page=0&size=100` — associations for a study.
- `GET /singleNucleotidePolymorphisms/{rsid}` — single SNP by rsID.
- `GET /efoTraits/{efo_id}` — EFO trait details.

## Response format

HAL-style JSON. List responses have `_embedded.<resource>`, `_links`, and
`page` (number, size, totalElements, totalPages). Single-resource responses
are flat dicts.

```json
{
  "_embedded": {"studies": [{...}, ...]},
  "_links": {"next": {"href": "..."}, "last": {...}},
  "page": {"size": 20, "totalElements": 4000, "totalPages": 200, "number": 0}
}
```

## Pagination

HAL `_links.next.href` gives the URL for the next page.  We follow it until
absent. Query params `page` (0-based) and `size` control the page.

## Rate limits / UA

- No hard limit; be polite. UA: `elixir-query/<version>`. No auth.

## Example request

`GET https://www.ebi.ac.uk/gwas/rest/api/studies/GCST000001`

Response (excerpt):
```json
{
  "accessionId": "GCST000001",
  "diseaseTrait": {"trait": "breast cancer"},
  "publicationInfo": {"pubmedId": "14973188", "title": "...", "journal": "Science"}
}
```

Test sentinel: `GCST000001` → `accessionId == "GCST000001"`,
`diseaseTrait.trait` contains "cancer" or "breast".

SNP `rs2981582` is a well-known FGFR2 breast-cancer hit; should return SNP metadata.

## Bulk

`supports_bulk = True`: GWAS Catalog ships a complete TSV dump at
`https://www.ebi.ac.uk/gwas/api/search/downloads/full` (≈120 MB). We stream
and materialise as Parquet.

## Citation

Sollis E, et al. The NHGRI-EBI GWAS Catalog: knowledgebase and deposition
resource. Nucleic Acids Res. 51:D977–D985 (2023).
