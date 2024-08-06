from functools import wraps
from flask import request
from flask import current_app

from errors import CustomHTTPException


def api_key_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = None
        if "x-api-key" in request.headers:
            api_key = request.headers["x-api-key"]
        if not api_key:
            raise CustomHTTPException("Missing API Key", 401)

        if api_key != current_app.config["API_KEY"]:
            raise CustomHTTPException("Invalid API Key", 401)

        return f(*args, **kwargs)

    return decorated
