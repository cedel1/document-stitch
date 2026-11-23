"""Tests for document_stitch.properties."""

# pylint: disable=redefined-outer-name,unused-import
from pathlib import Path
from unittest.mock import patch

import pytest

from document_stitch.errors import PropertiesError
from document_stitch.properties import Properties, document_title, load_properties, parse_properties
from test.document_stitch.fixtures import PAGE_UUIDS, PROPERTIES_TEXT, natural_folder, properties_folder


@pytest.fixture(scope="module")
def parsed() -> Properties:
    """The parsed sample properties."""
    return parse_properties(PROPERTIES_TEXT)


def test_parse_properties_should_read_values_with_lowercase_keys(parsed: Properties) -> None:
    """Keys are lower-cased and values stripped."""
    assert parsed.values["title"] == "Zahlenangaben für die 12 cm"


def test_parse_properties_should_keep_colons_in_values(parsed: Properties) -> None:
    """Only the first colon separates key and value."""
    assert parsed.values["source url"] == "https://example.org/view/uuid:bf33aac4"


def test_parse_properties_should_read_empty_values_as_empty_string(parsed: Properties) -> None:
    """Empty values are present but empty."""
    assert parsed.values["part title"] == ""


def test_parse_properties_should_read_pages_in_order_without_prefix(parsed: Properties) -> None:
    """Page uuids keep their line order and lose the uuid: prefix."""
    assert parsed.pages == PAGE_UUIDS


def test_parse_properties_should_not_treat_following_keys_as_pages(parsed: Properties) -> None:
    """The pages block ends at the first non-indented line."""
    assert parsed.values["page count"] == "3"


def test_parse_properties_should_ignore_lines_without_colon() -> None:
    """Garbage lines are skipped."""
    assert parse_properties("nonsense\nTitle: T").values == {"title": "T"}


def test_load_properties_should_return_none_without_file(natural_folder: Path) -> None:
    """A folder without properties.txt yields None."""
    assert load_properties(natural_folder) is None


def test_load_properties_should_parse_file(properties_folder: Path) -> None:
    """The properties file of a folder is parsed."""
    assert load_properties(properties_folder).pages == PAGE_UUIDS


def test_load_properties_should_raise_when_file_unreadable(properties_folder: Path) -> None:
    """Read errors are reported as PropertiesError."""
    with patch("pathlib.Path.read_text", side_effect=OSError("boom")):
        with pytest.raises(PropertiesError):
            load_properties(properties_folder)


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"title": "T", "part title": "P"}, "T_P"),
        ({"title": "T", "part title": ""}, "T"),
        ({"title": "", "part title": "P"}, "P"),
        ({"title": "T"}, "T"),
    ],
)
def test_document_title_should_join_available_parts(values: dict, expected: str) -> None:
    """Title and part title are joined by an underscore; a missing one is skipped."""
    assert document_title(Properties(values)) == expected


def test_document_title_should_raise_without_any_title() -> None:
    """Without title and part title there is no name."""
    with pytest.raises(PropertiesError):
        document_title(Properties({"title": "", "part title": ""}))
