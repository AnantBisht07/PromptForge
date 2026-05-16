import logging
import time

from fastapi import Request

from app.core.security import decode_token

logger = logging.getLogger("promptforge.requests")


def _request_identity(request: Request) -> tuple[str, str, str]:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return "-", "-", "-"

    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except Exception:
        return "invalid", "-", "-"

    return (
        str(payload.get("user_id", "-")),
        str(payload.get("tenant_id", "-")),
        str(payload.get("role", "-")),
    )


async def request_logging_middleware(request: Request, call_next):
    started = time.perf_counter()
    user_id, tenant_id, role = _request_identity(request)
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.exception(
            "request_failed method=%s path=%s latency_ms=%.1f user_id=%s tenant_id=%s role=%s",
            request.method,
            request.url.path,
            elapsed_ms,
            user_id,
            tenant_id,
            role,
        )
        raise

    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Process-Time-MS"] = f"{elapsed_ms:.1f}"
    logger.info(
        "request method=%s path=%s status=%s latency_ms=%.1f user_id=%s tenant_id=%s role=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        user_id,
        tenant_id,
        role,
    )
    return response
