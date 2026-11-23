"""Tests for document_stitch.layout."""

# pylint: disable=redefined-outer-name,unused-import
from pathlib import Path

import pytest

from document_stitch.layout import POINTS_PER_MM, ImageGeometry, PageLayout, compute_layout, read_geometry
from test.fixtures import write_image

MM = POINTS_PER_MM
SMALL = ImageGeometry(10 * MM, 20 * MM)
LARGE = ImageGeometry(200 * MM, 100 * MM)


def in_mm(layout: PageLayout) -> tuple[float, ...]:
    """Converts a layout to rounded millimetres."""
    return tuple(round(value / MM, 3) for value in layout.as_tuple())


def test_read_geometry_should_use_embedded_dpi(tmp_path: Path) -> None:
    """Size in points comes from pixels and the embedded DPI."""
    path = write_image(tmp_path / "a.png", (720, 360), dpi=(72, 72))
    geometry = read_geometry(path)
    assert (geometry.width, geometry.height) == pytest.approx((720, 360), rel=1e-3)


def test_read_geometry_should_default_to_300_dpi_without_embedded_dpi(tmp_path: Path) -> None:
    """Images without DPI are treated as 300 DPI."""
    path = write_image(tmp_path / "a.png", (300, 600))
    assert read_geometry(path) == ImageGeometry(72, 144)


def test_compute_layout_should_match_image_without_dimensions() -> None:
    """The original size is kept by default."""
    assert in_mm(compute_layout(SMALL, None, None)) == (10, 20, 10, 20)


def test_compute_layout_should_scale_to_width_keeping_aspect_ratio() -> None:
    """Only a width: height follows the aspect ratio."""
    assert in_mm(compute_layout(SMALL, 50, None)) == (50, 100, 50, 100)


def test_compute_layout_should_scale_to_height_keeping_aspect_ratio() -> None:
    """Only a height: width follows the aspect ratio."""
    assert in_mm(compute_layout(SMALL, None, 40)) == (20, 40, 20, 40)


def test_compute_layout_should_centre_smaller_image_at_natural_size() -> None:
    """A small image keeps its size on a larger page."""
    assert in_mm(compute_layout(SMALL, 100, 100)) == (100, 100, 10, 20)


def test_compute_layout_should_stretch_smaller_image_when_allowed() -> None:
    """Stretching fills the page exactly."""
    assert in_mm(compute_layout(SMALL, 100, 100, allow_stretching=True)) == (100, 100, 100, 100)


def test_compute_layout_should_fit_larger_image_inside_page() -> None:
    """A large image is scaled down to fit."""
    assert in_mm(compute_layout(LARGE, 100, 100)) == (100, 100, 100, 50)


def test_compute_layout_should_cover_page_with_larger_image_when_cropping() -> None:
    """With cropping the smaller side matches the page and the overflow is cropped."""
    assert in_mm(compute_layout(LARGE, 100, 100, allow_cropping=True)) == (100, 100, 200, 100)


def test_compute_layout_should_not_crop_smaller_image_when_cropping_allowed() -> None:
    """Cropping does not affect images that fit."""
    assert in_mm(compute_layout(SMALL, 100, 100, allow_cropping=True)) == (100, 100, 10, 20)


def test_page_layout_should_return_tuple_of_four_values() -> None:
    """as_tuple lists page size then image size."""
    assert PageLayout(1, 2, 3, 4).as_tuple() == (1, 2, 3, 4)
