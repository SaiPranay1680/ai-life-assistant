import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.documents import Document
from app.modules.documents import service as documents_service
from app.worker.celery_app import celery_app


@celery_app.task(
    name="documents.process_document",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_document_task(self, document_id: str) -> str:
    return asyncio.run(_run(document_id))


async def _run(document_id: str) -> str:
    # Fresh engine per Celery task — shared async pool breaks across asyncio.run() calls.
    engine = create_async_engine(settings.database_url, poolclass=NullPool, future=True, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as db:
            result = await db.execute(select(Document).where(Document.id == UUID(document_id)))
            document = result.scalar_one_or_none()
            if document is None:
                return "missing"

            if document.processing_status in ("ready_for_review", "reviewed", "failed"):
                return document.processing_status

            document.processing_status = "processing"
            await db.commit()

            await documents_service.process_document_pipeline(db, document)
            await db.refresh(document)
            return document.processing_status or "unknown"
    finally:
        await engine.dispose()
