# OMA (Orthologous Matrix) adapter notes

**Consulted:** 2026-05-03 via omabrowser.org/api/docs and the OMA REST API paper.

## Base URL

- REST API: `https://omabrowser.org/api`
- Interactive docs: `https://omabrowser.org/api/docs`

## Endpoints used

- `GET /protein/{entry_id}/` — single protein by OMA entry ID, UniProt accession,
  or species-prefixed name (e.g. `YEAST00012`, `P53_HUMAN`, `Q9Y6Q9`).
- `GET /protein/{entry_id}/orthologs/` — pairwise orthologs (paginated).
- `GET /protein/{entry_id}/hog/` — hierarchical orthologous group for a protein.
- `GET /genome/{taxon_id}/` — genome record (e.g. `559292` = *S. cerevisiae* S288C).
- `GET /hog/{hog_id}/members/` — members of a HOG.

## Response format

JSON only. Single records are dicts; lists are wrapped in DRF-style pagination
envelopes with `count`, `next`, `previous`, `results`.

Pairwise orthologs response (excerpt):
```json
{
  "count": 350,
  "next": "https://omabrowser.org/api/protein/YEAST00012/orthologs/?page=2",
  "results": [
    {
      "entry_nr": 12345,
      "omaid": "HUMAN12345",
      "canonicalid": "Q9Y...",
      "rel_type": "1:1",
      "distance": 1.23,
      "score": 999
    }
  ]
}
```

## Pagination

`page` (1-based) and `per_page` query params; default 100. `next` URL when
more pages exist.

## Rate limits / UA

- No documented hard limit. UA: `elixir-query/<version>`. No auth.

## Example request

`GET https://omabrowser.org/api/protein/YEAST00012/`

Response (excerpt):
```json
{
  "entry_nr": 12,
  "omaid": "YEAST00012",
  "canonicalid": "P53_YEAST",
  "sequence_md5": "...",
  "species": {"taxon_id": 559292, "species": "Saccharomyces cerevisiae"}
}
```

Test sentinel: `YEAST00012` → `omaid == "YEAST00012"`, species contains
"Saccharomyces". For the human TP53, use UniProt accession `P04637`.

## Bulk

`supports_bulk = False` — bulk OMA exports are very large (tens of GB) and
have specialised flat-file formats; v1 focuses on the API. Power users can
consult the OmaDB R/Python packages for bulk handling.

## Citation

Altenhoff AM, et al. The OMA orthology database in 2024. Nucleic Acids Res.
52:D513–D520 (2024).
