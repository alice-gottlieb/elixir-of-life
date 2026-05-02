# MGnify adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API v1: `https://www.ebi.ac.uk/metagenomics/api/v1`
- Docs: https://docs.mgnify.org/src/docs/api.html

## Endpoints used

- `GET /studies/{accession}` — single study metadata (JSON:API resource).
- `GET /studies/?ordering=-last_update&page=1&page_size=50` — paginated study list.
- `GET /samples/{accession}` — single sample.
- `GET /runs/?study_accession={accession}` — runs for a study.

## Response format

JSON:API (`application/vnd.api+json`).  Resource objects live under `data`
(single) or `data[]` (collection).  Attributes are under `data.attributes`.

```json
{
  "data": {
    "type": "studies",
    "id": "MGYS00001598",
    "attributes": {
      "accession": "MGYS00001598",
      "secondary-accession": "ERP009703",
      "study-name": "ERP009703: ...",
      "bioproject": "PRJEB9071",
      ...
    }
  }
}
```

## Pagination

JSON:API links style: `links.next` URL in response body.

## Rate limits / auth

No auth for public data.

## Reproducible example

```
GET https://www.ebi.ac.uk/metagenomics/api/v1/studies/MGYS00001598
```

Sentinel: `id == "MGYS00001598"`.

## Citation

Richardson L, et al. MGnify: the microbiome sequence data analysis resource
in 2023. Nucleic Acids Res. 51:D753–D759 (2023).
