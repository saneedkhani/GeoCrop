"""Discovers models from folders containing `manifest.yaml` + `task.py`."""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from model_registry.base import ModelTask
from model_registry.graph import execution_order

REQUIRED_KEYS = ("key", "name", "task", "version", "status", "entrypoint", "outputs")


class ManifestError(ValueError):
    pass


@dataclass
class RegisteredModel:
    key: str
    manifest: dict
    folder: Path
    task_cls: type[ModelTask]

    def create(self) -> ModelTask:
        return self.task_cls(self.manifest, self.folder)

    @property
    def enabled(self) -> bool:
        return bool(self.manifest.get("enabled", True))


def _load_class(folder: Path, key: str, entrypoint: str) -> type[ModelTask]:
    module_name, _, class_name = entrypoint.partition(":")
    path = folder / f"{module_name}.py"
    if not path.exists():
        raise ManifestError(f"{folder.name}: entrypoint file {path.name} not found")
    mod_id = f"geocrop_models.{key}.{module_name}"
    spec = importlib.util.spec_from_file_location(mod_id, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_id] = module
    spec.loader.exec_module(module)
    cls = getattr(module, class_name, None)
    if cls is None or not issubclass(cls, ModelTask):
        raise ManifestError(f"{folder.name}: {class_name} is not a ModelTask subclass")
    return cls


class Registry:
    def __init__(self, dirs: list[str | Path]):
        self.dirs = [Path(d) for d in dirs]
        self.models: dict[str, RegisteredModel] = {}
        self.errors: list[str] = []
        self.reload()

    def reload(self) -> None:
        self.models, self.errors = {}, []
        for d in self.dirs:
            if not d.exists():
                self.errors.append(f"Model directory not found: {d}")
                continue
            for mf in sorted(d.glob("*/manifest.yaml")):
                try:
                    manifest = yaml.safe_load(mf.read_text()) or {}
                    missing = [k for k in REQUIRED_KEYS if k not in manifest]
                    if missing:
                        raise ManifestError(f"{mf.parent.name}: manifest missing {', '.join(missing)}")
                    key = manifest["key"]
                    if key in self.models:
                        raise ManifestError(f"{mf.parent.name}: duplicate model key '{key}'")
                    cls = _load_class(mf.parent, key, manifest["entrypoint"])
                    self.models[key] = RegisteredModel(key, manifest, mf.parent, cls)
                except Exception as e:  # one broken model must not take the platform down
                    self.errors.append(str(e))

    def get(self, key: str) -> RegisteredModel:
        return self.models[key]

    def list(self, include_disabled: bool = True) -> list[RegisteredModel]:
        return [m for m in self.models.values() if include_disabled or m.enabled]

    def plan(self, requested: list[str]) -> list[str]:
        manifests = {k: m.manifest for k, m in self.models.items() if m.enabled}
        return execution_order(requested, manifests)
