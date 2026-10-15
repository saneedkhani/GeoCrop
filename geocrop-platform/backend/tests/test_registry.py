"""Model registry tests, including the flexibility acceptance test:
a new model is added by copying a folder and editing only its manifest."""
import shutil
from pathlib import Path

import numpy as np
import pytest
import rasterio
import yaml
from rasterio.transform import from_origin

from model_registry.base import RunContext
from model_registry.graph import PlanError, execution_order
from model_registry.registry import Registry

BUILTIN = Path(__file__).resolve().parents[1] / "model_registry" / "builtin"


def test_builtin_models_load_without_errors():
    reg = Registry([BUILTIN])
    assert reg.errors == []
    assert {"cropland", "croptype", "boundary", "yield", "example_ndvi"} <= set(reg.models)


def test_dependencies_resolve_in_order():
    reg = Registry([BUILTIN])
    assert reg.plan(["croptype"]) == ["cropland", "croptype"]
    assert reg.plan(["yield"]) == ["cropland", "croptype", "yield"]


def test_unknown_and_cyclic_models_give_readable_errors():
    with pytest.raises(PlanError, match="No registered model"):
        execution_order(["nope"], {})
    cyc = {"a": {"requires": ["b_out"], "outputs": [{"kind": "a_out"}]},
           "b": {"requires": ["a_out"], "outputs": [{"kind": "b_out"}]}}
    with pytest.raises(PlanError, match="cycle"):
        execution_order(["a"], cyc)


def _tiny_s2(path: Path) -> None:
    data = np.random.default_rng(0).integers(200, 4000, size=(7, 64, 64)).astype("float32")
    with rasterio.open(path, "w", driver="GTiff", width=64, height=64, count=7, dtype="float32",
                       crs="EPSG:5070", transform=from_origin(-1_900_000, 2_900_000, 30, 30)) as dst:
        dst.write(data)


def test_stub_models_never_fabricate_data(tmp_path):
    reg = Registry([BUILTIN])
    img = tmp_path / "img.tif"
    _tiny_s2(img)
    ctx = RunContext(run_id="t", image_path=str(img), upstream={}, out_dir=tmp_path,
                     artifact_dir=tmp_path, manifest=reg.get("yield").manifest)
    result = reg.get("yield").create().run(ctx)
    assert result.status == "not_available" and result.files == {}


def test_add_a_model_by_folder_and_manifest_only(tmp_path):
    """Acceptance test 8.5: copy the example, change only manifest key/name, and it works."""
    plugins = tmp_path / "plugins"
    shutil.copytree(BUILTIN / "example_ndvi", plugins / "my_index")
    mf_path = plugins / "my_index" / "manifest.yaml"
    mf = yaml.safe_load(mf_path.read_text())
    mf["key"], mf["name"] = "my_index", "My vegetation index"
    mf["outputs"][0]["kind"] = "my_index"
    mf_path.write_text(yaml.safe_dump(mf))

    reg = Registry([BUILTIN, plugins])
    assert reg.errors == []
    assert "my_index" in reg.models
    assert reg.plan(["my_index"]) == ["my_index"]

    img = tmp_path / "img.tif"
    _tiny_s2(img)
    out = tmp_path / "out"
    out.mkdir()
    ctx = RunContext(run_id="t", image_path=str(img), upstream={}, out_dir=out, artifact_dir=tmp_path,
                     manifest=reg.get("my_index").manifest)
    result = reg.get("my_index").create().run(ctx)
    assert set(result.files) == {"my_index"}
    with rasterio.open(result.files["my_index"]) as ds:
        arr = ds.read(1)
        assert ds.dtypes[0] == "float32" and np.nanmax(arr) <= 1.0
