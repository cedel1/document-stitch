"""Discovery and ordering of the page images of a document."""

import logging
import re
from pathlib import Path

from document_stitch.errors import OrderingError
from document_stitch.properties import Properties

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff"})


def natural_key(name: str) -> list[tuple[int, int, str]]:
    """Builds a sort key that orders embedded numbers by value (``page2`` before ``page10``).

    Args:
        name: A file name.

    Returns:
        The sort key.
    """
    return [
        (0, int(chunk), "") if chunk.isdigit() else (1, 0, chunk.lower()) for chunk in re.split(r"(\d+)", name) if chunk
    ]


def list_images(folder: Path) -> list[Path]:
    """Lists the images of a folder in natural order.

    Args:
        folder: Folder to scan (not recursively).

    Returns:
        Image paths sorted naturally by file name.
    """
    images = [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS]
    return sorted(images, key=lambda path: natural_key(path.name))


def order_by_explicit_list(images: list[Path], order: tuple[str, ...]) -> list[Path]:
    """Puts the listed files first, in the listed order; remaining files follow in their current order.

    Args:
        images: Images in their default order.
        order: Explicit file names.

    Returns:
        The reordered images.

    Raises:
        OrderingError: If a listed name is not an image of the folder or is listed twice.
    """
    by_name = {path.name: path for path in images}
    if len(set(order)) != len(order):
        raise OrderingError("the explicit order lists a file more than once")
    missing = [name for name in order if name not in by_name]
    if missing:
        raise OrderingError(f"files in the explicit order were not found: {', '.join(missing)}")
    listed = [by_name[name] for name in order]
    return listed + [path for path in images if path.name not in order]


def _page_index(name: str, pages: tuple[str, ...]) -> int | None:
    """Finds the page whose uuid (or first uuid segment) appears in a file name.

    Args:
        name: File name.
        pages: Page uuids in document order.

    Returns:
        Index of the page, or ``None`` if nothing matches.
    """
    lowered = name.lower()
    for index, page in enumerate(pages):
        if page.lower() in lowered:
            return index
    for index, page in enumerate(pages):
        if page.split("-")[0].lower() in lowered:
            return index
    return None


def order_by_properties(images: list[Path], properties: Properties) -> list[Path]:
    """Orders images by the page list of the properties file.

    Args:
        images: Images in their default order.
        properties: Properties with the page list.

    Returns:
        The images in page order.

    Raises:
        OrderingError: If some file name cannot be matched to a page.
    """
    indexed = [(_page_index(path.name, properties.pages), path) for path in images]
    unmatched = [path.name for index, path in indexed if index is None]
    if unmatched:
        raise OrderingError(f"files cannot be matched to pages of the properties file: {', '.join(unmatched)}")
    return [path for _, path in sorted(indexed, key=lambda item: item[0])]


def order_images(
    images: list[Path],
    explicit_order: tuple[str, ...] | None,
    properties: Properties | None,
    use_properties: bool,
    allow_fallback: bool,
) -> tuple[list[Path], list[str]]:
    """Determines the page order of a document.

    An explicit order wins; otherwise the properties file is used if requested and it lists pages;
    otherwise natural order is used.

    Args:
        images: Images in natural order.
        explicit_order: File names from the configuration, if any.
        properties: Properties of the folder, if present.
        use_properties: Whether the properties file should be used to order the pages.
        allow_fallback: Whether natural order may replace an order that the properties file cannot provide.

    Returns:
        The ordered images and a list of warnings.

    Raises:
        OrderingError: If the order cannot be determined and falling back is not allowed.
    """
    if explicit_order:
        return order_by_explicit_list(images, explicit_order), []
    if not (use_properties and properties and properties.pages):
        return images, []
    try:
        return order_by_properties(images, properties), []
    except OrderingError as error:
        if not allow_fallback:
            raise
        message = f"{error}; using natural order"
        logger.warning(message)
        return images, [message]
