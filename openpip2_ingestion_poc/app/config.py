import os
from arq.connections import RedisSettings


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://openpip:openpip@localhost:5432/openpip_poc")


def get_storage_root() -> str:
    return os.getenv("STORAGE_ROOT", "./data/uploads")


def get_parser_version() -> str:
    return os.getenv("PARSER_VERSION", "psi_mitab_core15_v1")


def get_redis_settings() -> RedisSettings:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return RedisSettings.from_dsn(redis_url)


def get_minio_config() -> dict[str, str]:
    return {
        "endpoint": os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        "access_key": os.getenv("MINIO_ACCESS_KEY", "openpip"),
        "secret_key": os.getenv("MINIO_SECRET_KEY", "openpipminio"),
    }


def get_logto_issuer() -> str:
    return os.getenv("LOGTO_ISSUER", "http://logto.local")
