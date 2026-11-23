"""Tests for the document_stitch.py controller script."""

# pylint: disable=redefined-outer-name,unused-import
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

from document_stitch.options import Options
from document_stitch.stitcher import RunSummary
from test.document_stitch.fixtures import documents_root, natural_folder
from test.fixtures import cli_module


def test_build_parser_should_reject_both_folder_options(cli_module: ModuleType) -> None:
    """The folder options are mutually exclusive."""
    parser = cli_module.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--document-folder", "a", "--documents-folders", "b"])


def test_options_from_args_should_convert_arguments(cli_module: ModuleType) -> None:
    """Parsed arguments map to options."""
    args = cli_module.build_parser().parse_args(["--document-folder", "a", "--output-width", "10", "--overwrite"])
    options = cli_module.options_from_args(args)
    assert (options.document_folder, options.output_width, options.overwrite) == (Path("a"), 10.0, True)


def test_options_from_args_should_leave_unset_flags_as_none(cli_module: ModuleType) -> None:
    """Flags not given do not override lower config layers."""
    args = cli_module.build_parser().parse_args(["--document-folder", "a"])
    assert cli_module.options_from_args(args).overwrite is None


def test_format_summary_should_list_outcomes(cli_module: ModuleType) -> None:
    """The summary names successes, warnings and failures."""
    summary = RunSummary([Path("ok.pdf")], {"w.pdf": ["careful"]}, {"f.pdf": "boom"})
    assert cli_module.format_summary(summary) == [
        "Summary: 1 succeeded, 1 with warnings, 1 failed",
        "  succeeded: ok.pdf",
        "  warning: w.pdf: careful",
        "  failed: f.pdf: boom",
    ]


def test_main_should_return_zero_and_create_pdf(cli_module: ModuleType, natural_folder: Path, tmp_path: Path) -> None:
    """A successful run exits with 0 and writes the file."""
    argv = ["--document-folder", str(natural_folder), "--output-folder", str(tmp_path)]
    assert (cli_module.main(argv, tmp_path), (tmp_path / "natural-doc.pdf").exists()) == (0, True)


def test_main_should_return_one_when_output_exists(
    cli_module: ModuleType, natural_folder: Path, tmp_path: Path
) -> None:
    """Existing output without --overwrite is a pre-flight failure."""
    (tmp_path / "natural-doc.pdf").write_bytes(b"")
    argv = ["--document-folder", str(natural_folder), "--output-folder", str(tmp_path)]
    assert cli_module.main(argv, tmp_path) == 1


def test_main_should_return_one_when_a_document_fails(cli_module: ModuleType, tmp_path: Path) -> None:
    """A failed document gives a non-zero exit code."""
    summary = RunSummary(failed={"a.pdf": "boom"})
    with patch.object(cli_module, "run", return_value=summary):
        assert cli_module.main(["--document-folder", str(tmp_path)], tmp_path) == 1


def test_main_should_return_two_for_invalid_configuration(cli_module: ModuleType, tmp_path: Path) -> None:
    """Library errors other than pre-flight ones give exit code 2."""
    assert cli_module.main(["--document-folder", str(tmp_path / "missing")], tmp_path) == 2


def test_main_should_return_two_for_missing_explicit_config(cli_module: ModuleType, tmp_path: Path) -> None:
    """A --config file that does not exist is an error."""
    argv = ["--document-folder", str(tmp_path), "--config", str(tmp_path / "none.toml")]
    assert cli_module.main(argv, tmp_path) == 2


def test_main_should_pass_resolved_options_to_run(cli_module: ModuleType, tmp_path: Path) -> None:
    """Options reach the library."""
    with patch.object(cli_module, "run", return_value=RunSummary()) as mocked:
        cli_module.main(["--document-folder", str(tmp_path), "--document-name", "n"], tmp_path)
    assert mocked.call_args.args[0] == Options(document_folder=tmp_path, document_name="n")
