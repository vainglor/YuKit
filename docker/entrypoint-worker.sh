#!/bin/sh
set -eu

cd /app/backend
python -m arq app.queue.worker.WorkerSettings
