from pathlib import Path

from .config import get_parser_version
from .db import (
    add_job_error,
    bulk_insert_interactions,
    complete_job,
    fail_job,
    set_job_progress,
    set_job_stage,
)
from .models import CanonicalInteraction, RowValidationError
from .parser import parse_mitab_line


async def ingest_upload_job(ctx, job_id: str, dataset_id: int, storage_key: str) -> dict:
    db_pool = ctx["db_pool"]
    storage_root = Path(ctx["storage_root"])
    parser_version = get_parser_version()

    file_path = storage_root / storage_key
    inserted = 0
    failed = 0
    processed = 0
    batch: list[CanonicalInteraction] = []

    await set_job_stage(db_pool, job_id, "parsing")

    try:
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            for row_no, line in enumerate(f, start=1):
                if not line.strip() or line.startswith("#"):
                    continue

                try:
                    interaction = parse_mitab_line(
                        row_no=row_no,
                        line=line,
                        dataset_id=dataset_id,
                        source_file=storage_key,
                        parser_version=parser_version,
                    )
                    processed = row_no
                    await set_job_progress(db_pool, job_id, processed)
                    batch.append(interaction)

                    if len(batch) >= 1000:
                        await set_job_stage(db_pool, job_id, "writing")
                        inserted += await bulk_insert_interactions(db_pool, batch)
                        batch.clear()
                        await set_job_stage(db_pool, job_id, "parsing")

                except RowValidationError as err:
                    failed += 1
                    await add_job_error(
                        db_pool,
                        job_id=job_id,
                        source_row=row_no,
                        error_code=err.code,
                        error_message=err.message,
                        raw_payload=line.rstrip("\n"),
                    )
                except Exception as exc:
                    failed += 1
                    await add_job_error(
                        db_pool,
                        job_id=job_id,
                        source_row=row_no,
                        error_code="ROW_RUNTIME",
                        error_message=str(exc),
                        raw_payload=line.rstrip("\n"),
                    )

        if batch:
            await set_job_stage(db_pool, job_id, "writing")
            inserted += await bulk_insert_interactions(db_pool, batch)

        await complete_job(db_pool, job_id=job_id, inserted_rows=inserted, failed_rows=failed)
        return {"job_id": job_id, "inserted": inserted, "failed": failed}

    except Exception as exc:
        await fail_job(
            db_pool,
            job_id=job_id,
            reason=f"Fatal ingestion error: {exc}",
            inserted_rows=inserted,
            failed_rows=failed,
        )
        raise
