#!/usr/bin/env bash
# Copy the AOI 1 demo inputs from the old prototype into ./data (gitignored).
set -euo pipefail
SRC="${PROTOTYPE_DIR:-/home/huzaifa/Downloads/zzzzzzzzzzzzz/fast_shared}"
DST="$(cd "$(dirname "$0")/.." && pwd)/data/raw"
mkdir -p "$DST"
cp -v "$SRC/aoi1_sentinel2.tif" "$DST/"
cp -v "$SRC/crop_data_layer/usa_cdl_aoi1.tif" "$DST/"
cp -v "$SRC"/Pl_usa_aoi1_wgs84.* "$DST/"
cp -v "$SRC/aoi1_cropland.geojson" "$SRC/aoi1_croptype.geojson" "$DST/" || true
echo "Demo data ready in $DST"
