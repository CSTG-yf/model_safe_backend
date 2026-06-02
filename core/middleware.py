import logging
import time
import uuid


api_logger = logging.getLogger("api.debug")


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.request_id = request_id
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response


class APIRequestLogMiddleware:
    """Write compact API request logs for frontend/backend debugging."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.perf_counter()
        response = None
        try:
            response = self.get_response(request)
            return response
        finally:
            if request.path.startswith("/api/"):
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                request_id = getattr(request, "request_id", "-")
                status_code = getattr(response, "status_code", 500)
                user = getattr(request, "user", None)
                user_id = getattr(user, "id", None) if getattr(user, "is_authenticated", False) else None
                query_string = request.META.get("QUERY_STRING", "")
                path = request.path
                if query_string:
                    path = f"{path}?{query_string}"

                api_logger.info(
                    "request_id=%s method=%s path=%s status=%s duration_ms=%s user_id=%s remote_addr=%s",
                    request_id,
                    request.method,
                    path,
                    status_code,
                    duration_ms,
                    user_id or "-",
                    request.META.get("REMOTE_ADDR", "-"),
                )
