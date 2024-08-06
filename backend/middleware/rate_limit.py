from flask import request
from flask_limiter import Limiter

from cache import cache
from errors import CustomHTTPException


def get_session_user_key():
    user_guid = None
    session_guid = None
    # user guid will either be in request query params or in request json body
    if request.method == "GET":
        user_guid = request.args.get("user_guid")
    else:
        j = request.get_json(silent=True)
        if j is not None and type(j) == dict:
            user_guid = j.get("user_guid")

    if not user_guid:
        raise CustomHTTPException("Missing User GUID", 401)

    # session will be in request path
    session_guid = request.view_args.get(
        "session_guid") if request.view_args else None
    if not session_guid:
        raise CustomHTTPException("Missing Session GUID", 401)

    return f"{session_guid}-{user_guid}"


def get_client_ip_from_request():
    ip_from_header = request.headers.get("True-Client-Ip", default=None)

    if ip_from_header:
        return ip_from_header

    return request.remote_addr or "127.0.0.1"


pool = cache.pool

session_user_ratelimiter = Limiter(
    key_func=get_session_user_key,
    storage_uri="redis://",
    storage_options={"socket_connect_timeout": 30, "connection_pool": pool},
    strategy="moving-window",
)


ip_ratelimter = Limiter(
    key_func=get_client_ip_from_request,
    storage_uri="redis://",
    storage_options={"socket_connect_timeout": 30, "connection_pool": pool},
    strategy="moving-window",
)
