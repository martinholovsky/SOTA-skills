"""Exporter registry.

Exporters are resolved by dotted path at call time so operators can point a
deployment at a different one through configuration without a code change.
"""
import importlib


def load(dotted_path):
    """Import an exporter module by dotted path and return its `render`."""
    module = importlib.import_module(dotted_path)
    return module.render
