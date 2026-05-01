from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger("django.request")


def dispatch_task(task: object, *args: Any, **kwargs: Any) -> None:
    try:
        task.delay(*args, **kwargs)
    except Exception:
        logger.exception("Celery broker unavailable; running task locally.")
        task.apply(args=args, kwargs=kwargs, throw=False)

