"""Tests for document_stitch.options."""

# pylint: disable=redefined-outer-name
from pathlib import Path

import pytest

from document_stitch.errors import OptionsError
from document_stitch.options import (
    Options,
    merge_options,
    option_key,
    options_from_mapping,
    validate_options,
    validate_settings,
)


def test_option_key_should_replace_underscores_with_hyphens() -> None:
    """Field names become hyphenated config keys."""
    assert option_key("output_width") == "output-width"


def test_merge_options_should_prefer_higher_values() -> None:
    """A value set in the higher layer wins."""
    merged = merge_options(Options(document_name="high"), Options(document_name="low"))
    assert merged.document_name == "high"


def test_merge_options_should_fill_gaps_from_lower_layer() -> None:
    """Options missing in the higher layer are taken from the lower one."""
    merged = merge_options(Options(document_name="high"), Options(output_width=5.0))
    assert merged.output_width == 5.0


def test_merge_options_should_keep_false_of_higher_layer() -> None:
    """An explicit False is a value and must not be replaced by the lower layer."""
    merged = merge_options(Options(overwrite=False), Options(overwrite=True))
    assert merged.overwrite is False


@pytest.mark.parametrize(
    ("key", "raw", "field", "expected"),
    [
        ("overwrite", True, "overwrite", True),
        ("output-width", 210, "output_width", 210.0),
        ("document-name", "doc", "document_name", "doc"),
        ("order", ["a.png", "b.png"], "order", ("a.png", "b.png")),
        ("output-folder", "out", "output_folder", Path("out")),
    ],
)
def test_options_from_mapping_should_convert_values(key: str, raw: object, field: str, expected: object) -> None:
    """Raw TOML values are converted to the option types."""
    assert getattr(options_from_mapping({key: raw}), field) == expected


def test_options_from_mapping_should_resolve_relative_folder_selection_against_base_dir() -> None:
    """Relative document folders in a config file are relative to the file."""
    options = options_from_mapping({"document-folder": "docs"}, base_dir=Path("/base"))
    assert options.document_folder == Path("/base/docs")


def test_options_from_mapping_should_not_resolve_output_folder_against_base_dir() -> None:
    """A relative output folder stays relative to each document folder."""
    options = options_from_mapping({"output-folder": "out"}, base_dir=Path("/base"))
    assert options.output_folder == Path("out")


@pytest.mark.parametrize(
    "mapping",
    [
        {"unknown": 1},
        {"overwrite": "yes"},
        {"output-width": "wide"},
        {"output-width": True},
        {"order": "a.png"},
        {"order": [1, 2]},
        {"document-name": ""},
    ],
)
def test_options_from_mapping_should_reject_invalid_entries(mapping: dict) -> None:
    """Unknown keys and wrongly typed values are rejected."""
    with pytest.raises(OptionsError):
        options_from_mapping(mapping)


@pytest.mark.parametrize("key", ["documents-folders", "document-folder"])
def test_options_from_mapping_should_reject_folder_selection_when_not_allowed(key: str) -> None:
    """Per-folder configs cannot choose which folders are processed."""
    with pytest.raises(OptionsError):
        options_from_mapping({key: "x"}, allow_folder_selection=False)


def test_validate_options_should_accept_single_folder() -> None:
    """A single document folder is valid."""
    validate_options(Options(document_folder=Path("a")))


@pytest.mark.parametrize(
    "options",
    [
        Options(),
        Options(documents_folders=Path("a"), document_folder=Path("b")),
        Options(document_folder=Path("a"), output_width=0),
        Options(document_folder=Path("a"), output_height=-1.0),
    ],
)
def test_validate_options_should_reject_invalid_combinations(options: Options) -> None:
    """Missing or conflicting folders and non-positive sizes are rejected."""
    with pytest.raises(OptionsError):
        validate_options(options)


@pytest.mark.parametrize("flag", ["allow_cropping", "allow_stretching"])
@pytest.mark.parametrize("size", [{}, {"output_width": 10.0}, {"output_height": 10.0}])
def test_validate_settings_should_reject_cropping_and_stretching_without_both_dimensions(flag: str, size: dict) -> None:
    """Cropping and stretching need both page dimensions."""
    with pytest.raises(OptionsError):
        validate_settings(Options(**{flag: True}, **size))


def test_validate_settings_should_accept_cropping_and_stretching_together() -> None:
    """The two flags are independent and can be combined."""
    validate_settings(Options(allow_cropping=True, allow_stretching=True, output_width=1.0, output_height=1.0))
