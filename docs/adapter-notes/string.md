# STRING adapter notes

**Consulted:** 2026-05-02 via string-db.org/help/api/.

## Base URL

- REST API: `https://string-db.org/api`
- Format-specific base: `https://string-db.org/api/{format}/{method}`
  where format is `tsv`, `json`, `json11`, `image`, `svg`, etc.

## Endpoints used

- `GET /tsv/get_string_ids?identifiers={names}&species={taxon_id}&limit=1`
  — resolve gene/protein names to STRING identifiers.
- `GET /tsv/network?identifiers={string_ids}&species={taxon_id}`
  — interaction network between listed proteins. Returns all pairwise
  interactions when >1 protein is given, or the top-`required_score` edges
  when 1 protein is given.
- `GET /tsv/interaction_partners?identifiers={id}&species={taxon_id}&limit=N`
  — interaction partners for a single protein.
- `GET /tsv/functional_annotation?identifiers={string_ids}&species={taxon_id}`
  — GO/KEGG annotations for listed proteins.

## Response format

**Native TSV** (preferred). Columns for network:
`stringId_A`, `stringId_B`, `preferredName_A`, `preferredName_B`,
`ncbiTaxonId`, `score`, `nscore`, `fscore`, `pscore`, `ascore`, `escore`,
`dscore`, `tscore`.

Score range 0–1000; `score` is the combined score (recommended threshold ≥400).

## Pagination

None — results are bounded by the input protein list or the `limit` parameter.

## Rate limits / UA

- No documented hard rate limit; recommended to keep ≤50 proteins per request.
- `User-Agent: elixir-query/<version>`. No auth required.

## Example request

`GET https://string-db.org/api/tsv/interaction_partners?identifiers=9606.ENSP00000269305&species=9606&limit=10`

(`9606.ENSP00000269305` is TP53)

Response (TSV):
```
stringId_A\tstringId_B\tpreferredName_A\tpreferredName_B\tncbiTaxonId\tscore\t...
9606.ENSP00000269305\t9606.ENSP00000349977\tTP53\tMDM2\t9606\t999\t...
```

Test sentinel: TP53 (`9606.ENSP00000269305`) → top partners include `MDM2`
(score ≥ 900).

## Bulk

`supports_bulk = True`: full protein link files at
`https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz`
(human only, ~1 GB compressed). We implement bulk as a streaming download of
the human protein links file.

## Citation

Szklarczyk D, et al. The STRING database in 2023: protein–protein association
networks and functional enrichment analyses for any sequenced genome of interest.
Nucleic Acids Res. 51:D638–D646 (2023).
