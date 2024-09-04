web: gunicorn main:app
worker: celery -A celery_worker.celery worker --loglevel=info