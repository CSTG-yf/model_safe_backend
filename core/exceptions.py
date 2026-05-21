import logging

from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None)

    if response is None:
        logger.exception("Unhandled API exception request_id=%s", request_id, exc_info=exc)
        return None

    detail = response.data
    if isinstance(detail, dict):
        message = detail.get("detail") or detail.get("message") or "request failed"
        errors = detail
    else:
        message = str(detail)
        errors = detail

    response.data = {
        "code": getattr(exc, "default_code", "error"),
        "message": message,
        "data": {},
        "errors": errors,
    }
    if request_id:
        response.data["request_id"] = request_id
    return response
