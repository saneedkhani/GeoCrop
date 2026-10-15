#!/bin/sh
# Create the bucket and allow anonymous READ of vector tiles (PMTiles are fetched by the browser).
# MinIO can report healthy a moment before it accepts connections (the Bitnami image
# restarts it once on boot), so retry the first connection instead of failing.
set -e
export MC_CONFIG_DIR=/tmp/.mc
MC=/opt/bitnami/minio-client/bin/mc
for i in $(seq 1 30); do
  if $MC alias set local http://minio:9000 "$S3_ACCESS_KEY" "$S3_SECRET_KEY" >/dev/null 2>&1; then
    break
  fi
  echo "Waiting for MinIO ($i/30)..."
  sleep 2
done
$MC alias set local http://minio:9000 "$S3_ACCESS_KEY" "$S3_SECRET_KEY"
$MC mb --ignore-existing "local/$S3_BUCKET"
$MC anonymous set download "local/$S3_BUCKET/vector"
echo "MinIO bucket $S3_BUCKET ready"
