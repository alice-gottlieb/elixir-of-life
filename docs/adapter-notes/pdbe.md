# PDBe adapter notes

**Consulted:** 2026-05-02 via the PDBe REST API docs at ebi.ac.uk/pdbe/api/doc.

## Base URL

- Legacy REST API: `https://www.ebi.ac.uk/pdbe/api`
- PDBe Graph API (newer, 80+ endpoints): `https://www.ebi.ac.uk/pdbe/graph-api`

This adapter uses the **legacy REST API** which has a stable, well-documented
per-entry surface and is simpler to consume for the common use cases here.

## Endpoints used

- `GET /pdb/entry/summary/{pdb_id}` — entry summary (title, release date,
  experimental method, resolution, depositors). Response: `{pdb_id: [{...}]}`.
- `GET /pdb/entry/experiment/{pdb_id}` — experimental details.
- `GET /pdb/entry/ligand_monomers/{pdb_id}` — ligands.
- `GET /pdb/entry/polymer_coverage/{pdb_id}` — chain coverage.
- `GET /mappings/uniprot/{pdb_id}` — UniProt cross-references.
- `GET /pdb/compound/summary/{ccd_id}` — ligand/compound by CCD code.

## Response format

JSON only. Single-entry endpoints return a top-level dict keyed by the PDB ID,
containing a list of one or more dicts. We extract `data[pdb_id][0]` for
single-record operations.

## Pagination

None — all PDBe REST endpoints are per-entry (not lists).

## Rate limits / UA

- No documented hard limit; 429 on excess. Our `HttpClient` honours Retry-After.
- User-Agent: `elixir-query/<version>`.
- No authentication.

## Example request

`GET https://www.ebi.ac.uk/pdbe/api/pdb/entry/summary/1cbs`

Response (excerpt):
```json
{
  "1cbs": [{
    "pdb_id": "1cbs",
    "title": "CRYSTAL STRUCTURE OF CELLULAR RETINOIC ACID BINDING PROTEIN II",
    "release_date": "19960925",
    "experimental_method": ["X-ray diffraction"],
    "resolution": 1.8
  }]
}
```

Test sentinel: `1cbs` → `title` contains "RETINOIC", `experimental_method`
contains `"X-ray diffraction"`.

## Bulk

`supports_bulk = False` — there is no per-entry list endpoint; bulk PDB data
comes from RCSB FTP (`https://files.wwpdb.org/pub/pdb/`) which is outside
the EBI PDBe REST API scope. v1 skips bulk.

## Citation

Bekker GJ, et al. PDBe: improved findability of macromolecular structure
data at the protein data bank in Europe. Nucleic Acids Res. 52:D411–D416 (2024).
