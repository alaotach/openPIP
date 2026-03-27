"""ARQ worker jobs for two-phase ingestion: validate then commit."""

from pathlib import Path

from .config import get_parser_version
from .db import (
    add_job_error,
    bulk_insert_interactions,
    complete_job_with_skipped,
    fail_job,
    set_job_progress,
    set_job_stage,
    update_job_status,
)
from .models import CanonicalInteraction, RowValidationError
from .parser import parse_mitab_line


async def validate_upload_job(
    ctx, job_id: str, dataset_id: int, storage_key: str
) -> dict:
    """Phase 1: Parse and validate without writing to DB.
    
    On success, job transitions to 'validated' status.
    All validation errors are recorded in upload_job_errors.
    """
    db_pool = ctx["db_pool"]
    storage_root = Path(ctx["storage_root"])
    parser_version = get_parser_version()

    file_path = storage_root / storage_key
    processed = 0
    failed = 0

    await set_job_stage(db_pool, job_id, "validating")

    try:
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            for row_no, line in enumerate(f, start=1):
                if not line.strip() or line.startswith("#"):
                    continue

                try:
                    # Parse and validate (don't write)
                    interaction = parse_mitab_line(
                        row_no=row_no,
                        line=line,
                        dataset_id=dataset_id,
                        source_file=storage_key,
                        parser_version=parser_version,
                    )
                    processed = row_no

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

                await set_job_progress(db_pool, job_id, processed)

        # Mark as validated (ready for human review and commit)
        await update_job_status(db_pool, job_id, "validated")
        await set_job_stage(db_pool, job_id, "completed")

        return {
            "job_id": job_id,
            "processed": processed,
            "validation_errors": failed,
            "status": "validated",
        }

    except Exception as exc:
        await fail_job(
            db_pool,
            job_id=job_id,
            reason=f"Fatal validation error: {exc}",
            inserted_rows=0,
            failed_rows=failed,
        )
        raise


async def commit_upload_job(
    ctx, job_id: str, dataset_id: int, storage_key: str
) -> dict:
    """Phase 2: Write validated interactions to DB.
    
    Only runs if job is in 'validated' status.
    Tracks both inserted rows and deduplicated (skipped) rows.
    """
    db_pool = ctx["db_pool"]
    storage_root = Path(ctx["storage_root"])
    parser_version = get_parser_version()

    file_path = storage_root / storage_key
    inserted = 0
    skipped = 0
    failed = 0
    batch: list[CanonicalInteraction] = []

    await set_job_stage(db_pool, job_id, "writing")

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
                    batch.append(interaction)

                    if len(batch) >= 1000:
                        batch_inserted, batch_skipped = await bulk_insert_interactions(
                            db_pool, batch
                        )
                        inserted += batch_inserted
                        skipped += batch_skipped
                        batch.clear()

                except RowValidationError:
                    # Skip validation errors (they were already recorded in phase 1)
                    failed += 1
                except Exception as exc:
                    failed += 1

        # Flush remaining batch
        if batch:
            batch_inserted, batch_skipped = await bulk_insert_interactions(db_pool, batch)
            inserted += batch_inserted
            skipped += batch_skipped

        # Mark as committed
        await update_job_status(db_pool, job_id, "committed")
        await complete_job_with_skipped(
            db_pool,
            job_id=job_id,
            inserted_rows=inserted,
            skipped_rows=skipped,
            failed_rows=failed,
        )

        return {
            "job_id": job_id,
            "inserted": inserted,
            "skipped_duplicates": skipped,
            "validation_failures": failed,
            "status": "committed",
        }

    except Exception as exc:
        await fail_job(
            db_pool,
            job_id=job_id,
            reason=f"Fatal commit error: {exc}",
            inserted_rows=inserted,
            failed_rows=failed,
        )
        raise
