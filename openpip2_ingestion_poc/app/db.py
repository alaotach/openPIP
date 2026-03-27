import json
import uuid

import asyncpg

from .models import CanonicalInteraction

from typing import Iterator
DDL = """
CREATE TABLE IF NOT EXISTS upload_jobs (
    id UUID PRIMARY KEY,
    dataset_id BIGINT NOT NULL,
    storage_key TEXT NOT NULL,
    parser_hint TEXT,
    stage TEXT NOT NULL CHECK (stage IN ('queued','parsing','validating','writing','completed','failed')),
    status TEXT NOT NULL DEFAULT 'parsing' CHECK (status IN ('parsing', 'validated', 'committed')),
    total_rows BIGINT,
    processed_rows BIGINT NOT NULL DEFAULT 0,
    inserted_rows BIGINT NOT NULL DEFAULT 0,
    skipped_rows BIGINT NOT NULL DEFAULT 0,
    failed_rows BIGINT NOT NULL DEFAULT 0,
    validated_data_location TEXT,
    error_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS upload_job_errors (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES upload_jobs(id) ON DELETE CASCADE,
    source_row BIGINT NOT NULL,
    error_code TEXT NOT NULL,
    error_message TEXT NOT NULL,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS interactions (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL,
    pair_key TEXT NOT NULL,
    interactor_a_ns TEXT NOT NULL,
    interactor_a_id TEXT NOT NULL,
    interactor_b_ns TEXT NOT NULL,
    interactor_b_id TEXT NOT NULL,
    interaction_type TEXT,
    confidence_score DOUBLE PRECISION,
    publication_id TEXT,
    source_file TEXT NOT NULL,
    source_row BIGINT NOT NULL,
    parser_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (dataset_id, pair_key, publication_id, source_row)
);

CREATE INDEX IF NOT EXISTS idx_interactions_pair_key ON interactions(pair_key);
CREATE INDEX IF NOT EXISTS idx_interactions_dataset ON interactions(dataset_id);
"""


async def create_db_pool(database_url: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn=database_url, min_size=1, max_size=10)


async def init_db(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(DDL)


async def create_job(
    pool: asyncpg.Pool,
    dataset_id: int,
    storage_key: str,
    parser_hint: str | None,
) -> str:
    job_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO upload_jobs (id, dataset_id, storage_key, parser_hint, stage)
            VALUES ($1::uuid, $2, $3, $4, 'queued')
            """,
            job_id,
            dataset_id,
            storage_key,
            parser_hint,
        )
    return job_id


async def get_job(pool: asyncpg.Pool, job_id: str):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id::text, dataset_id, storage_key, parser_hint, stage, total_rows,
                   processed_rows, inserted_rows, failed_rows, error_summary,
                   created_at, updated_at
            FROM upload_jobs
            WHERE id = $1::uuid
            """,
            job_id,
        )
    return dict(row) if row else None


async def list_job_errors(pool: asyncpg.Pool, job_id: str, limit: int, offset: int):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, source_row, error_code, error_message, raw_payload, created_at
            FROM upload_job_errors
            WHERE job_id = $1::uuid
            ORDER BY id ASC
            LIMIT $2 OFFSET $3
            """,
            job_id,
            limit,
            offset,
        )
    return [dict(r) for r in rows]


async def set_job_stage(pool: asyncpg.Pool, job_id: str, stage: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE upload_jobs
            SET stage = $2, updated_at = now()
            WHERE id = $1::uuid
            """,
            job_id,
            stage,
        )


async def set_job_progress(pool: asyncpg.Pool, job_id: str, processed_rows: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE upload_jobs
            SET processed_rows = $2, updated_at = now()
            WHERE id = $1::uuid
            """,
            job_id,
            processed_rows,
        )


async def add_job_error(
    pool: asyncpg.Pool,
    job_id: str,
    source_row: int,
    error_code: str,
    error_message: str,
    raw_payload: str | None,
) -> None:
    payload = json.dumps({"line": raw_payload}) if raw_payload else None
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO upload_job_errors (job_id, source_row, error_code, error_message, raw_payload)
            VALUES ($1::uuid, $2, $3, $4, $5::jsonb)
            """,
            job_id,
            source_row,
            error_code,
            error_message,
            payload,
        )


async def bulk_insert_interactions(pool: asyncpg.Pool, rows: list[CanonicalInteraction]) -> int:
    if not rows:
        return 0, 0

    async with pool.acquire() as conn:
        # Use RETURNING id to count actual inserts (ON CONFLICT DO NOTHING won't return conflicting rows)
        # We'll insert with RETURNING and count the results
        inserted = 0
        for row in rows:
            result = await conn.fetchval(
            """

                INSERT INTO interactions (
                    dataset_id, pair_key, interactor_a_ns, interactor_a_id,
                    interactor_b_ns, interactor_b_id, interaction_type, confidence_score,
                    publication_id, source_file, source_row, parser_version
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                ON CONFLICT (dataset_id, pair_key, publication_id, source_row) DO NOTHING
                RETURNING id
                """,
                row.dataset_id,
                row.pair_key,
                row.interactor_a_ns,
                row.interactor_a_id,
                row.interactor_b_ns,
                row.interactor_b_id,
                row.interaction_type,
                row.confidence_score,
                row.publication_id,
                row.source_file,
                row.source_row,
                row.parser_version,
            )
            if result is not None:
                inserted += 1
    
    skipped = len(rows) - inserted
    return inserted, skipped

async def complete_job(pool: asyncpg.Pool, job_id: str, inserted_rows: int, failed_rows: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE upload_jobs
            SET stage = 'completed', inserted_rows = $2, failed_rows = $3, updated_at = now()
            WHERE id = $1::uuid
            """,
            job_id,
            inserted_rows,
            failed_rows,
        )


async def fail_job(pool: asyncpg.Pool, job_id: str, reason: str, inserted_rows: int, failed_rows: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE upload_jobs
            SET stage = 'failed', inserted_rows = $2, failed_rows = $3,
                error_summary = $4, updated_at = now()
            WHERE id = $1::uuid
            """,
            job_id,
            inserted_rows,
            failed_rows,
            reason,
        )


    async def update_job_status(
        pool: asyncpg.Pool, job_id: str, status: str
    ) -> None:
        """Update job status: parsing → validated → committed."""
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE upload_jobs
                SET status = $2, updated_at = now()
                WHERE id = $1::uuid
                """,
                job_id,
                status,
            )


    async def complete_job_with_skipped(
        pool: asyncpg.Pool,
        job_id: str,
        inserted_rows: int,
        skipped_rows: int,
        failed_rows: int,
    ) -> None:
        """Mark job completed, tracking duplicates skipped."""
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE upload_jobs
                SET stage = 'completed', inserted_rows = $2, skipped_rows = $3,
                    failed_rows = $4, updated_at = now()
                WHERE id = $1::uuid
                """,
                job_id,
                inserted_rows,
                skipped_rows,
                failed_rows,
            )


    async def get_job_errors_as_csv(
        pool: asyncpg.Pool, job_id: str
    ) -> Iterator[str]:
        """Export job errors as CSV lines."""
        yield "source_row,error_code,error_message,raw_payload\n"
        async with pool.acquire() as conn:
            cursor = await conn.cursor(
                """
                SELECT source_row, error_code, error_message, raw_payload
                FROM upload_job_errors
                WHERE job_id = $1::uuid
                ORDER BY id ASC
                """,
                job_id,
            )
            async for row in cursor:
                source_row, error_code, error_message, raw_payload = row
                # CSV escape: quote values with commas/quotes
                def csv_escape(s):
                    if s is None:
                        return ""
                    s = str(s)
                    if "," in s or '"' in s or "\n" in s:
                        s = s.replace('"', '""')
                        return f'"{s}"'
                    return s
            
                yield f"{csv_escape(source_row)},{csv_escape(error_code)},{csv_escape(error_message)},{csv_escape(raw_payload)}\n"
