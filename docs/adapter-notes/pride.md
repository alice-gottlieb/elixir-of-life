# PRIDE adapter notes

**Consulted:** 2026-05-02 via PRIDE Archive API Guide and Swagger at ebi.ac.uk/pride/ws/archive/.

## Base URL

- REST API v2: `https://www.ebi.ac.uk/pride/ws/archive/v2`
- Interactive docs: `https://www.ebi.ac.uk/pride/ws/archive/`

## Endpoints used

- `GET /projects/{accession}` — single project by PXD accession (e.g. `PXD000001`).
- `GET /projects?keyword=...&pageSize=N&page=N` — keyword search over projects.
- `GET /projects/{accession}/files` — files associated with a project.

## Response format

HAL-style JSON. Single-project response is a flat dict. List responses have
`_embedded.compactprojects` (list of compact project summaries) and
`_links` for pagination.

Key fields per project: `accession`, `title`, `description`, `projectTags`,
`organisms`, `instruments`, `keywords`, `submissionDate`, `publicationDate`,
`references`, `numAssays`, `numProteins`, `numPeptides`.

## Pagination

`page` (0-based) and `pageSize` query parameters. `_links.next.href` when available.

## Rate limits / UA

- No documented hard limit. UA: `elixir-query/<version>`. No auth for public projects.

## Example request

`GET https://www.ebi.ac.uk/pride/ws/archive/v2/projects/PXD000001`

Response (excerpt):
```json
{
  "accession": "PXD000001",
  "title": "TMT spikes",
  "description": "...",
  "organisms": [{"name": "Homo sapiens", "taxid": 9606}],
  "numProteins": 3325,
  "numPeptides": 52847
}
```

Test sentinel: `PXD000001` → `accession == "PXD000001"`, `title` present.

## Bulk

`supports_bulk = False` — large proteomics data files are individual downloads
per project, not a single manageable dump. Metadata browsing is the scope here.

## Citation

Perez-Riverol Y, et al. The PRIDE database and related tools and resources in 2019.
Nucleic Acids Res. 47:D442–D450 (2019). Updated: PRIDE database at 20 years,
Nucleic Acids Res. 53:D543 (2025).
