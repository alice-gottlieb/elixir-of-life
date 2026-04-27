# Rhea adapter notes

**Consulted:** 2026-04-27 via the Rhea help pages (rhea-db.org/help/rest-api, /help/api, /help/download).

## Base URLs

- REST search / single-entry: `https://www.rhea-db.org/rhea`
  - Search:   `GET https://www.rhea-db.org/rhea?query=...&columns=...&format=tsv&limit=...`
  - Entry:    `GET https://www.rhea-db.org/rhea/{id}.{ext}` where `{id}` is the numeric Rhea ID
              (no `RHEA:` prefix) and `{ext}` is `rxn`, `rd`, or omitted (use the search
              endpoint with `query=rhea:{id}` for tabular data).
- FTP bulk:  `https://ftp.expasy.org/databases/rhea/tsv/`
  - Useful files: `rhea-reactions.tsv`, `rhea2uniprot_sprot.tsv`, `rhea2chebi.tsv`,
                 `rhea2ec.tsv`, `rhea-directions.tsv`.

## Query parameters (REST search)

| param     | meaning                                                                       |
|-----------|-------------------------------------------------------------------------------|
| `query`   | Free-text or field-qualified query: `glucose`, `rhea:10044`, `uniprot:P12345`. |
| `columns` | Comma-separated columns: `rhea-id,equation,chebi,uniprot,ec`, etc.             |
| `format`  | `tsv` (preferred), `json`, `rxn`, `rd`.                                       |
| `limit`   | Max rows (server caps at a few thousand per request).                         |

## Response formats (tabular preference)

Rhea's REST endpoint returns TSV (typed columns, smallest payload), JSON, or RXN/RD
chemistry text. We accept TSV over the wire and let `core.cache` persist as CSV +
Parquet per the project-wide preference.

## Pagination

The REST search endpoint is **not paginated** — callers pass `limit=N` (server-side cap).
For exhaustive dumps we use the Expasy FTP TSV files instead.

## Rate limits / UA policy

No documented hard limit on the REST endpoint; the service expects polite use and a
descriptive User-Agent (we send `elixir-query/<version>`). FTP downloads are unlimited.

## Example request + expected payload

`GET https://www.rhea-db.org/rhea?query=rhea:10044&columns=rhea-id,equation,chebi,ec&format=tsv&limit=1`

Expected first row:

```
Reaction identifier	Equation	ChEBI identifier(s)	EC number
RHEA:10044	(S)-lactate + NAD(+) = pyruvate + NADH + H(+)	CHEBI:16651;...	1.1.1.27
```

Test sentinel: `RHEA:10044` is L-lactate dehydrogenase; equation contains "(S)-lactate"
and "pyruvate", and the participants include CHEBI:16651 (L-lactate) and CHEBI:15361
(pyruvate). EC = `1.1.1.27`.

## Bulk dump shape

`rhea-reactions.tsv` (TSV, ~15k rows): one row per directional reaction with columns
`MASTER_ID`, `ID`, `DIRECTION`, `EQUATION`, `STATUS`. Streamed to disk, parsed with
Polars, written to Parquet for `pl.scan_parquet`.

## Citation

Bansal P. et al. Rhea, the reaction knowledgebase in 2022. Nucleic Acids Res. 50(D1)
D693–D700 (2022).
