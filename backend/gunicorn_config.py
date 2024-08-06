from gunicorn import glogging


class CustomGunicornLogger(glogging.Logger):
    def access(self, resp, req, environ, request_time):
        if req.path in ["/health"]:
            return
        super().access(resp, req, environ, request_time)
