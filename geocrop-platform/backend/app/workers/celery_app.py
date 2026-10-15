from celery import Celery

from app.core.config import configure_gdal_env, get_settings

settings = get_settings()
configure_gdal_env(settings)

celery_app = Celery("geocrop", broker=settings.redis_url, backend=settings.redis_url,
                    include=["app.workers.tasks"])
celery_app.conf.update(
    task_always_eager=settings.celery_always_eager,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "geocrop.ingest": {"queue": "ingest"},
        "geocrop.run_pipeline": {"queue": "models"},
    },
    task_default_queue="default",
)
