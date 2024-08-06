import json
from flask import jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException


class CustomHTTPException(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['error'] = self.message
        return rv


def register_error_handlers(app):
    @app.errorhandler(CustomHTTPException)
    def handle_http_exception(e):
        return jsonify(e.to_dict()), e.status_code

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError):
        return jsonify({
            "error": e.messages
        }), 422

    @app.errorhandler(HTTPException)
    def handle_exception(e):
        """Return JSON instead of HTML for HTTP errors."""
        # start with the correct headers and status code from the error
        response = e.get_response()
        # replace the body with JSON
        response.data = json.dumps({
            "error": e.description,
        })
        response.content_type = "application/json"
        return response

    @app.errorhandler(429)
    def handle_rate_limit(e):
        return jsonify({
            "error": "Rate limit exceeded"
        }), 429
