import logging
import uuid

from django.core.cache import cache
from django.utils import timezone

from core.models import AsyncTaskRecord


logger = logging.getLogger(__name__)


class TaskService:
    """Small compatibility layer for long-running task state."""

    CACHE_TTL_SECONDS = 60 * 60 * 24

    @classmethod
    def create_task(cls, task_type, project_id=None, payload=None, created_by=None, task_id=None):
        task_id = task_id or uuid.uuid4().hex
        record = AsyncTaskRecord.objects.create(
            task_id=task_id,
            task_type=task_type,
            project_id=project_id,
            payload=payload or {},
            created_by_id=getattr(created_by, "id", None),
        )
        cls._cache(record)
        return record

    @classmethod
    def attach_celery_task(cls, task_id, celery_task_id):
        record = AsyncTaskRecord.objects.get(task_id=task_id)
        record.mark_running(celery_task_id=celery_task_id)
        cls._cache(record)
        return record

    @classmethod
    def update_progress(cls, task_id, progress, message="", status=None, result=None):
        record = AsyncTaskRecord.objects.get(task_id=task_id)
        record.progress = max(0, min(100, int(progress)))
        if message:
            record.message = message
        if status:
            record.status = status
            if status == "running" and not record.started_at:
                record.started_at = timezone.now()
            if status in {"completed", "failed", "cancelled"} and not record.finished_at:
                record.finished_at = timezone.now()
        if result is not None:
            record.result = result
        record.save()
        cls._cache(record)
        logger.info("Task progress task_id=%s status=%s progress=%s", task_id, record.status, record.progress)
        return record

    @classmethod
    def request_cancel(cls, task_id):
        record = AsyncTaskRecord.objects.get(task_id=task_id)
        record.cancel_requested = True
        record.status = "cancelling"
        record.save(update_fields=["cancel_requested", "status", "updated_at"])
        cls._cache(record)
        return record

    @classmethod
    def is_cancel_requested(cls, task_id):
        cache_key = cls._cache_key(task_id)
        cached = cache.get(cache_key)
        if cached:
            return bool(cached.get("cancel_requested"))
        return AsyncTaskRecord.objects.filter(task_id=task_id, cancel_requested=True).exists()

    @classmethod
    def get_status(cls, task_id):
        cached = cache.get(cls._cache_key(task_id))
        if cached:
            return cached
        record = AsyncTaskRecord.objects.get(task_id=task_id)
        cls._cache(record)
        return cls._serialize(record)

    @classmethod
    def _cache(cls, record):
        cache.set(cls._cache_key(record.task_id), cls._serialize(record), cls.CACHE_TTL_SECONDS)

    @staticmethod
    def _cache_key(task_id):
        return f"async_task:{task_id}"

    @staticmethod
    def _serialize(record):
        return {
            "task_id": record.task_id,
            "task_type": record.task_type,
            "project_id": record.project_id,
            "status": record.status,
            "progress": record.progress,
            "message": record.message,
            "result": record.result,
            "error_message": record.error_message,
            "cancel_requested": record.cancel_requested,
            "celery_task_id": record.celery_task_id,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }
