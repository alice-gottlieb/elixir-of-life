# GWAS Catalog adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API: `https://www.ebi.ac.uk/gwas/rest/api`
- API docs: https://www.ebi.ac.uk/gwas/rest/docs/api

## Endpoints used

- `GET /studies/{accession}` — single study by GWAS Catalog accession (e.g. `GCST000001`).
- `GET /associations/search/findByStudyAccession?studyAccession={accession}` — all
  associations for a study; HAL-paginated.
- `GET /singleNucleotidePolymorphisms/{rsid}` — SNP metadata.
- `GET /singleNucleotidePolymorphisms/{rsid}/associations` — associations for a SNP.

## Response format

HAL JSON (Hypertext Application Language).  Paginated lists use `_embedded` for
results and `_links.next.href` for the next page URL.

```json
{
  "_embedded": {
    "associations": [{ "pvalueMantissa": 5, "pvalueExponent": -24, ... }]
  },
  "_links": { "next": {"href": "..."}, "self": {"href": "..."} },
  "page": { "size": 20, "totalElements": 42, "number": 0 }
}
```

## Pagination

Follow `_links.next.href` (when present) until absent.  The adapter tracks this
via a simple `while next_url` loop.

## Rate limits / auth

No auth for public data.  Soft limit; retry on 429.

## Reproducible example

```
GET https://www.ebi.ac.uk/gwas/rest/api/singleNucleotidePolymorphisms/rs7903146
```

Sentinel: `rsId == "rs7903146"` (TCF7L2, the most replicated T2D GWAS variant).

## Citation

Sollis E, et al. The NHGRI-EBI GWAS Catalog: knowledgebase and deposition
resource. Nucleic Acids Res. 51:D977–D985 (2023).
