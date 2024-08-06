import sentry_sdk


def capture_exception(e, metadata=None):
    if metadata is None:
        sentry_sdk.capture_exception(e)
    else:
        with sentry_sdk.push_scope() as scope:
            for key, value in metadata.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(e)
