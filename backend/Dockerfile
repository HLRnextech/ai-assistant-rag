FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y curl

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml /app/
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project false \
    && poetry install --no-interaction

COPY . .

EXPOSE 5000

CMD poetry run gunicorn \
    --logger-class gunicorn_config.CustomGunicornLogger \
    --bind 0.0.0.0:5000 \
    --reload \
    --workers 2 \
    --threads 4 \
    --log-level info \
    wsgi:app
