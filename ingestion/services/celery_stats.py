"""
Celery runtime statistics helper.

Returns real-time numbers from Celery workers and the broker so the UI can
reflect the actual active and queued tasks rather than stale DB or cache state.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import os

from celery import current_app
from django.conf import settings

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis may not be available in tests
    redis = None

logger = logging.getLogger(__name__)


def _get_celery_app():
    try:
        # Prefer the configured app if available
        from data_warehouse.celery import app as celery_app  # lazy import
        return celery_app
    except Exception:
        return current_app


def _parse_redis_url(url: str):
    """Parse redis URL to connection kwargs understood by redis-py."""
    # Examples: redis://:password@host:6379/0
    #           rediss://:password@host:6379/0
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("redis", "rediss"):
        return None

    db = 0
    if parsed.path and parsed.path.strip("/"):
        try:
            db = int(parsed.path.strip("/"))
        except Exception:
            db = 0
    pw = parsed.password
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 6379,
        "db": db,
        "password": pw,
        "ssl": parsed.scheme == "rediss",
    }


def _redis_queue_lengths(queue_names: List[str], broker_url: str) -> Dict[str, int]:
    """Return lengths for each Redis list used as a Celery queue.

    Celery with Redis uses list names equal to the queue names.
    """
    lengths: Dict[str, int] = {name: 0 for name in queue_names}
    if not broker_url or not redis:
        return lengths

    try:
        kwargs = _parse_redis_url(broker_url)
        if not kwargs:
            return lengths
        client = redis.Redis(**kwargs)  # type: ignore
        for name in queue_names:
            try:
                # Celery uses list key equal to the queue name
                lengths[name] = int(client.llen(name))
            except Exception as e:  # pragma: no cover - broker hiccups
                logger.warning(f"Unable to query Redis length for {name}: {e}")
        return lengths
    except Exception as e:  # pragma: no cover - connection issues
        logger.warning(f"Redis queue length inspection failed: {e}")
        return lengths


def get_celery_stats(timeout: float = 2.0) -> Dict[str, Any]:
    """Collect real-time Celery stats.

    Returns a dict with keys: broker, workers, active, reserved, scheduled,
    queues, total_queued, and active_tasks (name/kwargs).
    """
    app = _get_celery_app()
    insp = app.control.inspect(timeout=timeout)

    # Defaults
    workers: List[str] = []
    active_count = 0
    reserved_count = 0
    scheduled_count = 0
    active_tasks_list: List[Dict[str, Any]] = []
    queue_names: List[str] = []

    try:
        stats = insp.stats() or {}
        workers = list(stats.keys()) if isinstance(stats, dict) else []
    except Exception as e:
        logger.debug(f"inspect.stats failed: {e}")

    try:
        actives = insp.active() or {}
        for w, tasks in (actives.items() if isinstance(actives, dict) else []):
            active_count += len(tasks or [])
            for t in tasks or []:
                # t has keys: name, args, kwargs, time_start, ...
                active_tasks_list.append({
                    "worker": w,
                    "name": t.get("name"),
                    "kwargs": t.get("kwargs"),
                })
    except Exception as e:
        logger.debug(f"inspect.active failed: {e}")

    try:
        reserved = insp.reserved() or {}
        for _, tasks in (reserved.items() if isinstance(reserved, dict) else []):
            reserved_count += len(tasks or [])
    except Exception as e:
        logger.debug(f"inspect.reserved failed: {e}")

    try:
        scheduled = insp.scheduled() or {}
        for _, entries in (scheduled.items() if isinstance(scheduled, dict) else []):
            # entries can be dicts with 'request'
            scheduled_count += len(entries or [])
    except Exception as e:
        logger.debug(f"inspect.scheduled failed: {e}")

    try:
        active_queues = insp.active_queues() or {}
        # active_queues dict: worker -> [{name: queue_name, ...}, ...]
        names = set()
        for _, queues in (active_queues.items() if isinstance(active_queues, dict) else []):
            for q in queues or []:
                if isinstance(q, dict) and q.get("name"):
                    names.add(q["name"])    
        queue_names = sorted(names)
    except Exception as e:
        logger.debug(f"inspect.active_queues failed: {e}")

    # Fallback to configured default queue if none discovered
    if not queue_names:
        try:
            default_q = getattr(settings, 'CELERY_TASK_DEFAULT_QUEUE', None)
            if default_q:
                queue_names = [default_q]
        except Exception:
            pass

    # Broker & queue depth
    broker_url = os.getenv("CELERY_BROKER_URL", "")
    queues_info: List[Dict[str, Any]] = []
    total_queued = 0
    if broker_url.startswith("redis") and queue_names:
        lengths = _redis_queue_lengths(queue_names, broker_url)
        for q in queue_names:
            qlen = lengths.get(q, 0)
            queues_info.append({"name": q, "messages": qlen})
            total_queued += qlen
    else:
        # Unknown broker or queue names; just report names if any
        for q in queue_names:
            queues_info.append({"name": q, "messages": None})

    return {
        "broker": ("redis" if broker_url.startswith("redis") else ("unknown" if not broker_url else broker_url.split(":", 1)[0])),
        "workers": workers,
        "active": active_count,
        "reserved": reserved_count,
        "scheduled": scheduled_count,
        "queues": queues_info,
        "total_queued": total_queued,
        "active_tasks": active_tasks_list,
    }
