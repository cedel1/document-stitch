"""Naming of output documents and resolution of output locations."""

import re
from pathlib import Path

from document_stitch.properties import Properties, document_title

OUTPUT_EXTENSION = ".pdf"
_ILLEGAL_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(name: str) -> str:
    """Replaces characters that are illegal in file names with underscores.

    Args:
        name: Proposed file name without extension.

    Returns:
        A safe file name; never empty.
    """
    cleaned = _ILLEGAL_CHARACTERS.sub("_", name).strip().rstrip(".")
    return cleaned or "_"


def resolve_base_name(
    folder: Path, document_name: str | None, use_properties: bool, properties: Properties | None
) -> str:
    """Chooses the name of a document, without numbering or extension.

    Args:
        folder: Folder containing the images.
        document_name: Name given explicitly, if any.
        use_properties: Whether to name the document from the properties file.
        properties: Properties of the folder, if present.

    Returns:
        The sanitized name: the explicit name, else the properties title, else the folder name.

    Raises:
        PropertiesError: If the properties file is used but has no title.
    """
    if document_name:
        return sanitize_filename(document_name)
    if use_properties and properties is not None:
        return sanitize_filename(document_title(properties))
    return sanitize_filename(folder.name)


def numbered_name(name: str, number: int) -> str:
    """Appends a number to a name, separated by an underscore.

    Args:
        name: Base name.
        number: Sequence number.

    Returns:
        The numbered name.
    """
    return f"{name}_{number}"


def resolve_output_dir(folder: Path, output_folder: Path | None) -> Path:
    """Determines where the document of a folder is saved.

    Args:
        folder: Folder containing the images.
        output_folder: Configured output folder, if any.

    Returns:
        The folder itself if no output folder is set, the output folder if absolute, otherwise the output
        folder relative to the document folder.
    """
    if output_folder is None:
        return folder
    return output_folder if output_folder.is_absolute() else folder / output_folder
