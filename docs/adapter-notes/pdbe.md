# PDBe adapter notes

**Consulted:** 2026-05-02

## Base URLs

- Entry API: `https://www.ebi.ac.uk/pdbe/api`
- New aggregated API v2: `https://www.ebi.ac.uk/pdbe/api/v2/`

## Endpoints used

- `GET /pdb/entry/summary/{pdb_id}` — entry summary (title, method, resolution, dates).
- `GET /pdb/entry/molecules/{pdb_id}` — molecules (chains, sequences, names).
- `GET /pdb/entry/publications/{pdb_id}` — primary citation.
- `GET /pdb/entry/ligand_monomers/{pdb_id}` — bound ligands.

## Response format

JSON.  Each response is a dict keyed by (lowercase) PDB ID, and the value is an
array of objects.  We take `data[pdb_id.lower()][0]` for single-entry calls.

```json
{
  "1cbs": [{
    "pdb_id": "1cbs",
    "title": "CRYSTAL STRUCTURE OF CELLULAR RETINOIC-ACID-BINDING PROTEIN...",
    "experimental_method": ["X-ray diffraction"],
    "resolution": 1.8,
    "release_date": "19940131",
    "deposition_date": "19931019"
  }]
}
```

## Pagination

No pagination — responses cover a single PDB entry.  For multi-entry queries use
comma-separated IDs in the path.

## Rate limits / auth

No auth required.  HTTPS only.

## Reproducible example

```
GET https://www.ebi.ac.uk/pdbe/api/pdb/entry/summary/1cbs
```

Sentinel: `pdb_id == "1cbs"`, `experimental_method` contains "X-ray diffraction".

## Citation

Armstrong DR, et al. PDBe: improved findability of macromolecular structure data
in the PDB. Nucleic Acids Res. 48:D335–D343 (2020).
