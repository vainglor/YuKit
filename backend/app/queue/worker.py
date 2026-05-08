from app.queue.jobs import run_tool_job


class WorkerSettings:
    functions = [run_tool_job]
    job_timeout = 30
