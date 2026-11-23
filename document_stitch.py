#!/usr/bin/env python3
"""Command line controller of document-stitch: parses and validates options, then calls the library."""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# This file shares its name with the package it imports, which static analysis cannot resolve.
# pylint: disable=wrong-import-position,import-error,no-name-in-module
from document_stitch.config import resolve_global_options
from document_stitch.errors import DocumentStitchError, PreflightError
from document_stitch.options import Options
from document_stitch.stitcher import RunSummary, run

logger = logging.getLogger("document_stitch")


def build_parser() -> argparse.ArgumentParser:
    """Builds the command line parser.

    Returns:
        The parser. Options that are not given default to ``None`` so that configuration files can supply them.
    """
    parser = argparse.ArgumentParser(description="Stitch folders of page images into multi-page PDF documents.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--documents-folders", type=Path, help="directory with one sub-folder of images per document")
    source.add_argument("--document-folder", type=Path, help="directory with the images of a single document")
    parser.add_argument(
        "--output-folder",
        type=Path,
        help="where to save the documents; relative paths are relative to each document folder "
        "(default: next to the source images)",
    )
    parser.add_argument("--overwrite", action="store_true", default=None, help="allow overwriting existing documents")
    parser.add_argument("--document-name", help="name of the output document (without extension)")
    parser.add_argument(
        "--use-properties-file",
        action="store_true",
        default=None,
        help="use properties.txt (if present) for the document name and the page order",
    )
    parser.add_argument(
        "--allow-natural-sorting-fallback",
        action="store_true",
        default=None,
        help="warn and use natural order when the properties file cannot order the pages",
    )
    parser.add_argument("--output-width", type=float, help="page width in mm (default: original size)")
    parser.add_argument("--output-height", type=float, help="page height in mm (default: original size)")
    parser.add_argument(
        "--allow-cropping",
        action="store_true",
        default=None,
        help="crop images larger than the page instead of fitting them (needs width and height)",
    )
    parser.add_argument(
        "--allow-stretching",
        action="store_true",
        default=None,
        help="stretch images smaller than the page to fill it (needs width and height)",
    )
    parser.add_argument(
        "--config", type=Path, help="configuration file (default: document-stitch.toml next to this script)"
    )
    parser.add_argument("--verbose", action="store_true", help="log progress")
    return parser


def options_from_args(args: argparse.Namespace) -> Options:
    """Converts parsed arguments into options.

    Args:
        args: Parsed command line.

    Returns:
        The options given on the command line.
    """
    return Options(
        documents_folders=args.documents_folders,
        document_folder=args.document_folder,
        output_folder=args.output_folder,
        overwrite=args.overwrite,
        document_name=args.document_name,
        use_properties_file=args.use_properties_file,
        allow_natural_sorting_fallback=args.allow_natural_sorting_fallback,
        output_width=args.output_width,
        output_height=args.output_height,
        allow_cropping=args.allow_cropping,
        allow_stretching=args.allow_stretching,
    )


def format_summary(summary: RunSummary) -> list[str]:
    """Formats the final summary.

    Args:
        summary: Outcome of the run.

    Returns:
        Summary lines.
    """
    lines = [
        f"Summary: {len(summary.succeeded)} succeeded, {len(summary.warnings)} with warnings, "
        f"{len(summary.failed)} failed"
    ]
    lines += [f"  succeeded: {path}" for path in summary.succeeded]
    lines += [f"  warning: {name}: {'; '.join(items)}" for name, items in summary.warnings.items()]
    lines += [f"  failed: {name}: {message}" for name, message in summary.failed.items()]
    return lines


def main(argv: list[str] | None = None, script_dir: Path | None = None) -> int:
    """Runs the program.

    Args:
        argv: Command line arguments without the program name; ``sys.argv`` is used if omitted.
        script_dir: Directory searched for the global configuration file; defaults to this script's directory.

    Returns:
        The exit status: 0 on success, 1 on errors, 2 on invalid usage.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s: %(message)s")
    script_dir = script_dir or Path(__file__).resolve().parent
    try:
        options = resolve_global_options(options_from_args(args), script_dir, args.config)
        summary = run(options)
    except PreflightError as error:
        for message in error.messages:
            logger.error("%s", message)
        return 1
    except DocumentStitchError as error:
        logger.exception("%s", error)
        return 2
    for line in format_summary(summary):
        logger.info(line)
        print(line)
    return 1 if summary.has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
