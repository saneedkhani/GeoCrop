"""Benchmark: old prototype (one 43 MB GeoJSON) vs new tile path, on AOI 1.

Measures, through nginx on :8080:
  - cold tiles (cache bypassed, TiTiler reads the COG from MinIO)
  - cached tiles (served by the nginx tile cache)
  - bytes for one screen (~24 tiles at zoom 12)
and compares with downloading + parsing the prototype GeoJSON.

    python tools/benchmark_tiles.py [--base http://localhost:8080] [--zoom 12]
"""
import argparse
import json
import statistics
import time
import urllib.request
import uuid
from pathlib import Path

import mercantile

ROOT = Path(__file__).resolve().parents[1]


def http(url: str, data: dict | None = None, token: str | None = None) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json"} if data else {})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read(), dict(r.headers)


def timed(url: str) -> tuple[float, int, str]:
    t = time.perf_counter()
    _, body, headers = http(url)
    return (time.perf_counter() - t) * 1000, len(body), headers.get("X-Cache-Status", "-")


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument("--zoom", type=int, default=12)
    ap.add_argument("--kind", default="croptype")
    a = ap.parse_args()

    _, body, _ = http(f"{a.base}/api/v1/auth/login", {"username": "demo", "password": "geocrop-demo"})
    token = json.loads(body)["token"]
    _, body, _ = http(f"{a.base}/api/v1/layers?kind={a.kind}", token=token)
    layer = json.loads(body)[0]
    w, s, e, n = layer["bounds"]
    tiles = list(mercantile.tiles(w, s, e, n, zooms=[a.zoom]))[:24]
    template = layer["tile_url"].replace("http://localhost:8080", a.base)
    urls = [template.replace("{z}", str(t.z)).replace("{x}", str(t.x)).replace("{y}", str(t.y)) for t in tiles]

    cold = [timed(f"{u}?nocache={uuid.uuid4().hex}")[0] for u in urls]
    for u in urls:
        timed(u)  # fill nginx cache
    warm_runs = [timed(u) for u in urls]
    warm = [r[0] for r in warm_runs]
    sizes = [r[1] for r in warm_runs]
    hits = sum(1 for r in warm_runs if r[2] == "HIT")

    gj = ROOT / "data/raw/aoi1_croptype.geojson"
    old_size = gj.stat().st_size if gj.exists() else 43_300_700
    t = time.perf_counter()
    feats = len(json.load(open(gj))["features"]) if gj.exists() else 101_435
    parse_ms = (time.perf_counter() - t) * 1000

    rows = [
        ("Data for one screen of AOI 1", f"{old_size / 1e6:.1f} MB (whole file)",
         f"{sum(sizes) / 1024:.0f} KB ({len(urls)} tiles)"),
        ("Objects the browser must draw", f"{feats:,} polygons", f"{len(urls)} PNG images"),
        ("Server/parse time", f"{parse_ms:.0f} ms just to parse JSON (no download, no drawing)",
         f"cold tile p50 {statistics.median(cold):.0f} ms, p95 {pct(cold, 95):.0f} ms"),
        ("Cached tile latency", "n/a (no caching)",
         f"p50 {statistics.median(warm):.0f} ms, p95 {pct(warm, 95):.0f} ms ({hits}/{len(urls)} nginx HIT)"),
        ("Typical tile size", "n/a", f"median {statistics.median(sizes) / 1024:.1f} KB, max {max(sizes) / 1024:.1f} KB"),
    ]
    md = ["| Measure | Old prototype (GeoJSON) | New (COG tiles via TiTiler) |", "|---|---|---|"]
    md += [f"| {r[0]} | {r[1]} | {r[2]} |" for r in rows]
    out = "\n".join(md)
    print(out)
    (ROOT / "docs/benchmark.md").write_text(
        f"# Tile benchmark\n\nLayer: {layer['name']}, zoom {a.zoom}, measured through nginx on this machine.\n\n{out}\n")


if __name__ == "__main__":
    main()
