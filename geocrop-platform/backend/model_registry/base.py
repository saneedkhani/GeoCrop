"""The contract every GeoCrop model implements.

A model is a folder with `manifest.yaml` and `task.py`. The platform discovers it,
resolves its dependencies, runs it in a worker and turns its outputs into map
layers and statistics. Nothing else in the code base needs to know it exists.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunContext:
    run_id: str
    image_path: str                       # preprocessed input raster (local path or /vsis3/...)
    upstream: dict[str, str]              # layer kind -> raster path produced earlier in this run
    out_dir: Path                         # scratch folder for this model's outputs
    artifact_dir: Path                    # where trained model files (joblib, weights) live
    manifest: dict
    params: dict = field(default_factory=dict)
    progress: Callable[[float, str], None] = lambda fraction, message: None


@dataclass
class RunResult:
    files: dict[str, Path]                # output kind -> raster/vector file written by the model
    metrics: dict = field(default_factory=dict)
    class_names: dict[int, str] | None = None   # pixel value -> label, for categorical outputs
    status: str = "done"                  # "done" | "not_available"
    message: str = ""


class ModelTask(ABC):
    """Subclass this in task.py and point the manifest's `entrypoint` at it."""

    def __init__(self, manifest: dict, folder: Path):
        self.manifest = manifest
        self.folder = folder
        self.key: str = manifest["key"]

    def validate(self, ctx: RunContext) -> list[str]:
        """Return readable problems with the input. Empty list means it can run."""
        return []

    @abstractmethod
    def run(self, ctx: RunContext) -> RunResult: ...


class StubTask(ModelTask):
    """Registered but not implemented yet. Never fabricates data."""

    def run(self, ctx: RunContext) -> RunResult:
        return RunResult(files={}, status="not_available",
                         message=f"{self.manifest.get('name', self.key)} is registered but not implemented yet.")
