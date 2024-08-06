from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import sentry_sdk
from sentry_sdk.integrations.openai import OpenAIIntegration

from settings import SENTRY_DSN, FLASK_ENV


# setup db
db = SQLAlchemy()


def create_app(**config_overrides):
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=FLASK_ENV,
        integrations=[
            OpenAIIntegration(
                include_prompts=False
            )
        ]
    )
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return "ok"

    bare_initialisation = config_overrides.get("bare", False)

    if bare_initialisation:
        app.config.from_pyfile("settings.py")
        db.init_app(app)
        Migrate(app, db)
        return app

    from flask_cors import CORS
    from middleware.rate_limit import session_user_ratelimiter, ip_ratelimter
    from errors import register_error_handlers

    register_error_handlers(app)

    # Load config
    app.config.from_pyfile("settings.py")

    # apply overrides for tests
    app.config.update(config_overrides)

    # initialize db
    db.init_app(app)
    # migrate =
    Migrate(app, db)

    # register cors
    CORS(app, origins=['*'])

    # apply rate limit middleware
    session_user_ratelimiter.init_app(app)
    ip_ratelimter.init_app(app)

    # import blueprints
    from client.routes import client_router
    from bot.routes import bot_router
    from asset.routes import asset_router
    from session.routes import session_router

    # register blueprints
    app.register_blueprint(client_router)
    app.register_blueprint(bot_router)
    app.register_blueprint(asset_router)
    app.register_blueprint(session_router)

    return app
