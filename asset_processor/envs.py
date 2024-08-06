import os
import sys

from dotenv import load_dotenv
from logger import logger

if os.environ.get('LOAD_FROM_ENV_FILE', '1') == '1':
    load_dotenv(override=True)

# rabbitmq
RABBITMQ_URL = os.environ.get('RABBITMQ_URL')
INPUT_QUEUE_NAME = os.environ.get('INPUT_QUEUE_NAME')

# postgres
DB_USERNAME = os.environ.get('DB_USERNAME')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DATABASE_NAME = os.environ.get('DATABASE_NAME')

# config
TMP_FOLDER_PATH = os.environ.get('TMP_FOLDER_PATH', './tmp')
ENV = os.environ.get('ENV', 'development')
# for a practice url, if more than 25% of the urls are scraped successfully
# then the asset corresponding to the practice url is considered as success
PRACTICE_URL_SUCCESS_RATE = os.environ.get('PRACTICE_URL_SUCCESS_RATE', 0.25)

# openai
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o')
CHUNK_SIZE_TOKENS = os.environ.get('CHUNK_SIZE_TOKENS', 512)
CHUNK_OVERLAP_TOKENS = os.environ.get('CHUNK_OVERLAP_TOKENS', 64)
OPENAI_EMBEDDING_MODEL = os.environ.get(
    'OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')
OPENAI_EMBEDDINGS_DIMS = os.environ.get('OPENAI_EMBEDDINGS_DIMS', 512)

# smartproxy
SMARTPROXY_AUTH = os.environ.get('SMARTPROXY_AUTH')

SENTRY_DSN = os.environ.get('SENTRY_DSN', '')

if TMP_FOLDER_PATH is None:
    logger.error('missing env var TMP_FOLDER_PATH')
    sys.exit(1)

if RABBITMQ_URL is None:
    logger.error('missing env var RABBITMQ_URL')
    sys.exit(1)

if INPUT_QUEUE_NAME is None:
    logger.error('missing env var INPUT_QUEUE_NAME')
    sys.exit(1)

if DB_USERNAME is None:
    logger.error('missing env var DB_USERNAME')
    sys.exit(1)

if DB_PASSWORD is None:
    logger.error('missing env var DB_PASSWORD')
    sys.exit(1)

if DB_HOST is None:
    logger.error('missing env var DB_HOST')
    sys.exit(1)

if DB_PORT is None:
    logger.error('missing env var DB_PORT')
    sys.exit(1)

if DATABASE_NAME is None:
    logger.error('missing env var DATABASE_NAME')
    sys.exit(1)

if OPENAI_API_KEY is None:
    logger.error('missing env var OPENAI_API_KEY')
    sys.exit(1)

if SMARTPROXY_AUTH is None:
    logger.error('missing env var SMARTPROXY_AUTH')
    sys.exit(1)

if type(CHUNK_SIZE_TOKENS) is not int:
    CHUNK_SIZE_TOKENS = int(CHUNK_SIZE_TOKENS)

if type(CHUNK_OVERLAP_TOKENS) is not int:
    CHUNK_OVERLAP_TOKENS = int(CHUNK_OVERLAP_TOKENS)

if type(OPENAI_EMBEDDINGS_DIMS) is not int:
    OPENAI_EMBEDDINGS_DIMS = int(OPENAI_EMBEDDINGS_DIMS)

if type(PRACTICE_URL_SUCCESS_RATE) is not float:
    PRACTICE_URL_SUCCESS_RATE = float(PRACTICE_URL_SUCCESS_RATE)

if PRACTICE_URL_SUCCESS_RATE > 1 or PRACTICE_URL_SUCCESS_RATE < 0:
    logger.error('PRACTICE_URL_SUCCESS_RATE should be between 0 and 1')
    sys.exit(1)

if CHUNK_OVERLAP_TOKENS >= CHUNK_SIZE_TOKENS:
    logger.error('CHUNK_OVERLAP_TOKENS should be less than CHUNK_SIZE_TOKENS')
    sys.exit(1)

SMARTPROXY_AUTH = SMARTPROXY_AUTH.strip()
OPENAI_API_KEY = OPENAI_API_KEY.strip()
DB_USERNAME = DB_USERNAME.strip()
DB_PASSWORD = DB_PASSWORD.strip()
DB_HOST = DB_HOST.strip()
DB_PORT = DB_PORT.strip()
DATABASE_NAME = DATABASE_NAME.strip()
ENV = ENV.strip()
TMP_FOLDER_PATH = TMP_FOLDER_PATH.strip()
INPUT_QUEUE_NAME = INPUT_QUEUE_NAME.strip()
RABBITMQ_URL = RABBITMQ_URL.strip()
SENTRY_DSN = SENTRY_DSN.strip()
