# openPIP 2.0 Ingestion POC

This POC validates the highest technical risk from the proposal:

- file upload to API
- async queue with ARQ
- streaming PSI-MI TAB parsing
- Postgres writes for valid rows
- row-level error storage and retrieval for invalid rows

## Stack

- FastAPI
- ARQ + Redis
- PostgreSQL
- Docker Compose

## What is implemented

- `POST /uploads/jobs` accepts multipart upload and enqueues ingestion
- `GET /uploads/jobs/{job_id}` returns stage and counters
- `GET /uploads/jobs/{job_id}/errors` returns row-level parse/validation failures
- Worker parses PSI-MI rows line-by-line and writes interactions in batches
- Errors are persisted to `upload_job_errors`

## Run locally

From this folder:

1. Build and start services

```bash
docker compose up --build
```

2. Health check

```bash
curl http://localhost:8000/health
```

## Demo flow

1. Upload sample file

```bash
curl -X POST http://localhost:8000/uploads/jobs \
  -F "dataset_id=42" \
  -F "parser_hint=psi_mitab" \
  -F "file=@sample_data/mitab_demo.tsv"
```

2. Poll job status (replace JOB_ID)

```bash
curl http://localhost:8000/uploads/jobs/JOB_ID
```

3. Get row-level errors

```bash
curl "http://localhost:8000/uploads/jobs/JOB_ID/errors?limit=100&offset=0"
```

Expected behavior with the sample file:

- 2 rows inserted
- 2 rows reported in `upload_job_errors`

## Suggested screenshot/video capture

For proposal evidence, capture these three moments:

1. Upload response showing `job_id`
2. Job status showing `stage=completed`, `inserted_rows`, `failed_rows`
3. Error endpoint payload showing `source_row`, `error_code`, `error_message`

A 30 to 60 second terminal screen recording is enough to support Section 15 credibility.

## File map

- `app/main.py`: API endpoints
- `app/worker.py`: ARQ worker settings
- `app/jobs.py`: ingestion job logic
- `app/parser.py`: streaming PSI-MI parser
- `app/db.py`: schema + DB operations
- `sample_data/mitab_demo.tsv`: fixture with valid and invalid rows
