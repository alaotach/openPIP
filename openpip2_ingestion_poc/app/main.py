from pathlib import Path

from arq import create_pool
from fastapi import FastAPI

from .config import get_database_url, get_redis_settings, get_storage_root
from .db import create_db_pool, init_db
from .routers import admin, datasets, exports, search, uploads

app = FastAPI(title="openPIP 2.0 API", version="0.2.0")


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


app.include_router(uploads.router)
app.include_router(search.router)
app.include_router(exports.router)
app.include_router(datasets.router)
app.include_router(admin.router)
