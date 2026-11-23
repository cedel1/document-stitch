"""Fixtures for the document_stitch library tests: pre-built folders of images, properties and configs."""

from pathlib import Path

import pytest

from test.fixtures import write_image

PAGE_UUIDS = (
    "3849013e-219e-11eb-bbab-001b63bd97ba",
    "3848b31c-219e-11eb-bbab-001b63bd97ba",
    "3848da2d-219e-11eb-bbab-001b63bd97ba",
)

PROPERTIES_TEXT = """Source URL: https://example.org/view/uuid:bf33aac4
Document_uuid: uuid:bf33aac4-6c42-4af0-bc2c-2e5bc76c924f
Title: Zahlenangaben für die 12 cm
Subtitle: China 1913
Part title: 
Part subtitle: 
pages:
    uuid:3849013e-219e-11eb-bbab-001b63bd97ba
    uuid:3848b31c-219e-11eb-bbab-001b63bd97ba
    uuid:3848da2d-219e-11eb-bbab-001b63bd97ba
Page count: 3
Date: 2026-11-20 14:53:21
"""


@pytest.fixture(scope="session")
def natural_folder(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A document folder whose images only sort correctly with natural ordering."""
    folder = tmp_path_factory.mktemp("natural") / "natural-doc"
    for name in ("page2.png", "page10.png", "page1.png"):
        write_image(folder / name)
    (folder / "readme.txt").write_text("not an image")
    return folder


@pytest.fixture(scope="session")
def properties_folder(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A document folder with uuid-named images and a properties file giving a non-alphabetical page order."""
    folder = tmp_path_factory.mktemp("properties") / "props-doc"
    for page in PAGE_UUIDS:
        write_image(folder / f"{page.split('-', maxsplit=1)[0]}.jpg")
    (folder / "properties.txt").write_text(PROPERTIES_TEXT, encoding="utf-8")
    return folder


@pytest.fixture(scope="session")
def unmatched_properties_folder(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A folder with a properties file listing pages but images whose names match none of them."""
    folder = tmp_path_factory.mktemp("unmatched") / "unmatched-doc"
    for name in ("a.png", "b.png"):
        write_image(folder / name)
    (folder / "properties.txt").write_text(PROPERTIES_TEXT, encoding="utf-8")
    return folder


@pytest.fixture(scope="session")
def configured_folder(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A folder with its own configuration file."""
    folder = tmp_path_factory.mktemp("configured") / "configured-doc"
    write_image(folder / "p1.png")
    (folder / "document-stitch.toml").write_text('document-name = "from-folder"\noutput-width = 50\n')
    return folder


@pytest.fixture(scope="session")
def documents_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A directory with two document sub-folders, an empty sub-folder and a stray file."""
    root = tmp_path_factory.mktemp("collection")
    for folder in ("beta", "alpha"):
        for name in ("1.png", "2.png"):
            write_image(root / folder / name)
    (root / "empty").mkdir()
    (root / "stray.txt").write_text("ignored")
    return root


@pytest.fixture(scope="session")
def mixed_size_folder(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A folder with images of different pixel sizes (at 254 DPI, so 10 px = 1 mm)."""
    folder = tmp_path_factory.mktemp("mixed") / "mixed-doc"
    write_image(folder / "a.png", (400, 800), dpi=(254, 254))
    write_image(folder / "b.png", (1000, 500), dpi=(254, 254))
    return folder
