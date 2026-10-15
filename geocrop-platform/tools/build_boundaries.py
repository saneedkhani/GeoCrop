"""Build the demo boundary layer: same-class regions of the crop-type raster -> PMTiles.

This is demo-grade (regions of one predicted class, minimum size filter), NOT a
field-boundary model. When a real boundary model exists, it plugs into the
registry and this script is no longer needed.

Usage:
    python tools/build_boundaries.py data/results/aoi1_croptype.tif data/results/aoi1_croptype.metrics.json data/results
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.vector_tiles import polygonize, save_geojson, write_pmtiles  # noqa: E402


def main() -> int:
    raster, metrics, out_dir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    names = json.load(open(metrics))["class_names"]
    class_names = {i + 1: n for i, n in enumerate(names)}
    feats = polygonize(raster, class_names, min_pixels=25)
    info = write_pmtiles(feats, out_dir / "aoi1_boundaries.pmtiles")
    save_geojson(feats, out_dir / "aoi1_fields.geojson")
    size = (out_dir / "aoi1_boundaries.pmtiles").stat().st_size
    print(f"{info['features']} regions, {info['tiles']} tiles, {size / 1e6:.2f} MB PMTiles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
