# Adding a model

Models live in `backend/model_registry/builtin/` (more folders can be listed in `MODEL_DIRS`, comma-separated). The platform discovers them at startup.

## Five steps

1. **Copy the template:** `cp -r backend/model_registry/builtin/example_ndvi backend/model_registry/builtin/my_model`
2. **Edit `manifest.yaml`:** set `key`, `name`, `task`, `version`, `status: ready`, `requires` (layer kinds it needs, e.g. `[imagery, croptype]`) and `outputs` (kind, group, format `cog`, dtype, colormap).
3. **Write `run()` in `task.py`:** read `ctx.image_path` (and `ctx.upstream["croptype"]` if required), write a GeoTIFF into `ctx.out_dir`, return `RunResult(files={"my_kind": path}, class_names=..., metrics=...)`. Use `ctx.progress(fraction, message)` to report progress.
4. **Add weights** (if any) to `data/models/` and reference them from the manifest (`artifact: my_model.joblib`).
5. **Restart:** `docker compose restart api worker`. The model shows on the Models page and in Analyze Imagery. Its output becomes a layer with a legend and statistics.

No change is needed in the API, the database schema, the tile service or the frontend.

## Contract

```python
class ModelTask(ABC):
    def validate(self, ctx: RunContext) -> list[str]: ...   # readable problems, [] if OK
    def run(self, ctx: RunContext) -> RunResult: ...
```

- Categorical output: return `class_names={1: "Corn", 2: "Wheat", ...}`. Pixel value 0 is nodata.
- Continuous output: set the manifest `colormap` to a name in `model_registry/colormaps.py` (`ndvi`, `yield`) or add one.
- A model that is not ready yet: `status: stub` and subclass `StubTask`. It shows as "not implemented yet" and never produces data.

## Proof

`backend/tests/test_registry.py::test_add_a_model_by_folder_and_manifest_only` copies the example, edits only the manifest, and runs it end to end.
