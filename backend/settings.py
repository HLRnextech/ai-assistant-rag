import os

# config
FLASK_APP = os.environ["FLASK_APP"]
FLASK_ENV = os.environ["FLASK_ENV"]
API_KEY = os.environ["API_KEY"]
MAX_BYTES_TO_READ_FOR_MIME_TYPE = 2048
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB

# db
DB_USERNAME = os.environ["DB_USERNAME"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_HOST = os.environ["DB_HOST"]
DB_PORT = os.environ["DB_PORT"]
DATABASE_NAME = os.environ["DATABASE_NAME"]
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = (
    f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DATABASE_NAME}"
)

# aws
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_ENDPOINT_URL = os.environ["AWS_ENDPOINT_URL"]
AWS_REGION = os.environ["AWS_REGION"]
S3_BUCKET = os.environ["S3_BUCKET"]
CLOUDFRONT_URL = os.environ.get("CLOUDFRONT_URL", "")
# SQLALCHEMY_ECHO = True

# rabbitmq
RABBITMQ_URL = os.environ["RABBITMQ_URL"]
ASSET_PROCESSOR_QUEUE_NAME = os.environ["ASSET_PROCESSOR_QUEUE_NAME"]
SITEMAP_PROCESSOR_QUEUE_NAME = os.environ["SITEMAP_PROCESSOR_QUEUE_NAME"]

# redis
REDIS_URL = os.environ["REDIS_URL"]

# openai
OPENAI_MODEL = os.environ["OPENAI_MODEL"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
# must be same as asset_processor/envs.py
OPENAI_EMBEDDING_MODEL = os.environ["OPENAI_EMBEDDING_MODEL"]
OPENAI_EMBEDDINGS_DIMS = int(os.environ["OPENAI_EMBEDDINGS_DIMS"])

# static asset
CHATBOT_JS_ASSET_URL = os.environ["CHATBOT_JS_ASSET_URL"]
CHATBOT_CSS_ASSET_URL = os.environ["CHATBOT_CSS_ASSET_URL"]

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

# if FLASK_ENV == "production" and CLOUDFRONT_URL == "":
#     raise Exception("CLOUDFRONT_URL must be set in production environment")
