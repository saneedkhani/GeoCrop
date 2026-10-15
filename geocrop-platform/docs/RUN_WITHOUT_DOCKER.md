# Running without Docker

Docker is the supported way. If it is not available, run the same services natively on Ubuntu.

```bash
sudo apt install -y postgresql postgis redis-server nginx
sudo -u postgres psql -c "CREATE USER geocrop WITH PASSWORD 'geocrop';"
sudo -u postgres psql -c "CREATE DATABASE geocrop OWNER geocrop;"
sudo -u postgres psql -d geocrop -c "CREATE EXTENSION postgis;"
```

Object storage: run MinIO from a binary, or use the local-disk fallback.

`.env` changes for native services:

```
DATABASE_URL=postgresql+psycopg://geocrop:geocrop@localhost:5432/geocrop
REDIS_URL=redis://localhost:6379/0
STORAGE_BACKEND=local            # flagged on the status page
LOCAL_STORE_DIR=./data/store
TILES_INTERNAL_URL=http://localhost:8001
PUBLIC_TILE_BASE=http://localhost:5173/tiles
MODEL_DIRS=model_registry/builtin
MODEL_ARTIFACT_DIR=../data/models
```

Start, each in its own terminal (from `backend/` with the host venv plus `pip install -r requirements.txt`):

```bash
alembic upgrade head && uvicorn app.main:app --port 8000
celery -A app.workers.celery_app worker -Q ingest,models,default
cd ../tiles && API_INTERNAL_URL=http://localhost:8000/api/v1 uvicorn main:app --port 8001
cd ../web && npm run dev     # proxy targets in vite.config.ts: point them at :8000 and :8001
```

`CELERY_ALWAYS_EAGER=true` removes the need for Redis (jobs run inside the API process). It is flagged on the status page.
