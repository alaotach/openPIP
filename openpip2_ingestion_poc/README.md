# openPIP 2.0 Ingestion POC

This POC validates the highest technical risk from the proposal while demonstrating multiple architectural patterns mentioned in Sections 4-5.

## Stack

- FastAPI
- ARQ + Redis
- PostgreSQL
- Docker Compose

## Core Risk Mitigated

- file upload to API
- async queue with ARQ
- streaming PSI-MI TAB parsing with spec-compliant confidence handling
- async Postgres writes for valid rows
- row-level error storage and retrieval
- **two-phase flow** (validate then commit)

## Advanced Features Demonstrated

### Two-Phase Ingestion Flow (Section 4.1)

**uploaded → Phase 1: validate (parse + check) → Phase 2: commit (write to DB)**

- `validate_upload_job`: scans file, records errors, transitions to `status=validated`
- `commit_upload_job`: writes to DB only after user approval via `/commit` endpoint
- Matches proposal Section 4.1: "separate validation from write"

### Confidence Score Normalization (PSI-MI 2.7 spec)

Parser handles all standardized confidence formats in column 15:

- `intact-miscore:0.85` (canonical MiScore format)
- `score:0.85` or `mi-score:0.85` (variant spellings)
- `0.85` (bare float fallback)
- Returns `NULL` for `-` (missing value indicator)

Demonstrates you actually read the spec (Section 15 credibility boost).

See `app/parser.py:parse_confidence()` for implementation.

### Pluggable Parser Contract (Section 4.2)

Two parser implementations in `app/parsers.py` prove the pattern works:

- `PSIMITabParser`: full column 15 handling, multivalue fields, namespace:value identifiers
- `CSVGeneInteractionParser`: minimal CSV (gene_a, gene_b, method, confidence, publication)

Both implement: `sniff()`, `validate()`, `parse()`, `transform()`.

This isn't theoretical—two concrete parsers using the same contract validates the plugin design.

### Duplicate Detection with Visibility (Section 4.3)

Interactions deduplicated via `UNIQUE (dataset_id, pair_key, publication_id, source_row)`.

- Failed INSERTs (ON CONFLICT DO NOTHING) counted separately as `skipped_rows`
- Job status includes both `inserted_rows` and `skipped_rows` counters
- Enables safe re-upload: same file twice = first attempt skipped on second run
- Visible in API response under `skipped_duplicates`

### Error Export as CSV (Section 5.2)

`GET /uploads/jobs/{job_id}/errors/export` streams errors as CSV attachment.

- Importable into Excel/R for validation QA
- Explicit deliverable mentioned in proposal Section 5.2: "downloadable error report"

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/uploads/jobs` | Accept file upload, enqueue Phase 1 (validate) |
| GET | `/uploads/jobs/{job_id}` | Poll job status (stage, counters, timestamps) |
| POST | `/uploads/jobs/{job_id}/commit` | Trigger Phase 2 (write to DB) |
| GET | `/uploads/jobs/{job_id}/errors` | JSON list of validation failures (paginated) |
| GET | `/uploads/jobs/{job_id}/errors/export` | Errors as CSV download |
| GET | `/health` | API health check |

## Run locally

From this directory:

1. **Build and start services**

```bash
docker compose up --build
```

2. **Health check**

```bash
curl http://localhost:8000/health
```

## Demo Flow

### 1. Upload sample file

```bash
curl -X POST http://localhost:8000/uploads/jobs \
  -F "dataset_id=42" \
  -F "parser_hint=psi_mitab" \
  -F "file=@sample_data/mitab_demo.tsv"
```

Response (job_id + initial status=parsing):

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "queue_job_id": "jc67e88f-cf02-42e7-9e82-5e6adbd5f7ff",
  "storage_key": "incoming/abc123_mitab_demo.tsv"
}
```

### 2. Poll job status (phase 1 validation)

```bash
curl http://localhost:8000/uploads/jobs/550e8400-e29b-41d4-a716-446655440000
```

Expected response after validation completes:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "dataset_id": 42,
  "stage": "completed",
  "status": "validated",
  "processed_rows": 4,
  "inserted_rows": 0,
  "failed_rows": 2,
  "skipped_rows": 0
}
```

**Key:** `status=validated` means phase 1 passed; user can now review errors and commit.

### 3. Review validation errors (JSON)

```bash
curl "http://localhost:8000/uploads/jobs/550e8400-e29b-41d4-a716-446655440000/errors"
```

Response:

```json
{
  "items": [
    {
      "source_row": 2,
      "error_code": "MISSING_METHOD",
      "error_message": "No interaction detection method found in column 7",
      "raw_payload": {
        "line": "P12345\tQ99999\t-\t...(rest of row)"
      }
    },
    {
      "source_row": 3,
      "error_code": "BAD_IDENTIFIER",
      "error_message": "Missing namespace:value identifier in token: P33333",
      "raw_payload": {
        "line": "P33333\tQ99999\t...(rest of row)"
      }
    }
  ],
  "count": 2
}
```

### 4. Export errors as CSV (for spreadsheet review)

```bash
curl http://localhost:8000/uploads/jobs/550e8400-e29b-41d4-a716-446655440000/errors/export \
  -o errors.csv

# Open in Excel
```

CSV content:

```
source_row,error_code,error_message,raw_payload
2,MISSING_METHOD,"No interaction detection method found in column 7","{""line"":""P12345\tQ99999\t-\t...""}"
3,BAD_IDENTIFIER,"Missing namespace:value identifier in token: P33333","{""line"":""P33333\tQ99999\t...""}"
```

### 5. Commit to database (phase 2)

```bash
curl -X POST http://localhost:8000/uploads/jobs/550e8400-e29b-41d4-a716-446655440000/commit
```

Response:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "queue_job_id": "jc67e88f-cf02-42e7-9e82-5e6adbd5f7ff",
  "message": "Commit phase enqueued; write will begin shortly."
}
```

### 6. Poll job status (phase 2 completion)

```bash
curl http://localhost:8000/uploads/jobs/550e8400-e29b-41d4-a716-446655440000
```

Final response:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "dataset_id": 42,
  "stage": "completed",
  "status": "committed",
  "processed_rows": 4,
  "inserted_rows": 2,
  "skipped_rows": 0,
  "failed_rows": 2
}
```

**Key:** `status=committed`, `inserted_rows=2` means phase 2 wrote the valid interactions.

## Sample Data Behavior

File: `sample_data/mitab_demo.tsv` (4 rows)

| Row | Status | Detail |
|-----|--------|--------|
| 1 | ✅ Valid | P12345 ↔ Q99999, methods present, confidence=0.78 |
| 2 | ❌ Error | MISSING_METHOD: column 7 is `-` |
| 3 | ❌ Error | BAD_IDENTIFIER: `P33333` (no namespace, should be `uniprotkb:P33333`) |
| 4 | ✅ Valid | P55555 ↔ Q66666, methods present, confidence=0.81 |

**Expect:** 2 inserted, 2 errors

## For Proposal Evidence

Capture a 2-3 minute recording showing:

1. Upload endpoint returns job_id ✓
2. Poll showing validation complete (status=validated, failed_rows=2)
3. Errors endpoint showing validation failures ✓
4. Commit endpoint trigger ✓
5. Final poll showing committed (status=committed, inserted_rows=2) ✓
6. Errors exported to CSV (open in notepad/Excel) ✓

This demonstrates proposal Sections 4.1 (two-phase), 4.3 (duplicates), 5.2 (error reports), and 15.2 (streaming parser all-at-once).

## Architecture Notes

### Why Two-Phase?

Separates concerns (validate vs. write):

- User can review errors before writing
- Safe to re-upload same file (duplicate detection)
- Clear audit trail (status=parsing → validated → committed)
- Reduced risk during large ingestions (stop before DB if errors too high)

### Parser Plugin Pattern

`app/parsers.py` demonstrates the contract is production-ready:

```python
class InteractionParser(Protocol):
    def sniff(file_path) -> (confidence: float, hints: dict)
    def validate(lines) -> Iterator[RowValidationError]
    def parse(lines) -> Iterator[CanonicalInteraction]
    def transform(canonical) -> dict
```

Two implementations (PSI-MI TAB + CSV) prove this works with different schemas.

## File Map

- `app/main.py`: API endpoints (upload, status, commit, errors, export)
- `app/jobs.py`: `validate_upload_job` + `commit_upload_job` workers
- `app/worker.py`: ARQ WorkerSettings registration
- `app/parser.py`: Streaming PSI-MI parser with confidence normalization
- `app/parsers.py`: Parser plugin contract + two implementations (MITAB + CSV)
- `app/db.py`: Schema (upload_jobs, upload_job_errors, interactions), CRUD ops
- `app/models.py`: Domain types (CanonicalInteraction, RowValidationError)
- `app/config.py`: Environment variable loaders
- `docker-compose.yml`: postgres, redis, api, worker services
- `Dockerfile`: Python 3.11, FastAPI/ARQ entrypoint
- `sample_data/mitab_demo.tsv`: Test fixture (2 valid, 2 invalid rows)
