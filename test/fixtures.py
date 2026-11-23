"""Fixtures and helpers shared by all tests."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def write_image(path: Path, size: tuple[int, int] = (100, 200), dpi: tuple[int, int] | None = None) -> Path:
    """Writes a small image whose format follows the file extension."""
    path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {"dpi": dpi} if dpi else {}
    Image.new("RGB", size, "white").save(path, **kwargs)
    return path


@pytest.fixture(scope="session")
def cli_module() -> ModuleType:
    """Loads the root script, whose file name clashes with the package name, under a different module name."""
    spec = importlib.util.spec_from_file_location("document_stitch_cli", ROOT / "document_stitch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
