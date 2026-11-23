"""Public API of the library: plans and performs the stitching of document folders into PDFs."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import img2pdf

from document_stitch.config import resolve_folder_options
from document_stitch.errors import DocumentStitchError, OptionsError, PreflightError, StitchError
from document_stitch.layout import PageLayout, compute_layout, read_geometry
from document_stitch.naming import OUTPUT_EXTENSION, numbered_name, resolve_base_name, resolve_output_dir
from document_stitch.options import Options
from document_stitch.ordering import list_images, order_images
from document_stitch.properties import load_properties

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentJob:
    """A planned document.

    Attributes:
        folder: Folder with the source images.
        images: Images in page order.
        output_path: File to create.
        options: Options effective for this document.
        warnings: Warnings produced while planning.
    """

    folder: Path
    images: list[Path]
    output_path: Path
    options: Options
    warnings: list[str] = field(default_factory=list)


@dataclass
class RunSummary:
    """Outcome of a run.

    Attributes:
        succeeded: Output files that were created.
        warnings: Warnings per document name.
        failed: Error message per document name.
    """

    succeeded: list[Path] = field(default_factory=list)
    warnings: dict[str, list[str]] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)

    @property
    def has_failures(self) -> bool:
        """Whether any document failed.

        Returns:
            ``True`` if at least one document failed.
        """
        return bool(self.failed)


def discover_document_folders(options: Options) -> list[Path]:
    """Finds the document folders selected by the options.

    Args:
        options: Global options.

    Returns:
        The single document folder, or the sorted sub-folders of ``documents-folders``.

    Raises:
        OptionsError: If the selected directory does not exist.
    """
    if options.document_folder is not None:
        if not options.document_folder.is_dir():
            raise OptionsError(f"document folder {options.document_folder} does not exist")
        return [options.document_folder]
    root = options.documents_folders
    if root is None or not root.is_dir():
        raise OptionsError(f"documents folder {root} does not exist")
    return sorted((path for path in root.iterdir() if path.is_dir()), key=lambda path: path.name.lower())


def _plan_job(folder: Path, index: int, global_options: Options) -> DocumentJob | None:
    """Plans one document.

    Args:
        folder: Document folder.
        index: One-based position of the folder among the selected folders.
        global_options: Global options.

    Returns:
        The job, or ``None`` if a sub-folder of ``documents-folders`` has no images.

    Raises:
        DocumentStitchError: If the document cannot be planned.
    """
    options = resolve_folder_options(global_options, folder)
    images = list_images(folder)
    if not images:
        if global_options.document_folder is None:
            logger.warning("skipping %s: no images found", folder)
            return None
        raise OptionsError(f"no images found in {folder}")
    properties = load_properties(folder) if options.use_properties_file else None
    ordered, warnings = order_images(
        images,
        options.order,
        properties,
        bool(options.use_properties_file),
        bool(options.allow_natural_sorting_fallback),
    )
    name = resolve_base_name(folder, options.document_name, bool(options.use_properties_file), properties)
    output_dir = resolve_output_dir(folder, options.output_folder)
    shared_directory = (
        global_options.documents_folders is not None
        and options.output_folder is not None
        and options.output_folder.is_absolute()
    )
    if shared_directory and options.document_name:
        name = numbered_name(name, index)
    return DocumentJob(folder, ordered, output_dir / f"{name}{OUTPUT_EXTENSION}", options, warnings)


def plan_jobs(global_options: Options) -> list[DocumentJob]:
    """Plans all documents and checks for problems before anything is stitched.

    Args:
        global_options: Validated global options.

    Returns:
        The planned jobs.

    Raises:
        OptionsError: If the selected folders do not exist.
        PreflightError: If any document cannot be planned, two documents would write the same file,
            or an output file exists and overwriting is not enabled.
    """
    problems: list[str] = []
    jobs: list[DocumentJob] = []
    for index, folder in enumerate(discover_document_folders(global_options), start=1):
        try:
            job = _plan_job(folder, index, global_options)
        except DocumentStitchError as error:
            problems.append(f"{folder}: {error}")
            continue
        if job is not None:
            jobs.append(job)
    seen: dict[Path, Path] = {}
    for job in jobs:
        key = job.output_path.resolve()
        if key in seen:
            problems.append(f"{job.folder} and {seen[key]} would both create {job.output_path}")
        seen[key] = job.folder
        if job.output_path.exists() and not job.options.overwrite:
            problems.append(f"{job.output_path} already exists (use --overwrite)")
    if problems:
        raise PreflightError(problems)
    return jobs


def _layout_function(job: DocumentJob) -> Callable[[int, int, tuple[float, float]], tuple[float, float, float, float]]:
    """Creates the img2pdf layout function for a job.

    img2pdf calls the function once per image in order; the natural sizes are read up front so that the
    default DPI is 300 and not the one img2pdf assumes.

    Args:
        job: The job.

    Returns:
        A layout function.
    """
    options = job.options
    layouts: list[PageLayout] = [
        compute_layout(
            read_geometry(path),
            options.output_width,
            options.output_height,
            bool(options.allow_cropping),
            bool(options.allow_stretching),
        )
        for path in job.images
    ]
    pending = iter(layouts)

    def layout(_width_px: int, _height_px: int, _dpi: tuple[float, float]) -> tuple[float, float, float, float]:
        """Returns the precomputed layout of the next image."""
        return next(pending).as_tuple()

    return layout


def stitch_document(job: DocumentJob) -> Path:
    """Creates the PDF of one job.

    Args:
        job: The planned document.

    Returns:
        The path of the created file.

    Raises:
        StitchError: If the document cannot be created.
    """
    try:
        data = img2pdf.convert([str(path) for path in job.images], layout_fun=_layout_function(job))
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        job.output_path.write_bytes(data)
    except Exception as error:  # img2pdf and Pillow raise many unrelated exception types
        raise StitchError(f"cannot create {job.output_path}: {error}") from error
    return job.output_path


def run(global_options: Options) -> RunSummary:
    """Plans and stitches all selected documents.

    Failure of one document does not stop the others.

    Args:
        global_options: Validated global options.

    Returns:
        A summary of the run.

    Raises:
        OptionsError: If the selected folders do not exist.
        PreflightError: If pre-flight checks fail; nothing is stitched in that case.
    """
    jobs = plan_jobs(global_options)
    summary = RunSummary()
    for job in jobs:
        name = job.output_path.name
        logger.info("processing %s (%d images)", job.folder, len(job.images))
        if job.warnings:
            summary.warnings[name] = list(job.warnings)
        try:
            summary.succeeded.append(stitch_document(job))
        except StitchError as error:
            logger.exception("%s", error)
            summary.failed[name] = str(error)
    return summary
