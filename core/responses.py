from rest_framework.response import Response


def success_response(data=None, message="success", code="success", status_code=200, request_id=None):
    payload = {
        "code": code,
        "message": message,
        "data": data if data is not None else {},
    }
    if request_id:
        payload["request_id"] = request_id
    return Response(payload, status=status_code)


def error_response(message="error", code="error", errors=None, status_code=400, request_id=None):
    payload = {
        "code": code,
        "message": message,
        "data": {},
    }
    if errors is not None:
        payload["errors"] = errors
    if request_id:
        payload["request_id"] = request_id
    return Response(payload, status=status_code)
