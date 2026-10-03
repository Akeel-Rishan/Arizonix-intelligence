import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request

security_logger = logging.getLogger("arizonix.security")


class RedactAccessQueryFilter(logging.Filter):
    """Keep Uvicorn access logs useful without retaining query-string secrets."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) >= 3:
            arguments = list(record.args)
            if isinstance(arguments[2], str):
                arguments[2] = arguments[2].split("?", 1)[0]
                record.args = tuple(arguments)
        return True


def configure_safe_access_logging() -> None:
    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, RedactAccessQueryFilter) for item in logger.filters):
        logger.addFilter(RedactAccessQueryFilter())


def request_id_for(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return str(value) if isinstance(value, UUID) else "unavailable"


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"


def log_security_event(
    request: Request,
    *,
    event: str,
    reason: str,
    status_code: int,
    actor_user_id: UUID | None = None,
    severity: int = logging.WARNING,
) -> None:
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "severity": logging.getLevelName(severity),
        "event": event,
        "request_id": request_id_for(request),
        "method": request.method,
        "route": _route_template(request),
        "status": status_code,
        "actor_user_id": str(actor_user_id) if actor_user_id is not None else None,
        "reason": reason,
    }
    security_logger.log(severity, json.dumps(record, separators=(",", ":"), sort_keys=True))
