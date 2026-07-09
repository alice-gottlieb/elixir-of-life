# Ensembl Genomes adapter notes

**Consulted:** 2026-04-27 via Ensembl Genomes REST docs and plants.ensembl.org.

## Scope

Ensembl Genomes covers non-vertebrate species: **plants, fungi, protists,
metazoa (invertebrates), bacteria**. Vertebrates live in the parent `ensembl`
adapter.

## Base URLs

- REST API: `https://rest.ensembl.org` (the same host serves Ensembl Genomes
  data — there is no separate `rest.ensemblgenomes.org` for the modern
  unified API). Division-specific subdomains exist for the BioMart UI and
  some legacy services (`plants.ensembl.org`, `fungi.ensembl.org`,
  `protists.ensembl.org`, `metazoa.ensembl.org`), but the `/lookup/id`,
  `/overlap/region`, and `/homology` endpoints accept identifiers from any
  division.
- FTP bulk dumps:
  - Plants: `https://ftp.ensemblgenomes.org/pub/plants/current/gtf/<species>/`
  - Fungi:  `https://ftp.ensemblgenomes.org/pub/fungi/current/gtf/<species>/`
  - Protists / Metazoa: same pattern, swap division.

## Endpoints used

- `GET /lookup/id/{id}` — Ensembl-Genomes stable IDs (e.g. `AT3G52260` for
  Arabidopsis, `YJR104C` for *S. cerevisiae*) work directly on the unified
  `/lookup/id` route.
- `GET /lookup/symbol/{species}/{symbol}` — symbol lookup with the
  Ensembl-Genomes species name (e.g. `arabidopsis_thaliana`,
  `saccharomyces_cerevisiae`).
- `GET /homology/id/{id}?compara={metazoa|plants|fungi|protists|pan_homology}`
  — comparative-genomics homology trees.
- `GET /info/genomes/division/{division}` — list every species in a division.

## Response formats

JSON only (negotiated via `Accept: application/json`). Ensembl Genomes never
emits CSV/TSV directly; we flatten one level into a Polars DataFrame and let
`core.cache` persist CSV+Parquet.

## Pagination

None — every endpoint either returns a single record or a complete (already
bounded) list.

## Rate limits / UA

- Same soft rate limit as `rest.ensembl.org` (~15 req/s per IP, headers
  `X-RateLimit-Remaining` / `X-RateLimit-Reset`, HTTP 429 on excess).
- A descriptive User-Agent is requested. We send `elixir-query/<version>`.
- No authentication.

## Example request

`GET https://rest.ensembl.org/lookup/id/AT3G52260?expand=0`
`Accept: application/json`

Response (excerpt):
```json
{
  "id": "AT3G52260",
  "biotype": "protein_coding",
  "species": "arabidopsis_thaliana",
  "object_type": "Gene",
  "assembly_name": "TAIR10",
  "seq_region_name": "3",
  "start": 19378128,
  "end": 19380317,
  "strand": -1,
  "display_name": "PUB48"
}
```

Test sentinel: `species == "arabidopsis_thaliana"` and `biotype == "protein_coding"`.

## Bulk dump shape

Per-species GTF gene annotation file:
`https://ftp.ensemblgenomes.org/pub/<division>/current/gtf/<species>/<Species_name>.<assembly>.<release>.gtf.gz`

Same 9-column GTF schema as the Ensembl adapter; we parse to a DataFrame
keeping `seqname, source, feature, start, end, score, strand, frame, attributes`
and persist Parquet for `pl.scan_parquet`.

## Citation

Yates AD, et al. Ensembl Genomes 2022: an expanding genome resource for
non-vertebrates. Nucleic Acids Res. 50:D996–D1003 (2022).
