"""Option model shared by the command line, the configuration files and the stitching library."""

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from document_stitch.errors import OptionsError

PATH_FIELDS = frozenset({"documents_folders", "document_folder", "output_folder"})
FOLDER_SELECTION_FIELDS = frozenset({"documents_folders", "document_folder"})
BOOL_FIELDS = frozenset(
    {"overwrite", "use_properties_file", "allow_natural_sorting_fallback", "allow_cropping", "allow_stretching"}
)
NUMBER_FIELDS = frozenset({"output_width", "output_height"})


@dataclass(frozen=True)
class Options:
    """Settings of the program. ``None`` means "not specified" so that settings can be layered.

    Attributes:
        documents_folders: Directory containing one sub-folder of images per document.
        document_folder: Directory containing the images of a single document.
        output_folder: Where to save the documents. Relative paths are relative to the document folder.
        overwrite: Allow overwriting existing documents.
        document_name: Name of the output document (without extension).
        use_properties_file: Use ``properties.txt`` for the name and the page order.
        allow_natural_sorting_fallback: Fall back to natural order when the properties file cannot order the pages.
        output_width: Page width in mm, ``None`` to keep the original size.
        output_height: Page height in mm, ``None`` to keep the original size.
        allow_cropping: Crop images that are larger than the page instead of fitting them inside.
        allow_stretching: Stretch images that are smaller than the page to fill it.
        order: Explicit order of the image file names.
    """

    documents_folders: Path | None = None
    document_folder: Path | None = None
    output_folder: Path | None = None
    overwrite: bool | None = None
    document_name: str | None = None
    use_properties_file: bool | None = None
    allow_natural_sorting_fallback: bool | None = None
    output_width: float | None = None
    output_height: float | None = None
    allow_cropping: bool | None = None
    allow_stretching: bool | None = None
    order: tuple[str, ...] | None = None


FIELD_NAMES = tuple(field.name for field in dataclasses.fields(Options))


def option_key(field_name: str) -> str:
    """Converts a field name to the hyphenated key used in configuration files.

    Args:
        field_name: Name of an ``Options`` field.

    Returns:
        The hyphenated key, e.g. ``output-width``.
    """
    return field_name.replace("_", "-")


def merge_options(higher: Options, lower: Options) -> Options:
    """Merges two layers of options; values of the higher layer win, gaps are filled from the lower one.

    Args:
        higher: Options with the higher precedence.
        lower: Options with the lower precedence.

    Returns:
        The merged options.
    """
    values = {}
    for name in FIELD_NAMES:
        value = getattr(higher, name)
        values[name] = value if value is not None else getattr(lower, name)
    return Options(**values)


def _convert_value(name: str, value: Any, base_dir: Path | None) -> Any:
    """Validates and converts a raw value read from a configuration file.

    Args:
        name: Field name of the option.
        value: Raw value.
        base_dir: Directory used to resolve relative folder selections, ``None`` to keep them as they are.

    Returns:
        The converted value.

    Raises:
        OptionsError: If the value has the wrong type.
    """
    key = option_key(name)
    if name in BOOL_FIELDS:
        if not isinstance(value, bool):
            raise OptionsError(f"'{key}' must be true or false")
        return value
    if name in NUMBER_FIELDS:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise OptionsError(f"'{key}' must be a number")
        return float(value)
    if name == "order":
        return _convert_order(key, value)
    if not isinstance(value, str) or not value:
        raise OptionsError(f"'{key}' must be a non-empty string")
    if name in PATH_FIELDS:
        return _convert_path(name, value, base_dir)
    return value


def _convert_order(key: str, value: Any) -> tuple[str, ...]:
    """Validates the explicit page order.

    Args:
        key: Configuration key, used in error messages.
        value: Raw value.

    Returns:
        The file names as a tuple.

    Raises:
        OptionsError: If the value is not a list of strings.
    """
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise OptionsError(f"'{key}' must be a list of file names")
    return tuple(value)


def _convert_path(name: str, value: str, base_dir: Path | None) -> Path:
    """Converts a path option, resolving folder selections against a base directory.

    Args:
        name: Field name of the option.
        value: Raw path string.
        base_dir: Directory used to resolve relative folder selections, ``None`` to keep them as they are.

    Returns:
        The path.
    """
    path = Path(value).expanduser()
    if name in FOLDER_SELECTION_FIELDS and base_dir is not None and not path.is_absolute():
        path = base_dir / path
    return path


def options_from_mapping(
    mapping: Mapping[str, Any], base_dir: Path | None = None, allow_folder_selection: bool = True
) -> Options:
    """Builds options from a parsed configuration file.

    Args:
        mapping: Parsed TOML content.
        base_dir: Directory used to resolve relative ``documents-folders`` and ``document-folder`` values.
        allow_folder_selection: Whether ``documents-folders`` and ``document-folder`` may be present.

    Returns:
        The options found in the mapping.

    Raises:
        OptionsError: If a key is unknown, not allowed or has an invalid value.
    """
    keys = {option_key(name): name for name in FIELD_NAMES}
    values = {}
    for key, raw in mapping.items():
        if key not in keys:
            raise OptionsError(f"unknown option '{key}'")
        name = keys[key]
        if not allow_folder_selection and name in FOLDER_SELECTION_FIELDS:
            raise OptionsError(f"option '{key}' is not allowed here")
        values[name] = _convert_value(name, raw, base_dir)
    return Options(**values)


def validate_options(options: Options) -> None:
    """Checks that the options are consistent.

    Args:
        options: The fully merged global options.

    Raises:
        OptionsError: If the options are inconsistent.
    """
    if options.documents_folders is not None and options.document_folder is not None:
        raise OptionsError("'documents-folders' and 'document-folder' are mutually exclusive")
    if options.documents_folders is None and options.document_folder is None:
        raise OptionsError("one of 'documents-folders' or 'document-folder' is required")
    validate_settings(options)


def validate_settings(options: Options) -> None:
    """Checks the output settings, ignoring which folders are selected.

    Args:
        options: Options of a single document or the merged global options.

    Raises:
        OptionsError: If the settings are invalid.
    """
    for name in NUMBER_FIELDS:
        value = getattr(options, name)
        if value is not None and value <= 0:
            raise OptionsError(f"'{option_key(name)}' must be greater than zero")
    if (options.allow_cropping or options.allow_stretching) and (
        options.output_width is None or options.output_height is None
    ):
        raise OptionsError("'allow-cropping' and 'allow-stretching' require both 'output-width' and 'output-height'")
