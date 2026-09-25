"""Celery worker. Run from the server directory:

    celery -A app.worker.celery_app:celery_app worker --pool=threads --concurrency=4 --loglevel=info

`--pool=threads` is required on Windows, where Celery's default prefork pool doesn't work.
"""
