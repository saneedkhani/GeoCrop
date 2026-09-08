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

    # Dense cluster of additional Iowa fields (Story County area) so the live map
    # shows many adjacent boundaries within a single state, like a real patchwork
    # of neighboring fields, instead of just one or two per state.
    {"id": 15, "name": "Field A3", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 239.7, "yield": 192.1, "confidence": 0.96,
     "center": (41.8491, -93.8058), "size": 0.0218},
    {"id": 16, "name": "Field A4", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 191.1, "yield": 166.1, "confidence": 0.91,
     "center": (41.8447, -93.7506), "size": 0.0209},
    {"id": 17, "name": "Field A5", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 255.0, "yield": 48.1, "confidence": 0.94,
     "center": (41.8492, -93.6976), "size": 0.0216},
    {"id": 18, "name": "Field A6", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Cotton", "area": 155.7, "yield": 766.5, "confidence": 0.85,
     "center": (41.8496, -93.6473), "size": 0.0214},
    {"id": 19, "name": "Field A7", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 197.6, "yield": 61.6, "confidence": 0.91,
     "center": (41.8508, -93.5932), "size": 0.0237},
    {"id": 20, "name": "Field A8", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Sorghum", "area": 206.2, "yield": 73.3, "confidence": 0.83,
     "center": (41.8484, -93.5394), "size": 0.0231},
    {"id": 21, "name": "Field A9", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 106.2, "yield": 176.1, "confidence": 0.94,
     "center": (41.8458, -93.4917), "size": 0.0211},
    {"id": 22, "name": "Field A10", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 281.7, "yield": 190.9, "confidence": 0.94,
     "center": (41.8469, -93.439), "size": 0.0216},
    {"id": 23, "name": "Field A11", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 292.8, "yield": 190.6, "confidence": 0.94,
     "center": (41.8974, -93.8002), "size": 0.0214},
    {"id": 24, "name": "Field A12", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 91.7, "yield": 177.6, "confidence": 0.92,
     "center": (41.9015, -93.7473), "size": 0.0236},
    {"id": 25, "name": "Field A13", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 222.6, "yield": 180.8, "confidence": 0.96,
     "center": (41.8977, -93.6945), "size": 0.024},
    {"id": 26, "name": "Field A14", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 140.2, "yield": 56.2, "confidence": 0.95,
     "center": (41.8997, -93.6479), "size": 0.0217},
    {"id": 27, "name": "Field A15", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 104.1, "yield": 48.7, "confidence": 0.89,
     "center": (41.8992, -93.5962), "size": 0.0244},
    {"id": 28, "name": "Field A16", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 165.1, "yield": 204.8, "confidence": 0.94,
     "center": (41.901, -93.5397), "size": 0.0223},
    {"id": 29, "name": "Field A17", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 228.2, "yield": 55.5, "confidence": 0.9,
     "center": (41.9038, -93.4871), "size": 0.0208},
    {"id": 30, "name": "Field A18", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 285.3, "yield": 60.3, "confidence": 0.9,
     "center": (41.9011, -93.4411), "size": 0.0224},
    {"id": 31, "name": "Field A19", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Sorghum", "area": 147.7, "yield": 72.2, "confidence": 0.88,
     "center": (41.952, -93.8046), "size": 0.0241},
    {"id": 32, "name": "Field A20", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Wheat", "area": 196.4, "yield": 42.0, "confidence": 0.88,
     "center": (41.9492, -93.7479), "size": 0.0228},
    {"id": 33, "name": "Field A21", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Sorghum", "area": 149.6, "yield": 62.9, "confidence": 0.91,
     "center": (41.9482, -93.6946), "size": 0.024},
    {"id": 34, "name": "Field A22", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 244.7, "yield": 195.6, "confidence": 0.91,
     "center": (41.9556, -93.6493), "size": 0.0226},
    {"id": 35, "name": "Field A23", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Sorghum", "area": 173.9, "yield": 65.4, "confidence": 0.88,
     "center": (41.9518, -93.5936), "size": 0.0218},
    {"id": 36, "name": "Field A24", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Rice", "area": 221.5, "yield": 8319.1, "confidence": 0.9,
     "center": (41.9538, -93.5444), "size": 0.0219},
    {"id": 37, "name": "Field A25", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 133.3, "yield": 51.1, "confidence": 0.89,
     "center": (41.949, -93.4922), "size": 0.022},
    {"id": 38, "name": "Field A26", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Sorghum", "area": 99.9, "yield": 65.8, "confidence": 0.89,
     "center": (41.953, -93.4402), "size": 0.0241},
    {"id": 39, "name": "Field A27", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 184.3, "yield": 59.0, "confidence": 0.94,
     "center": (42.0017, -93.8049), "size": 0.0242},
    {"id": 40, "name": "Field A28", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 183.1, "yield": 58.2, "confidence": 0.93,
     "center": (42.0015, -93.7532), "size": 0.0224},
    {"id": 41, "name": "Field A29", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 266.0, "yield": 174.9, "confidence": 0.91,
     "center": (42.0079, -93.7012), "size": 0.0223},
    {"id": 42, "name": "Field A30", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 278.9, "yield": 182.7, "confidence": 0.96,
     "center": (42.0036, -93.6466), "size": 0.0218},
    {"id": 43, "name": "Field A31", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Sorghum", "area": 288.5, "yield": 76.8, "confidence": 0.91,
     "center": (42.0044, -93.5976), "size": 0.0244},
    {"id": 44, "name": "Field A32", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 97.3, "yield": 53.3, "confidence": 0.96,
     "center": (42.0013, -93.5421), "size": 0.0216},
    {"id": 45, "name": "Field A33", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 286.0, "yield": 61.9, "confidence": 0.92,
     "center": (42.0021, -93.4877), "size": 0.0225},
    {"id": 46, "name": "Field A34", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Rice", "area": 206.6, "yield": 8371.1, "confidence": 0.92,
     "center": (42.0057, -93.4408), "size": 0.0219},
    {"id": 47, "name": "Field A35", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Sorghum", "area": 118.1, "yield": 77.4, "confidence": 0.84,
     "center": (42.0525, -93.8013), "size": 0.0226},
    {"id": 48, "name": "Field A36", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 110.2, "yield": 200.6, "confidence": 0.92,
     "center": (42.0535, -93.7492), "size": 0.0233},
    {"id": 49, "name": "Field A37", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 194.8, "yield": 61.1, "confidence": 0.9,
     "center": (42.0568, -93.697), "size": 0.0223},
    {"id": 50, "name": "Field A38", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 148.0, "yield": 52.4, "confidence": 0.94,
     "center": (42.0577, -93.6481), "size": 0.0222},
    {"id": 51, "name": "Field A39", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Rice", "area": 100.4, "yield": 8206.6, "confidence": 0.88,
     "center": (42.0526, -93.5943), "size": 0.0244},
    {"id": 52, "name": "Field A40", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 118.1, "yield": 198.3, "confidence": 0.95,
     "center": (42.0595, -93.539), "size": 0.024},
    {"id": 53, "name": "Field A41", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 256.6, "yield": 177.0, "confidence": 0.95,
     "center": (42.0569, -93.4861), "size": 0.0232},
    {"id": 54, "name": "Field A42", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 201.2, "yield": 175.9, "confidence": 0.94,
     "center": (42.0595, -93.4409), "size": 0.0212},
    {"id": 55, "name": "Field A43", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 187.6, "yield": 201.2, "confidence": 0.96,
     "center": (42.1097, -93.8044), "size": 0.0231},
    {"id": 56, "name": "Field A44", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 246.9, "yield": 190.5, "confidence": 0.92,
     "center": (42.1047, -93.7506), "size": 0.0218},
    {"id": 57, "name": "Field A45", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 100.8, "yield": 200.3, "confidence": 0.96,
     "center": (42.1099, -93.6976), "size": 0.0224},
    {"id": 58, "name": "Field A46", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 111.8, "yield": 177.3, "confidence": 0.96,
     "center": (42.1084, -93.6433), "size": 0.0229},
    {"id": 59, "name": "Field A47", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 137.4, "yield": 169.1, "confidence": 0.95,
     "center": (42.1104, -93.5911), "size": 0.0241},
    {"id": 60, "name": "Field A48", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 280.3, "yield": 199.6, "confidence": 0.97,
     "center": (42.1111, -93.5427), "size": 0.0231},
    {"id": 61, "name": "Field A49", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Wheat", "area": 154.8, "yield": 51.3, "confidence": 0.91,
     "center": (42.1105, -93.4869), "size": 0.0209},
    {"id": 62, "name": "Field A50", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Wheat", "area": 107.7, "yield": 50.7, "confidence": 0.92,
     "center": (42.1109, -93.4355), "size": 0.0218},
    {"id": 63, "name": "Field A51", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 252.0, "yield": 174.1, "confidence": 0.9,
     "center": (42.1578, -93.7995), "size": 0.0225},
    {"id": 64, "name": "Field A52", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Rice", "area": 143.6, "yield": 8420.7, "confidence": 0.89,
     "center": (42.1575, -93.7514), "size": 0.0239},
    {"id": 65, "name": "Field A53", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 288.8, "yield": 172.1, "confidence": 0.97,
     "center": (42.1638, -93.6977), "size": 0.0242},
    {"id": 66, "name": "Field A54", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 150.9, "yield": 56.5, "confidence": 0.92,
     "center": (42.1581, -93.6491), "size": 0.0224},
    {"id": 67, "name": "Field A55", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 85.4, "yield": 61.0, "confidence": 0.92,
     "center": (42.1591, -93.5934), "size": 0.0217},
    {"id": 68, "name": "Field A56", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 99.7, "yield": 191.6, "confidence": 0.92,
     "center": (42.1618, -93.5401), "size": 0.0232},
    {"id": 69, "name": "Field A57", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 149.9, "yield": 181.3, "confidence": 0.93,
     "center": (42.1585, -93.4872), "size": 0.0234},
    {"id": 70, "name": "Field A58", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Cotton", "area": 227.2, "yield": 823.2, "confidence": 0.9,
     "center": (42.1584, -93.441), "size": 0.0223},
    {"id": 71, "name": "Field A59", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 175.3, "yield": 188.2, "confidence": 0.95,
     "center": (42.2104, -93.8016), "size": 0.0208},
    {"id": 72, "name": "Field A60", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 274.2, "yield": 59.1, "confidence": 0.89,
     "center": (42.2117, -93.7505), "size": 0.0216},
    {"id": 73, "name": "Field A61", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 256.9, "yield": 195.0, "confidence": 0.95,
     "center": (42.2087, -93.6979), "size": 0.0231},
    {"id": 74, "name": "Field A62", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 184.8, "yield": 199.0, "confidence": 0.91,
     "center": (42.2098, -93.6484), "size": 0.0209},
    {"id": 75, "name": "Field A63", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Soybean", "area": 188.8, "yield": 51.4, "confidence": 0.93,
     "center": (42.2113, -93.593), "size": 0.0215},
    {"id": 76, "name": "Field A64", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Corn", "area": 174.3, "yield": 172.0, "confidence": 0.97,
     "center": (42.208, -93.54), "size": 0.0236},
    {"id": 77, "name": "Field A65", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Sorghum", "area": 180.9, "yield": 74.8, "confidence": 0.89,
     "center": (42.2121, -93.4936), "size": 0.0217},
    {"id": 78, "name": "Field A66", "country": "USA", "state": "Iowa", "region": "Midwest",
     "crop_type": "Sorghum", "area": 213.7, "yield": 73.5, "confidence": 0.88,
     "center": (42.2159, -93.4372), "size": 0.0243},
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
                "coordinates": _square(lat, lng, f.get("size", 0.03)),
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
