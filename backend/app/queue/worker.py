from app.config import get_settings
from app.queue.client import redis_settings_from_url
from app.queue.jobs import run_tool_job


def worker_redis_url() -> str:
    return get_settings().redis_url or "redis://localhost:6379/0"


class WorkerSettings:
    functions = [run_tool_job]
    job_timeout = 30
    redis_settings = redis_settings_from_url(worker_redis_url())
