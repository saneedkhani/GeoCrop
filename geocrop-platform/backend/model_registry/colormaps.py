"""Named colour maps and helpers that turn class names into a layer style + legend.

Styles are stored on the layer row and applied by the tile service, so the
frontend never hard-codes colours for a model.
"""
from __future__ import annotations

# Qualitative palette for crop classes (colour-blind aware order first).
QUALITATIVE = [
    "#e6a817", "#2e7d32", "#7b5ea7", "#d1495b", "#1f77b4", "#8c564b", "#17becf",
    "#bcbd22", "#e377c2", "#ff7f0e", "#9467bd", "#2ca02c", "#aec7e8", "#ffbb78",
    "#98df8a", "#c5b0d5", "#c49c94", "#f7b6d2", "#dbdb8d", "#9edae5",
]

NAMED = {
    "cropland_default": {1: ("#3f8f3a", "Cropland"), 2: ("#d8c79a", "Non-cropland")},
}

CONTINUOUS = {
    "ndvi": {"colormap_name": "rdylgn", "rescale": [-0.1, 0.9], "label": "NDVI"},
    "yield": {"colormap_name": "viridis", "rescale": [0, 250], "label": "bu/acre"},
}


def categorical(class_names: dict[int, str], colormap: str | None = None) -> tuple[dict, list]:
    """Return (style, legend) for a categorical raster."""
    named = NAMED.get(colormap or "", {})
    style_map, legend = {}, []
    for i, code in enumerate(sorted(class_names)):
        color, label = named.get(code, (QUALITATIVE[i % len(QUALITATIVE)], class_names[code]))
        label = class_names.get(code, label)
        style_map[str(code)] = color
        legend.append({"code": code, "label": label, "color": color})
    return {"type": "categorical", "colormap": style_map}, legend


def continuous(name: str, band: int = 1) -> tuple[dict, list]:
    c = CONTINUOUS[name]
    style = {"type": "continuous", "bidx": [band], "rescale": c["rescale"], "colormap_name": c["colormap_name"]}
    legend = [{"label": f"{c['label']} {c['rescale'][0]} to {c['rescale'][1]}", "ramp": c["colormap_name"],
               "min": c["rescale"][0], "max": c["rescale"][1]}]
    return style, legend


def rgb(bidx: list[int], rescale: list[float]) -> tuple[dict, list]:
    return {"type": "rgb", "bidx": bidx, "rescale": rescale}, [{"label": "True colour (B4, B3, B2)"}]


def style_for_output(output: dict, class_names: dict[int, str] | None) -> tuple[dict, list]:
    """Pick the style for a model output from its manifest entry."""
    cmap = output.get("colormap", "")
    if cmap in CONTINUOUS:
        return continuous(cmap)
    if class_names:
        return categorical(class_names, cmap)
    return continuous("ndvi")
