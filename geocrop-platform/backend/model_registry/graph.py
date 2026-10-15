"""Dependency resolution between models.

A manifest lists `requires: [imagery, cropland]` (layer kinds). Each model's
`outputs` say which kinds it produces. From that we build the execution order.
"""
from __future__ import annotations


class PlanError(ValueError):
    pass


def producers(manifests: dict[str, dict]) -> dict[str, str]:
    """Map output kind -> model key that produces it."""
    out: dict[str, str] = {}
    for key, m in manifests.items():
        for o in m.get("outputs", []):
            out.setdefault(o["kind"], key)
    return out


def execution_order(requested: list[str], manifests: dict[str, dict],
                    provided: frozenset[str] = frozenset({"imagery"})) -> list[str]:
    """Return model keys in an order where every dependency runs first.

    Raises PlanError with a readable message for unknown models, missing
    producers or cycles.
    """
    prod = producers(manifests)
    order: list[str] = []
    visiting: set[str] = set()

    def visit(key: str) -> None:
        if key in order:
            return
        if key in visiting:
            raise PlanError(f"Models depend on each other in a cycle at '{key}'.")
        if key not in manifests:
            raise PlanError(f"No registered model called '{key}'.")
        visiting.add(key)
        for kind in manifests[key].get("requires", []):
            if kind in provided:
                continue
            if kind not in prod:
                raise PlanError(f"'{key}' needs a '{kind}' layer, but no registered model produces it.")
            visit(prod[kind])
        visiting.discard(key)
        order.append(key)

    for k in requested:
        visit(k)
    return order
