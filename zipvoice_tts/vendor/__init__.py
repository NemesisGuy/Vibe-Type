"""Vendored copy of the ZipVoice package for standalone streaming use."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Optional


def ensure_vendor_zipvoice() -> ModuleType:
    """Ensure the vendored ``zipvoice`` package is importable.

    If an external installation of ``zipvoice`` is already available, this
    function leaves it untouched. Otherwise it registers the vendored copy so
    that absolute imports like ``import zipvoice`` resolve correctly.
    """

    try:
        return importlib.import_module("zipvoice")
    except ModuleNotFoundError:
        pass

    vendor_pkg = importlib.import_module("zipvoice_tts.vendor.zipvoice")
    sys.modules.setdefault("zipvoice", vendor_pkg)
    return vendor_pkg


__all__ = ["ensure_vendor_zipvoice"]
