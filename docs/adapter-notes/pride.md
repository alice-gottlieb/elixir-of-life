# PRIDE adapter notes

**Consulted:** 2026-05-02

## Base URL

- REST API v2: `https://www.ebi.ac.uk/pride/ws/archive/v2`
- Swagger: https://www.ebi.ac.uk/pride/ws/archive/

## Endpoints used

- `GET /projects/{accession}` — single PRIDE project by PXD accession.
- `GET /projects?pageSize=100&page=0&q={keywords}` — paginated project search.
- `GET /projects/{accession}/files` — files associated with a project.
- `GET /spectra/{pxd_accession}` — spectra summary.

## Response format

JSON.  Single project response returns a flat object; list responses return
`{ "_embedded": { "compactprojects": [...] }, "_links": { "next": {...} }, "page": {...} }`.

Example project fields: `accession`, `title`, `submissionDate`, `publicationDate`,
`projectDescription`, `numProteins`, `numPeptides`, `numSpectra`, `organisms`,
`instruments`, `softwareList`.

## Pagination

`page` (0-indexed) + `pageSize` params.  Check `_links.next` or compare returned
count to pageSize to stop.

## Rate limits / auth

No auth for public data.

## Reproducible example

```
GET https://www.ebi.ac.uk/pride/ws/archive/v2/projects/PXD000001
```

Sentinel: `accession == "PXD000001"` (the first PRIDE project — a landmark dataset).

## Citation

Perez-Riverol Y, et al. The PRIDE database resources in 2022: a hub for
mass spectrometry-based proteomics evidences.
Nucleic Acids Res. 50:D543–D552 (2022).
