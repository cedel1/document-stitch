"""Tests for document_stitch.config."""

# pylint: disable=redefined-outer-name,unused-import
from pathlib import Path

import pytest

from document_stitch.config import (
    CONFIG_FILENAME,
    find_global_config,
    load_config_file,
    resolve_folder_options,
    resolve_global_options,
)
from document_stitch.errors import ConfigError, OptionsError
from document_stitch.options import Options
from test.document_stitch.fixtures import configured_folder, natural_folder


def write_config(directory: Path, content: str) -> Path:
    """Writes a configuration file into a directory."""
    path = directory / CONFIG_FILENAME
    path.write_text(content)
    return path


def test_load_config_file_should_read_options(tmp_path: Path) -> None:
    """Options in the file are returned."""
    assert load_config_file(write_config(tmp_path, "overwrite = true")).overwrite is True


@pytest.mark.parametrize("content", ["not = [valid", "bogus = 1"])
def test_load_config_file_should_raise_for_invalid_content(tmp_path: Path, content: str) -> None:
    """Syntax errors and invalid options raise ConfigError."""
    config_file = write_config(tmp_path, content)
    with pytest.raises(ConfigError):
        load_config_file(config_file)


def test_load_config_file_should_raise_for_missing_file(tmp_path: Path) -> None:
    """A file that cannot be read raises ConfigError."""
    with pytest.raises(ConfigError):
        load_config_file(tmp_path / "missing.toml")


def test_load_config_file_should_raise_for_non_toml_file(tmp_path: Path) -> None:
    """A file without the .toml suffix is rejected."""
    path = tmp_path / "config.txt"
    path.write_text("overwrite = true")
    with pytest.raises(ConfigError, match="not an existing .toml file"):
        load_config_file(path)


def test_load_config_file_should_raise_for_directory(tmp_path: Path) -> None:
    """A directory named like a TOML file is rejected."""
    directory = tmp_path / "dir.toml"
    directory.mkdir()
    with pytest.raises(ConfigError):
        load_config_file(directory)


def test_find_global_config_should_prefer_explicit_file(tmp_path: Path) -> None:
    """--config replaces the file next to the script."""
    (tmp_path / "script").mkdir()
    write_config(tmp_path / "script", "")
    explicit = tmp_path / "explicit.toml"
    explicit.write_text("")
    assert find_global_config(tmp_path / "script", explicit) == explicit


def test_find_global_config_should_find_file_next_to_script(tmp_path: Path) -> None:
    """Without --config the file next to the script is used."""
    path = write_config(tmp_path, "")
    assert find_global_config(tmp_path, None) == path


def test_find_global_config_should_return_none_when_absent(tmp_path: Path) -> None:
    """No configuration file is fine."""
    assert find_global_config(tmp_path, None) is None


def test_find_global_config_should_raise_for_missing_explicit_file(tmp_path: Path) -> None:
    """An explicitly requested file must exist."""
    with pytest.raises(ConfigError):
        find_global_config(tmp_path, tmp_path / "nope.toml")


def test_resolve_global_options_should_prefer_cli_over_config(tmp_path: Path) -> None:
    """CLI values override the global configuration file."""
    write_config(tmp_path, 'document-name = "from-config"')
    result = resolve_global_options(Options(document_folder=Path("d"), document_name="cli"), tmp_path)
    assert result.document_name == "cli"


def test_resolve_global_options_should_add_options_missing_on_cli(tmp_path: Path) -> None:
    """Options not given on the CLI come from the global file."""
    write_config(tmp_path, "overwrite = true")
    assert resolve_global_options(Options(document_folder=Path("d")), tmp_path).overwrite is True


def test_resolve_global_options_should_accept_folder_selection_from_config(tmp_path: Path) -> None:
    """The global file may select the folder to process."""
    write_config(tmp_path, 'document-folder = "docs"')
    assert resolve_global_options(Options(), tmp_path).document_folder == tmp_path / "docs"


def test_resolve_global_options_should_read_explicit_config_path(tmp_path: Path) -> None:
    """The --config path is loaded."""
    path = write_config(tmp_path, "overwrite = true")
    assert resolve_global_options(Options(document_folder=Path("d")), Path("/nonexistent"), path).overwrite is True


def test_resolve_global_options_should_raise_when_no_folder_selected(tmp_path: Path) -> None:
    """The merged options are validated."""
    with pytest.raises(OptionsError):
        resolve_global_options(Options(), tmp_path)


def test_resolve_folder_options_should_return_global_options_without_folder_config(natural_folder: Path) -> None:
    """A folder without a config file uses the global options unchanged."""
    options = Options(document_name="x")
    assert resolve_folder_options(options, natural_folder) is options


def test_resolve_folder_options_should_add_folder_options(configured_folder: Path) -> None:
    """Options absent from the global layer come from the folder config."""
    assert resolve_folder_options(Options(), configured_folder).output_width == 50.0


def test_resolve_folder_options_should_prefer_global_options(configured_folder: Path) -> None:
    """Global options win over the per-folder config."""
    assert resolve_folder_options(Options(document_name="global"), configured_folder).document_name == "global"


def test_resolve_folder_options_should_reject_folder_selection_in_folder_config(tmp_path: Path) -> None:
    """A folder config may not select folders."""
    write_config(tmp_path, 'document-folder = "x"')
    with pytest.raises(ConfigError):
        resolve_folder_options(Options(), tmp_path)


def test_resolve_folder_options_should_validate_merged_settings(tmp_path: Path) -> None:
    """Merged per-folder settings must be consistent."""
    write_config(tmp_path, "allow-cropping = true")
    with pytest.raises(OptionsError):
        resolve_folder_options(Options(), tmp_path)
