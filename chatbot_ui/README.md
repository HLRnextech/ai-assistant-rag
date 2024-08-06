Dev Setup:

1. `cp .env.example .env.docker`
2. That's it! You're ready to go!

Prod setup:

1. `cp .env.example .env`
2. `cp deploy/.env.example deploy/.env`
3. Setup the required AWS credentials in `deploy/.env`
4. `Dockerfile` for production will build and deploy static assets to the configured S3 bucket
