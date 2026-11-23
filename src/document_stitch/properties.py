"""Parsing of the ``properties.txt`` file that accompanies downloaded documents."""

from dataclasses import dataclass, field
from pathlib import Path

from document_stitch.errors import PropertiesError

PROPERTIES_FILENAME = "properties.txt"
UUID_PREFIX = "uuid:"


@dataclass(frozen=True)
class Properties:
    """Content of a properties file.

    Attributes:
        values: Simple ``key: value`` entries with lower-cased keys.
        pages: Page uuids in document order, without the ``uuid:`` prefix.
    """

    values: dict[str, str] = field(default_factory=dict)
    pages: tuple[str, ...] = ()


def parse_properties(text: str) -> Properties:
    """Parses the text of a properties file.

    Args:
        text: Content of the file.

    Returns:
        The parsed properties.
    """
    values: dict[str, str] = {}
    pages: list[str] = []
    in_pages = False
    for line in text.splitlines():
        if not line.strip():
            continue
        if in_pages and line[0].isspace():
            pages.append(line.strip().removeprefix(UUID_PREFIX))
            continue
        in_pages = False
        key, separator, value = line.partition(":")
        if not separator:
            continue
        key = key.strip().lower()
        if key == "pages":
            in_pages = True
        else:
            values[key] = value.strip()
    return Properties(values, tuple(pages))


def load_properties(folder: Path) -> Properties | None:
    """Loads the properties file of a document folder.

    Args:
        folder: Folder containing the images.

    Returns:
        The properties, or ``None`` if the folder has no properties file.

    Raises:
        PropertiesError: If the file exists but cannot be read.
    """
    path = folder / PROPERTIES_FILENAME
    if not path.is_file():
        return None
    try:
        return parse_properties(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise PropertiesError(f"cannot read {path}: {error}") from error


def document_title(properties: Properties) -> str:
    """Builds the document title from the title and the part title.

    Args:
        properties: Parsed properties.

    Returns:
        ``Title_Part title``, or whichever of the two is present.

    Raises:
        PropertiesError: If neither a title nor a part title is present.
    """
    parts = [properties.values.get(key, "") for key in ("title", "part title")]
    parts = [part for part in parts if part]
    if not parts:
        raise PropertiesError("properties file has neither a 'Title' nor a 'Part title'")
    return "_".join(parts)
