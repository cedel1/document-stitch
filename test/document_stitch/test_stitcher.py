"""Tests for document_stitch.stitcher."""

# pylint: disable=redefined-outer-name,unused-import
from pathlib import Path
from unittest.mock import patch

import pikepdf
import pytest

from document_stitch.errors import OptionsError, PreflightError, StitchError
from document_stitch.layout import POINTS_PER_MM
from document_stitch.options import Options
from document_stitch.stitcher import RunSummary, discover_document_folders, plan_jobs, run, stitch_document
from test.document_stitch.fixtures import (
    documents_root,
    mixed_size_folder,
    natural_folder,
    properties_folder,
    unmatched_properties_folder,
)


def page_sizes(path: Path) -> list[tuple[float, float]]:
    """Returns the rounded mediabox sizes in mm of every page."""
    with pikepdf.open(path) as pdf:
        return [
            (round(float(page.mediabox[2]) / POINTS_PER_MM, 1), round(float(page.mediabox[3]) / POINTS_PER_MM, 1))
            for page in pdf.pages
        ]


def test_discover_document_folders_should_return_single_folder(natural_folder: Path) -> None:
    """A document folder is returned as is."""
    assert discover_document_folders(Options(document_folder=natural_folder)) == [natural_folder]


def test_discover_document_folders_should_return_sorted_subfolders(documents_root: Path) -> None:
    """Only sub-directories are returned, sorted."""
    result = discover_document_folders(Options(documents_folders=documents_root))
    assert [path.name for path in result] == ["alpha", "beta", "empty"]


@pytest.mark.parametrize("key", ["document_folder", "documents_folders"])
def test_discover_document_folders_should_raise_for_missing_directory(tmp_path: Path, key: str) -> None:
    """Missing directories are errors."""
    with pytest.raises(OptionsError):
        discover_document_folders(Options(**{key: tmp_path / "nope"}))


def test_plan_jobs_should_name_job_after_folder(natural_folder: Path, tmp_path: Path) -> None:
    """The default name is the folder name with .pdf."""
    jobs = plan_jobs(Options(document_folder=natural_folder, output_folder=tmp_path))
    assert jobs[0].output_path == tmp_path / "natural-doc.pdf"


def test_plan_jobs_should_order_images_naturally(natural_folder: Path, tmp_path: Path) -> None:
    """Images are ordered naturally."""
    jobs = plan_jobs(Options(document_folder=natural_folder, output_folder=tmp_path))
    assert [path.name for path in jobs[0].images] == ["page1.png", "page2.png", "page10.png"]


def test_plan_jobs_should_apply_folder_config(natural_folder: Path, tmp_path: Path) -> None:
    """Per-folder configuration contributes missing options."""
    folder = tmp_path / "doc"
    folder.mkdir()
    (folder / "p.png").write_bytes((natural_folder / "page1.png").read_bytes())
    (folder / "document-stitch.toml").write_text('document-name = "configured"')
    assert plan_jobs(Options(document_folder=folder))[0].output_path.name == "configured.pdf"


def test_plan_jobs_should_skip_subfolders_without_images(documents_root: Path, tmp_path: Path) -> None:
    """Sub-folders without images are skipped."""
    jobs = plan_jobs(Options(documents_folders=documents_root, output_folder=tmp_path))
    assert [job.folder.name for job in jobs] == ["alpha", "beta"]


def test_plan_jobs_should_save_relative_output_next_to_each_folder(documents_root: Path) -> None:
    """A relative output folder is relative to each document folder."""
    jobs = plan_jobs(Options(documents_folders=documents_root, output_folder=Path("out")))
    assert jobs[0].output_path == documents_root / "alpha" / "out" / "alpha.pdf"


def test_plan_jobs_should_number_names_in_shared_absolute_folder(documents_root: Path, tmp_path: Path) -> None:
    """Document name plus a shared absolute folder gives numbered names."""
    options = Options(documents_folders=documents_root, output_folder=tmp_path, document_name="doc")
    assert [job.output_path.name for job in plan_jobs(options)] == ["doc_1.pdf", "doc_2.pdf"]


def test_plan_jobs_should_not_number_names_for_relative_output(documents_root: Path) -> None:
    """Relative output folders keep the plain document name."""
    options = Options(documents_folders=documents_root, output_folder=Path("out"), document_name="doc")
    assert {job.output_path.name for job in plan_jobs(options)} == {"doc.pdf"}


def test_plan_jobs_should_raise_for_colliding_names(documents_root: Path, tmp_path: Path) -> None:
    """Two documents producing the same file abort, even with overwrite."""
    options = Options(documents_folders=documents_root, output_folder=tmp_path, document_name="x", overwrite=True)
    with patch("document_stitch.stitcher.numbered_name", side_effect=lambda name, _: name):
        with pytest.raises(PreflightError):
            plan_jobs(options)


def test_plan_jobs_should_raise_when_output_exists_without_overwrite(natural_folder: Path, tmp_path: Path) -> None:
    """Existing files are protected."""
    (tmp_path / "natural-doc.pdf").write_bytes(b"")
    with pytest.raises(PreflightError):
        plan_jobs(Options(document_folder=natural_folder, output_folder=tmp_path))


def test_plan_jobs_should_accept_existing_output_with_overwrite(natural_folder: Path, tmp_path: Path) -> None:
    """--overwrite allows existing files."""
    (tmp_path / "natural-doc.pdf").write_bytes(b"")
    assert plan_jobs(Options(document_folder=natural_folder, output_folder=tmp_path, overwrite=True))


def test_plan_jobs_should_raise_for_document_folder_without_images(tmp_path: Path) -> None:
    """A single folder without images is an error."""
    with pytest.raises(PreflightError):
        plan_jobs(Options(document_folder=tmp_path))


def test_plan_jobs_should_raise_for_unmatched_properties_without_fallback(
    unmatched_properties_folder: Path, tmp_path: Path
) -> None:
    """Unmatched ordering is a pre-flight error without the fallback flag."""
    options = Options(document_folder=unmatched_properties_folder, output_folder=tmp_path, use_properties_file=True)
    with pytest.raises(PreflightError):
        plan_jobs(options)


def test_plan_jobs_should_collect_warning_when_falling_back(unmatched_properties_folder: Path, tmp_path: Path) -> None:
    """With the fallback flag the job carries a warning."""
    options = Options(
        document_folder=unmatched_properties_folder,
        output_folder=tmp_path,
        use_properties_file=True,
        allow_natural_sorting_fallback=True,
    )
    assert len(plan_jobs(options)[0].warnings) == 1


def test_plan_jobs_should_name_from_properties(properties_folder: Path, tmp_path: Path) -> None:
    """The properties title names the document."""
    options = Options(document_folder=properties_folder, output_folder=tmp_path, use_properties_file=True)
    assert plan_jobs(options)[0].output_path.name == "Zahlenangaben für die 12 cm.pdf"


def test_stitch_document_should_create_pdf_with_one_page_per_image(natural_folder: Path, tmp_path: Path) -> None:
    """The PDF has all pages."""
    job = plan_jobs(Options(document_folder=natural_folder, output_folder=tmp_path))[0]
    assert len(page_sizes(stitch_document(job))) == 3


def test_stitch_document_should_size_pages_to_requested_dimensions(mixed_size_folder: Path, tmp_path: Path) -> None:
    """With both dimensions every page has that size."""
    options = Options(document_folder=mixed_size_folder, output_folder=tmp_path, output_width=50, output_height=60)
    job = plan_jobs(options)[0]
    assert page_sizes(stitch_document(job)) == [(50.0, 60.0), (50.0, 60.0)]


def test_stitch_document_should_keep_original_page_sizes_by_default(mixed_size_folder: Path, tmp_path: Path) -> None:
    """Without sizes the pages match their images."""
    job = plan_jobs(Options(document_folder=mixed_size_folder, output_folder=tmp_path))[0]
    assert page_sizes(stitch_document(job)) == [(40.0, 80.0), (100.0, 50.0)]


def test_stitch_document_should_raise_stitch_error_when_conversion_fails(natural_folder: Path, tmp_path: Path) -> None:
    """Conversion errors are wrapped."""
    job = plan_jobs(Options(document_folder=natural_folder, output_folder=tmp_path))[0]
    with patch("document_stitch.stitcher.img2pdf.convert", side_effect=ValueError("bad")):
        with pytest.raises(StitchError):
            stitch_document(job)


def test_run_should_report_successes(documents_root: Path, tmp_path: Path) -> None:
    """All documents are created."""
    summary = run(Options(documents_folders=documents_root, output_folder=tmp_path))
    assert sorted(path.name for path in summary.succeeded) == ["alpha.pdf", "beta.pdf"]


def test_run_should_continue_after_failed_document(documents_root: Path, tmp_path: Path) -> None:
    """One failure does not stop the others."""
    real = stitch_document
    calls = []

    def flaky(job):
        calls.append(job)
        if len(calls) == 1:
            raise StitchError("boom")
        return real(job)

    with patch("document_stitch.stitcher.stitch_document", side_effect=flaky):
        summary = run(Options(documents_folders=documents_root, output_folder=tmp_path))
    assert (list(summary.failed), len(summary.succeeded)) == (["alpha.pdf"], 1)


def test_run_should_record_warnings(unmatched_properties_folder: Path, tmp_path: Path) -> None:
    """Planning warnings appear in the summary."""
    options = Options(
        document_folder=unmatched_properties_folder,
        output_folder=tmp_path,
        use_properties_file=True,
        allow_natural_sorting_fallback=True,
    )
    assert len(run(options).warnings) == 1


def test_run_should_not_stitch_anything_when_preflight_fails(documents_root: Path, tmp_path: Path) -> None:
    """Nothing is created if any document fails the checks."""
    (tmp_path / "beta.pdf").write_bytes(b"")
    with pytest.raises(PreflightError):
        run(Options(documents_folders=documents_root, output_folder=tmp_path))
    assert not (tmp_path / "alpha.pdf").exists()


@pytest.mark.parametrize(("failed", "expected"), [({}, False), ({"a.pdf": "x"}, True)])
def test_run_summary_has_failures_should_reflect_failed_documents(failed: dict, expected: bool) -> None:
    """has_failures is true only with failures."""
    assert RunSummary(failed=failed).has_failures is expected
