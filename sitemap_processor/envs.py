import os
import sys

from dotenv import load_dotenv
from logger import logger

if os.environ.get('LOAD_FROM_ENV_FILE', '1') == '1':
    load_dotenv(override=True)

# rabbitmq
RABBITMQ_URL = os.environ.get('RABBITMQ_URL')
INPUT_QUEUE_NAME = os.environ.get('INPUT_QUEUE_NAME')
OUTPUT_QUEUE_NAME = os.environ.get('OUTPUT_QUEUE_NAME')

# postgres
DB_USERNAME = os.environ.get('DB_USERNAME')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DATABASE_NAME = os.environ.get('DATABASE_NAME')

# smartproxy
SMARTPROXY_AUTH = os.environ.get('SMARTPROXY_AUTH')

ENV = os.environ.get('ENV', 'development')
MAX_URLS_ALLOWED = int(os.environ.get('MAX_URLS_ALLOWED', 500))

SENTRY_DSN = os.environ.get('SENTRY_DSN', '')

if SMARTPROXY_AUTH is None:
    logger.error('missing env var SMARTPROXY_AUTH')
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

DB_USERNAME = DB_USERNAME.strip()
DB_PASSWORD = DB_PASSWORD.strip()
DB_HOST = DB_HOST.strip()
DB_PORT = DB_PORT.strip()
DATABASE_NAME = DATABASE_NAME.strip()
ENV = ENV.strip()
INPUT_QUEUE_NAME = INPUT_QUEUE_NAME.strip()
RABBITMQ_URL = RABBITMQ_URL.strip()
SMARTPROXY_AUTH = SMARTPROXY_AUTH.strip()
SENTRY_DSN = SENTRY_DSN.strip()
