import os
import uuid
from pathlib import Path

from arq.connections import ArqRedis
from fastapi import HTTPException, UploadFile

from ..db import (
    create_job,
    create_upload_file,
    ensure_dataset,
    get_job,
    list_job_errors,
)


async def create_upload_and_enqueue_validation(
    *,
    db_pool,
    redis: ArqRedis,
    storage_root: Path,
    file: UploadFile,
    dataset_id: int,
    parser_hint: str,
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    await ensure_dataset(db_pool, dataset_id)

    safe_name = os.path.basename(file.filename)
    storage_key = f"incoming/{uuid.uuid4().hex}_{safe_name}"
    storage_path = storage_root / storage_key
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    contents = await file.read()
    storage_path.write_bytes(contents)

    upload_file_id = await create_upload_file(
        pool=db_pool,
        dataset_id=dataset_id,
        filename=safe_name,
        storage_key=storage_key,
        parser_hint=parser_hint,
    )

    job_id = await create_job(
        pool=db_pool,
        upload_file_id=upload_file_id,
        dataset_id=dataset_id,
        storage_key=storage_key,
        parser_hint=parser_hint,
    )

    queued = await redis.enqueue_job(
        "validate_upload_job",
        job_id,
        dataset_id,
        storage_key,
        parser_hint,
    )

    return {
        "job_id": job_id,
        "queue_job_id": queued.job_id if queued else None,
        "storage_key": storage_key,
    }


async def enqueue_commit(*, db_pool, redis: ArqRedis, job_id: str) -> dict:
    job = await get_job(db_pool, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    if job["status"] != "validated":
        raise HTTPException(
            status_code=400,
            detail=f"Job must be in 'validated' status, current: {job['status']}",
        )

    queued = await redis.enqueue_job(
        "commit_upload_job",
        job_id,
        job["dataset_id"],
        job["storage_key"],
        job["parser_hint"],
    )

    return {
        "job_id": job_id,
        "queue_job_id": queued.job_id if queued else None,
        "message": "Commit phase enqueued; write will begin shortly.",
    }


async def get_job_or_404(*, db_pool, job_id: str) -> dict:
    job = await get_job(db_pool, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


async def get_job_errors(*, db_pool, job_id: str, limit: int, offset: int) -> dict:
    _ = await get_job_or_404(db_pool=db_pool, job_id=job_id)
    errors = await list_job_errors(
        pool=db_pool,
        job_id=job_id,
        limit=max(1, min(limit, 1000)),
        offset=max(0, offset),
    )
    return {"items": errors, "count": len(errors)}
