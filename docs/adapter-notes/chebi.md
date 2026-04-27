# ChEBI adapter notes

**Consulted:** 2026-04-27 via the EBI Ontology Lookup Service (OLS4) and ChEBI
2.0 release notes.

## Backend choice — OLS4

ChEBI's legacy SOAP service was retired in **September 2025** and the dedicated
ChEBI 2.0 REST API (`/chebi/backend/api/`) is still being documented at the time
of writing. The most stable, well-documented programmatic access to ChEBI today
is via the **EBI Ontology Lookup Service** (`OLS4`), which exposes ChEBI as an
ontology with the same coverage and a stable API contract.

We therefore route this adapter through OLS4. When ChEBI's native REST API is
finalised, switching the base URL is a one-line change.

## Base URL

- OLS4 REST API: `https://www.ebi.ac.uk/ols4/api`
- ChEBI within OLS4: `https://www.ebi.ac.uk/ols4/api/ontologies/chebi`

## Endpoints used

- `GET /ontologies/chebi/terms?short_form={CHEBI%3A15377}` — lookup by ChEBI ID.
  OLS4 returns a paginated `_embedded.terms` list; we take the first match.
- `GET /search?q={text}&ontology=chebi&rows=N` — free-text search over labels.
- Bulk: `https://ftp.ebi.ac.uk/pub/databases/chebi/Flat_file_tab_delimited/compounds.tsv.gz`
  (gzipped TSV from the ChEBI flat-file release).

## Response formats

JSON only. We negotiate via `Accept: application/json` and flatten one level
into a Polars DataFrame.

## Pagination

OLS4 uses HAL-style pagination (`page.totalElements`, `_links.next.href`). For
the small queries this adapter performs (single ID, capped search), we honour
the `_links.next` link header up to ``limit`` rows.

## Rate limits / UA

- No documented hard rate limit; 429 returned on excess. Our `HttpClient`
  honours `Retry-After`.
- `User-Agent: elixir-query/<version>`.
- No authentication.

## Example request

`GET https://www.ebi.ac.uk/ols4/api/ontologies/chebi/terms?short_form=CHEBI%3A15377`
`Accept: application/json`

Response (excerpt):
```json
{
  "_embedded": {
    "terms": [
      {
        "iri": "http://purl.obolibrary.org/obo/CHEBI_15377",
        "label": "water",
        "obo_id": "CHEBI:15377",
        "short_form": "CHEBI_15377",
        "ontology_name": "chebi",
        "is_obsolete": false
      }
    ]
  }
}
```

Test sentinel: `CHEBI:15377` has `label == "water"` and `obo_id == "CHEBI:15377"`.

## Bulk dump

`compounds.tsv.gz` (≈10 MB, gzipped) gives one row per ChEBI compound with
columns: `ID`, `STATUS`, `CHEBI_ACCESSION`, `PARENT_ID`, `NAME`, `SOURCE`,
`MODIFIED_ON`. We stream, decompress, parse to Parquet, return LazyFrame.

## Citation

Hastings J, et al. ChEBI in 2016: Improved services and an expanding collection
of metabolites. Nucleic Acids Res. 44:D1214–D1219 (2016). For ChEBI 2.0 see
chembl.blogspot.com/2025/10/chebi2-release.html.
