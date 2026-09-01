"""
Shared dummy dataset for the GeoCrop prototype.

This is the single source of truth for both:
  - /api/fields/            (map polygons, filtered by country/state/crop_type)
  - /api/dashboard-stats/   (aggregated totals, filtered by state/region/crop_type)

Later, when the real ML pipeline exists, these two endpoints will read from the
model's output instead of this module - the filtering/aggregation logic and the
frontend code that consumes it won't need to change.
"""


def _square(center_lat, center_lng, half_width_deg=0.03):
    """Build a small square polygon (GeoJSON [lng, lat] winding order) around a center point."""
    return [[
        [center_lng - half_width_deg, center_lat - half_width_deg],
        [center_lng + half_width_deg, center_lat - half_width_deg],
        [center_lng + half_width_deg, center_lat + half_width_deg],
        [center_lng - half_width_deg, center_lat + half_width_deg],
        [center_lng - half_width_deg, center_lat - half_width_deg],
    ]]


# Crop type -> color used consistently across the map legend and polygons.
CROP_COLORS = {
    "Corn": "#f2b134",
    "Soybean": "#4c9a2a",
    "Wheat": "#d9a441",
    "Cotton": "#e8e8e8",
    "Rice": "#4aa3df",
    "Sorghum": "#b5651d",
}

FIELDS = [
    {"id": 1, "name": "Field A1", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 182.4, "yield": 178.2, "confidence": 0.94,
     "center": (41.8780, -93.0977)},
    {"id": 2, "name": "Field A2", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 145.7, "yield": 55.6, "confidence": 0.91,
     "center": (41.6005, -93.6091)},
    {"id": 3, "name": "Field B1", "country": "USA", "state": "Illinois", "region": "Midwest",
     "crop_type": "Corn", "area": 210.9, "yield": 195.4, "confidence": 0.96,
     "center": (40.6331, -89.3985)},
    {"id": 4, "name": "Field B2", "country": "USA", "state": "Illinois", "region": "Midwest",
     "crop_type": "Soybean", "area": 133.2, "yield": 58.1, "confidence": 0.89,
     "center": (39.7817, -89.6501)},
    {"id": 5, "name": "Field C1", "country": "USA", "state": "Kansas", "region": "Great Plains",
     "crop_type": "Wheat", "area": 264.5, "yield": 48.7, "confidence": 0.92,
     "center": (38.5266, -96.7265)},
    {"id": 6, "name": "Field C2", "country": "USA", "state": "Kansas", "region": "Great Plains",
     "crop_type": "Sorghum", "area": 98.3, "yield": 72.0, "confidence": 0.85,
     "center": (37.6922, -97.3375)},
    {"id": 7, "name": "Field D1", "country": "USA", "state": "Nebraska", "region": "Great Plains",
     "crop_type": "Corn", "area": 176.0, "yield": 182.9, "confidence": 0.93,
     "center": (41.4925, -99.9018)},
    {"id": 8, "name": "Field D2", "country": "USA", "state": "Nebraska", "region": "Great Plains",
     "crop_type": "Wheat", "area": 121.6, "yield": 46.3, "confidence": 0.88,
     "center": (40.8136, -96.7026)},
    {"id": 9, "name": "Field E1", "country": "USA", "state": "Texas", "region": "South",
     "crop_type": "Cotton", "area": 302.1, "yield": 820.0, "confidence": 0.90,
     "center": (33.5779, -101.8552)},
    {"id": 10, "name": "Field E2", "country": "USA", "state": "Texas", "region": "South",
     "crop_type": "Sorghum", "area": 154.8, "yield": 68.4, "confidence": 0.87,
     "center": (31.5493, -97.1467)},
    {"id": 11, "name": "Field F1", "country": "USA", "state": "California", "region": "West",
     "crop_type": "Rice", "area": 189.3, "yield": 8300.0, "confidence": 0.95,
     "center": (39.1404, -121.6169)},
    {"id": 12, "name": "Field F2", "country": "USA", "state": "California", "region": "West",
     "crop_type": "Cotton", "area": 167.5, "yield": 795.0, "confidence": 0.86,
     "center": (36.3302, -119.6922)},
    {"id": 13, "name": "Field G1", "country": "USA", "state": "Indiana", "region": "Midwest",
     "crop_type": "Corn", "area": 198.7, "yield": 188.0, "confidence": 0.94,
     "center": (40.2672, -86.1349)},
    {"id": 14, "name": "Field G2", "country": "USA", "state": "Indiana", "region": "Midwest",
     "crop_type": "Soybean", "area": 142.9, "yield": 56.9, "confidence": 0.90,
     "center": (39.7684, -86.1581)},
]


def get_all_fields():
    """Return the raw dummy field records (list of dicts)."""
    return FIELDS


def filter_fields(country=None, state=None, region=None, crop_type=None):
    """Filter the dummy dataset by any combination of country/state/region/crop_type."""
    results = FIELDS
    if country:
        results = [f for f in results if f["country"].lower() == country.lower()]
    if state:
        results = [f for f in results if f["state"].lower() == state.lower()]
    if region:
        results = [f for f in results if f["region"].lower() == region.lower()]
    if crop_type:
        results = [f for f in results if f["crop_type"].lower() == crop_type.lower()]
    return results


def fields_to_geojson(fields):
    """Convert a list of field records into a GeoJSON FeatureCollection for Leaflet."""
    features = []
    for f in fields:
        lat, lng = f["center"]
        features.append({
            "type": "Feature",
            "properties": {
                "id": f["id"],
                "name": f["name"],
                "country": f["country"],
                "state": f["state"],
                "region": f["region"],
                "crop_type": f["crop_type"],
                "area": f["area"],
                "yield": f["yield"],
                "confidence": f["confidence"],
                "color": CROP_COLORS.get(f["crop_type"], "#999999"),
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": _square(lat, lng),
            },
        })
    return {"type": "FeatureCollection", "features": features}


def aggregate_stats(fields):
    """Compute summary totals for the dashboard / results summary bar."""
    total_area = sum(f["area"] for f in fields)
    crop_types = sorted(set(f["crop_type"] for f in fields))

    by_crop = {}
    for f in fields:
        by_crop.setdefault(f["crop_type"], {"area": 0.0, "yield_x_area": 0.0})
        by_crop[f["crop_type"]]["area"] += f["area"]
        by_crop[f["crop_type"]]["yield_x_area"] += f["yield"] * f["area"]

    crop_breakdown = []
    for crop, vals in by_crop.items():
        avg_yield = vals["yield_x_area"] / vals["area"] if vals["area"] else 0
        crop_breakdown.append({
            "crop_type": crop,
            "area": round(vals["area"], 1),
            "avg_yield": round(avg_yield, 1),
            "pct_of_total_area": round((vals["area"] / total_area) * 100, 1) if total_area else 0,
        })
    crop_breakdown.sort(key=lambda c: c["area"], reverse=True)

    overall_avg_yield = (
        sum(f["yield"] * f["area"] for f in fields) / total_area if total_area else 0
    )

    return {
        "total_fields": len(fields),
        "total_crop_types": len(crop_types),
        "crop_types": crop_types,
        "total_area": round(total_area, 1),
        "avg_yield": round(overall_avg_yield, 1),
        "crop_breakdown": crop_breakdown,
    }


def get_distinct_values():
    """Distinct country/state/region/crop_type values, used to populate filter dropdowns."""
    return {
        "countries": sorted(set(f["country"] for f in FIELDS)),
        "states": sorted(set(f["state"] for f in FIELDS)),
        "regions": sorted(set(f["region"] for f in FIELDS)),
        "crop_types": sorted(set(f["crop_type"] for f in FIELDS)),
    }
