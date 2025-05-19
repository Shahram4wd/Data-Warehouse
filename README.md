# Data Warehouse ETL

## Setup
1. Clone the repo
2. Copy `.env.example` to `.env` and update secrets
3. Run with Docker:
```bash
docker-compose up --build
```

## CI/CD
- GitHub Actions triggers on `push` or `pull_request` to `main`/`dev`
- Runs tests and builds the Docker image