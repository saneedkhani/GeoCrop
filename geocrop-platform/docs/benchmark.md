# Tile benchmark

Layer: Crop type (Random Forest), zoom 12, measured through nginx on this machine.

| Measure | Old prototype (GeoJSON) | New (COG tiles via TiTiler) |
|---|---|---|
| Data for one screen of AOI 1 | 43.3 MB (whole file) | 337 KB (24 tiles) |
| Objects the browser must draw | 101,435 polygons | 24 PNG images |
| Server/parse time | 1021 ms just to parse JSON (no download, no drawing) | cold tile p50 47 ms, p95 54 ms |
| Cached tile latency | n/a (no caching) | p50 1 ms, p95 1 ms (24/24 nginx HIT) |
| Typical tile size | n/a | median 2.9 KB, max 44.2 KB |
