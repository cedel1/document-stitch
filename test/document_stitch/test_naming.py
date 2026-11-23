"""Tests for document_stitch.naming."""

from pathlib import Path

import pytest

from document_stitch.errors import PropertiesError
from document_stitch.naming import numbered_name, resolve_base_name, resolve_output_dir, sanitize_filename
from document_stitch.properties import Properties


@pytest.mark.parametrize(
    ("name", "expected"),
    [("a/b", "a_b"), ('a:b*c?"d<e>f|g', "a_b_c__d_e_f_g"), ("ok name", "ok name"), ("...", "_"), ("", "_")],
)
def test_sanitize_filename_should_replace_illegal_characters(name: str, expected: str) -> None:
    """Illegal characters become underscores and the result is never empty."""
    assert sanitize_filename(name) == expected


def test_resolve_base_name_should_prefer_document_name() -> None:
    """An explicit name wins."""
    props = Properties({"title": "T"})
    assert resolve_base_name(Path("f"), "given", True, props) == "given"


def test_resolve_base_name_should_use_properties_title_when_requested() -> None:
    """The properties title is used with the option."""
    assert resolve_base_name(Path("f"), None, True, Properties({"title": "T", "part title": "P"})) == "T_P"


@pytest.mark.parametrize(("use", "props"), [(False, Properties({"title": "T"})), (True, None)])
def test_resolve_base_name_should_use_folder_name_otherwise(use: bool, props: Properties | None) -> None:
    """Without a name source the folder name is used."""
    assert resolve_base_name(Path("some/folder"), None, use, props) == "folder"


def test_resolve_base_name_should_raise_when_properties_have_no_title() -> None:
    """Properties without any title cannot name the document."""
    with pytest.raises(PropertiesError):
        resolve_base_name(Path("f"), None, True, Properties({}))


def test_numbered_name_should_append_number_after_underscore() -> None:
    """The number is appended with an underscore."""
    assert numbered_name("doc", 3) == "doc_3"


def test_resolve_output_dir_should_default_to_document_folder() -> None:
    """Without an output folder files go next to the images."""
    assert resolve_output_dir(Path("/d/f"), None) == Path("/d/f")


def test_resolve_output_dir_should_resolve_relative_folder_against_document_folder() -> None:
    """A relative output folder is relative to the document folder."""
    assert resolve_output_dir(Path("/d/f"), Path("out")) == Path("/d/f/out")


def test_resolve_output_dir_should_use_absolute_folder_as_is() -> None:
    """An absolute output folder is used unchanged."""
    assert resolve_output_dir(Path("/d/f"), Path("/x/out")) == Path("/x/out")
