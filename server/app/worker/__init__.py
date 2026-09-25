"""Phase 15: Celery background worker.

Run it next to the API (from the server directory):

    celery -A app.worker.celery_app:celery_app worker --pool=threads --concurrency=4 --loglevel=info

`--pool=threads` is required on Windows (Celery's default prefork pool needs fork) and suits this
workload, which mostly waits on the Gemini and Qdrant APIs.
"""
