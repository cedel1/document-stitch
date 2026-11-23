"""Tests for document_stitch.ordering."""

# pylint: disable=redefined-outer-name,unused-import
from pathlib import Path

import pytest

from document_stitch.errors import OrderingError
from document_stitch.ordering import list_images, natural_key, order_by_explicit_list, order_by_properties, order_images
from document_stitch.properties import Properties, load_properties
from test.document_stitch.fixtures import natural_folder, properties_folder, unmatched_properties_folder


def names(paths: list[Path]) -> list[str]:
    """Returns the file names of paths."""
    return [path.name for path in paths]


def test_natural_key_should_sort_numbers_by_value() -> None:
    """page2 sorts before page10."""
    assert sorted(["page10", "page2", "page1"], key=natural_key) == ["page1", "page2", "page10"]


def test_natural_key_should_ignore_case() -> None:
    """Letters compare case-insensitively."""
    assert sorted(["b", "A"], key=natural_key) == ["A", "b"]


def test_list_images_should_return_images_in_natural_order(natural_folder: Path) -> None:
    """Images are listed naturally."""
    assert names(list_images(natural_folder)) == ["page1.png", "page2.png", "page10.png"]


def test_list_images_should_not_return_other_files(natural_folder: Path) -> None:
    """Non-image files are skipped."""
    assert "readme.txt" not in names(list_images(natural_folder))


def test_order_by_explicit_list_should_put_listed_files_first_then_rest_naturally(natural_folder: Path) -> None:
    """Listed files come first, the rest follows in natural order."""
    result = order_by_explicit_list(list_images(natural_folder), ("page10.png",))
    assert names(result) == ["page10.png", "page1.png", "page2.png"]


@pytest.mark.parametrize("order", [("missing.png",), ("page1.png", "page1.png")])
def test_order_by_explicit_list_should_raise_for_missing_or_duplicated_names(
    natural_folder: Path, order: tuple
) -> None:
    """Unknown and repeated names are errors."""
    with pytest.raises(OrderingError):
        order_by_explicit_list(list_images(natural_folder), order)


def test_order_by_properties_should_follow_page_order(properties_folder: Path) -> None:
    """Pages follow the properties file, not the alphabet."""
    result = order_by_properties(list_images(properties_folder), load_properties(properties_folder))
    assert names(result) == ["3849013e.jpg", "3848b31c.jpg", "3848da2d.jpg"]


def test_order_by_properties_should_match_full_uuid_in_file_name(tmp_path: Path) -> None:
    """A file name containing the whole uuid matches its page."""
    first, second = tmp_path / "x_bbb-1.png", tmp_path / "x_aaa-2.png"
    for path in (first, second):
        path.write_bytes(b"")
    result = order_by_properties([second, first], Properties({}, ("bbb-1", "aaa-2")))
    assert result == [first, second]


def test_order_by_properties_should_raise_for_unmatched_files(unmatched_properties_folder: Path) -> None:
    """Files that match no page are an error."""
    with pytest.raises(OrderingError):
        order_by_properties(list_images(unmatched_properties_folder), load_properties(unmatched_properties_folder))


def test_order_images_should_prefer_explicit_order(properties_folder: Path) -> None:
    """The explicit list beats the properties file."""
    images = list_images(properties_folder)
    result, _ = order_images(images, ("3848da2d.jpg",), load_properties(properties_folder), True, False)
    assert result[0].name == "3848da2d.jpg"


def test_order_images_should_return_natural_order_without_properties_option(properties_folder: Path) -> None:
    """Without --use-properties-file the natural order is kept."""
    images = list_images(properties_folder)
    assert order_images(images, None, load_properties(properties_folder), False, False) == (images, [])


def test_order_images_should_return_natural_order_when_properties_missing(natural_folder: Path) -> None:
    """No properties file means natural order."""
    images = list_images(natural_folder)
    assert order_images(images, None, None, True, False) == (images, [])


def test_order_images_should_use_properties_order(properties_folder: Path) -> None:
    """With the option, the properties order is used."""
    result, warnings = order_images(
        list_images(properties_folder), None, load_properties(properties_folder), True, False
    )
    assert (names(result)[0], warnings) == ("3849013e.jpg", [])


def test_order_images_should_warn_and_fall_back_when_allowed(unmatched_properties_folder: Path) -> None:
    """With the fallback flag an unmatched order gives a warning and natural order."""
    images = list_images(unmatched_properties_folder)
    result, warnings = order_images(images, None, load_properties(unmatched_properties_folder), True, True)
    assert (result, len(warnings)) == (images, 1)


def test_order_images_should_not_fall_back_when_not_allowed(unmatched_properties_folder: Path) -> None:
    """Without the fallback flag an unmatched order is an error."""
    with pytest.raises(OrderingError):
        order_images(
            list_images(unmatched_properties_folder), None, load_properties(unmatched_properties_folder), True, False
        )
