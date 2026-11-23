"""Loading and layering of ``document-stitch.toml`` configuration files."""

import tomllib
from pathlib import Path

from document_stitch.errors import ConfigError, OptionsError
from document_stitch.options import Options, merge_options, options_from_mapping, validate_options, validate_settings

CONFIG_FILENAME = "document-stitch.toml"


def load_config_file(path: Path, allow_folder_selection: bool = True) -> Options:
    """Reads a configuration file.

    Args:
        path: Path of the TOML file.
        allow_folder_selection: Whether ``documents-folders`` and ``document-folder`` may be used in the file.

    Returns:
        The options in the file.

    Raises:
        ConfigError: If the file cannot be read, parsed or contains invalid options.
    """
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError as error:
        raise ConfigError(f"cannot read configuration file {path}: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid configuration file {path}: {error}") from error
    try:
        return options_from_mapping(data, path.parent, allow_folder_selection)
    except OptionsError as error:
        raise ConfigError(f"invalid configuration file {path}: {error}") from error


def find_global_config(script_dir: Path, explicit: Path | None) -> Path | None:
    """Finds the global configuration file.

    Args:
        script_dir: Directory of the main script.
        explicit: File given on the command line, which replaces the one next to the script.

    Returns:
        The configuration file, or ``None`` if there is none.

    Raises:
        ConfigError: If an explicitly given file does not exist.
    """
    if explicit is not None:
        if not explicit.is_file():
            raise ConfigError(f"configuration file {explicit} does not exist")
        return explicit
    candidate = script_dir / CONFIG_FILENAME
    return candidate if candidate.is_file() else None


def resolve_global_options(cli: Options, script_dir: Path, config_path: Path | None = None) -> Options:
    """Layers the command line over the global configuration file and validates the result.

    Args:
        cli: Options given on the command line.
        script_dir: Directory of the main script.
        config_path: Value of ``--config``, if any.

    Returns:
        The merged and validated global options.

    Raises:
        ConfigError: If the configuration file is unusable.
        OptionsError: If the merged options are invalid.
    """
    found = find_global_config(script_dir, config_path)
    merged = merge_options(cli, load_config_file(found)) if found else cli
    validate_options(merged)
    return merged


def resolve_folder_options(global_options: Options, folder: Path) -> Options:
    """Layers the global options over the configuration file inside a document folder.

    Args:
        global_options: Merged global options.
        folder: Folder containing the images of one document.

    Returns:
        The options effective for the folder.

    Raises:
        ConfigError: If the folder configuration file is unusable.
        OptionsError: If the merged options are invalid.
    """
    path = folder / CONFIG_FILENAME
    if not path.is_file():
        return global_options
    merged = merge_options(global_options, load_config_file(path, allow_folder_selection=False))
    validate_settings(merged)
    return merged
