from celery import Celery

from ..core.config import settings

celery_app = Celery(
    "ai_life_assistant",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(task_track_started=True, task_time_limit=60 * 60)


@celery_app.task(name="app.worker.tasks.process_document_task")
def process_document_task(document_id: str):
    return {"document_id": document_id, "status": "queued"}
