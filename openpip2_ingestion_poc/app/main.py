import os
import uuid
from pathlib import Path

from arq import create_pool
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, StreamingResponse


from .config import get_database_url, get_redis_settings, get_storage_root
from .db import (
    create_db_pool, create_job, get_job, init_db, list_job_errors, 
    get_job_errors_as_csv, update_job_status
)
app = FastAPI(title="openPIP 2.0 Ingestion POC", version="0.1.0")


@app.on_event("startup")
async def startup() -> None:
    app.state.db_pool = await create_db_pool(get_database_url())
    await init_db(app.state.db_pool)

    app.state.redis = await create_pool(get_redis_settings())
    app.state.storage_root = Path(get_storage_root())
    app.state.storage_root.mkdir(parents=True, exist_ok=True)


@app.on_event("shutdown")
async def shutdown() -> None:
    await app.state.redis.close()
    await app.state.db_pool.close()


@app.get("/health")
async def health() -> dict:
    async with app.state.db_pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok"}


@app.post("/uploads/jobs")
async def create_upload_job(
    file: UploadFile = File(...),
    dataset_id: int = Form(...),
    parser_hint: str | None = Form(default="psi_mitab"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    safe_name = os.path.basename(file.filename)
    storage_key = f"incoming/{uuid.uuid4().hex}_{safe_name}"
    storage_path = app.state.storage_root / storage_key
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    contents = await file.read()
    storage_path.write_bytes(contents)

    job_id = await create_job(
        pool=app.state.db_pool,
        dataset_id=dataset_id,
        storage_key=storage_key,
        parser_hint=parser_hint,
    )

    queued = await app.state.redis.enqueue_job(
        "validate_upload_job",
        job_id,
        dataset_id,
        storage_key,
    )

    return {
        "job_id": job_id,
        "queue_job_id": queued.job_id if queued else None,
        "storage_key": storage_key,
    }


@app.get("/uploads/jobs/{job_id}")
async def get_upload_job(job_id: str):
    job = await get_job(app.state.db_pool, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.post("/uploads/jobs/{job_id}/commit")
async def commit_upload_job(job_id: str):
    """Trigger phase 2: write validated data to database."""
    job = await get_job(app.state.db_pool, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    
    if job["status"] != "validated":
        raise HTTPException(
            status_code=400,
            detail=f"Job must be in 'validated' status, current: {job['status']}",
        )
    
    queued = await app.state.redis.enqueue_job(
        "commit_upload_job",
        job_id,
        job["dataset_id"],
        job["storage_key"],
    )
    
    return {
        "job_id": job_id,
        "queue_job_id": queued.job_id if queued else None,
        "message": "Commit phase enqueued; write will begin shortly.",
    }


@app.get("/uploads/jobs/{job_id}/errors")
async def get_upload_job_errors(job_id: str, limit: int = 100, offset: int = 0):
    job = await get_job(app.state.db_pool, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    errors = await list_job_errors(
        pool=app.state.db_pool,
        job_id=job_id,
        limit=max(1, min(limit, 1000)),
        offset=max(0, offset),
    )
    return {"items": errors, "count": len(errors)}


@app.get("/uploads/jobs/{job_id}/errors/export")
async def export_upload_job_errors(job_id: str):
    """Export errors as CSV."""
    job = await get_job(app.state.db_pool, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    
    return StreamingResponse(
        get_job_errors_as_csv(app.state.db_pool, job_id),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=errors_{job_id}.csv"},
    )
