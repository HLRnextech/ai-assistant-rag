Dev Setup:

1. `cp .env.example .env.docker`
2. Make sure to provide `OPENAI_API_KEY`
3. If db migration is needed, see the `DB Initialisation` section below.

App accessible at `localhost:5001`

DB Initialisation:

```bash
# run inside the backend container
poetry run flask db init # one time

poetry run flask db migrate -m "message" # any time a change is done in schema

poetry run flask db upgrade # sync db
```

Running tests:

```bash
# run inside the backend container
poetry run pytest -s
```
