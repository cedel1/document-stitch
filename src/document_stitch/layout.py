"""Page geometry: how an image is placed on a page of the output document."""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

DEFAULT_DPI = 300.0
POINTS_PER_MM = 72 / 25.4


@dataclass(frozen=True)
class ImageGeometry:
    """Size of an image in PDF points (1/72 inch).

    Attributes:
        width: Natural width.
        height: Natural height.
    """

    width: float
    height: float


@dataclass(frozen=True)
class PageLayout:
    """Placement of an image on a page, all values in PDF points.

    Attributes:
        page_width: Width of the page.
        page_height: Height of the page.
        image_width: Width the image is drawn at; may exceed the page, in which case the overflow is cropped.
        image_height: Height the image is drawn at.
    """

    page_width: float
    page_height: float
    image_width: float
    image_height: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Returns the layout in the order expected by img2pdf layout functions.

        Returns:
            Page width, page height, image width, image height.
        """
        return self.page_width, self.page_height, self.image_width, self.image_height


def read_geometry(path: Path) -> ImageGeometry:
    """Reads the natural size of an image from its pixels and embedded DPI (300 DPI if there is none).

    Args:
        path: Image file.

    Returns:
        The natural size in points.
    """
    with Image.open(path) as image:
        width_px, height_px = image.size
        dpi = image.info.get("dpi")
    dpi_x, dpi_y = (float(dpi[0]), float(dpi[1])) if dpi and min(dpi) > 0 else (DEFAULT_DPI, DEFAULT_DPI)
    return ImageGeometry(width_px / dpi_x * 72, height_px / dpi_y * 72)


def compute_layout(
    image: ImageGeometry,
    width_mm: float | None,
    height_mm: float | None,
    allow_cropping: bool = False,
    allow_stretching: bool = False,
) -> PageLayout:
    """Computes the page layout of one image.

    With neither dimension the page matches the image. With one dimension the image is scaled to it and the other
    follows the aspect ratio. With both, the page has exactly that size: an image fitting inside is centred (or
    stretched to the page if allowed), a larger one is scaled to fit inside (or to cover the page and be cropped
    if allowed).

    Args:
        image: Natural size of the image.
        width_mm: Requested page width in mm.
        height_mm: Requested page height in mm.
        allow_cropping: Crop larger images instead of fitting them inside.
        allow_stretching: Stretch smaller images to fill the page.

    Returns:
        The layout.
    """
    if width_mm is None and height_mm is None:
        return PageLayout(image.width, image.height, image.width, image.height)
    if height_mm is None:
        scale = width_mm * POINTS_PER_MM / image.width
        return PageLayout(*[value * scale for value in (image.width, image.height)] * 2)
    if width_mm is None:
        scale = height_mm * POINTS_PER_MM / image.height
        return PageLayout(*[value * scale for value in (image.width, image.height)] * 2)

    page_width, page_height = width_mm * POINTS_PER_MM, height_mm * POINTS_PER_MM
    if image.width <= page_width and image.height <= page_height:
        if allow_stretching:
            return PageLayout(page_width, page_height, page_width, page_height)
        return PageLayout(page_width, page_height, image.width, image.height)
    pick = max if allow_cropping else min
    scale = pick(page_width / image.width, page_height / image.height)
    return PageLayout(page_width, page_height, image.width * scale, image.height * scale)
