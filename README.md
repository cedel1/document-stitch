# document-stitch

Stitches folders of page images into multi-page PDF documents.

## Installation

```bash
uv sync
```

## Usage

```bash
./document_stitch.py --document-folder scans/book1
./document_stitch.py --documents-folders scans --output-folder /tmp/pdfs --overwrite --verbose
```

Exactly one of `--documents-folders` (a directory with one sub-folder of images per document) or
`--document-folder` (a single document) is required.

| Option                           | Description                                                                          |
|----------------------------------|--------------------------------------------------------------------------------------|
| `--output-folder`                | Relative: relative to each document folder. Absolute: used as is. Default: next to the images. |
| `--overwrite`                    | Allow overwriting existing documents.                                                |
| `--document-name`                | Name of the output file (without extension).                                         |
| `--use-properties-file`          | Use `properties.txt` for the name (`Title_Part title`) and the page order.           |
| `--allow-natural-sorting-fallback` | If pages cannot be matched to `properties.txt`, warn and use natural order instead of failing. |
| `--output-width`, `--output-height` | Page size in mm. One value: the other follows each image's aspect ratio. Both: every page has exactly that size. Default: original size. |
| `--allow-cropping`               | Larger images are scaled to cover the page and the overflow is cropped (needs both dimensions). |
| `--allow-stretching`             | Smaller images are stretched to fill the page (needs both dimensions).               |
| `--config`                       | Configuration file; replaces `document-stitch.toml` next to the script.              |
| `--verbose`                      | Log progress (INFO). Warnings and errors are always logged.                          |

## Configuration

Options can be set in TOML files using the hyphenated CLI names (`config` and `verbose` are CLI-only):

```toml
output-width = 210
output-height = 297
allow-stretching = true
use-properties-file = true
order = ["cover.jpg", "page_001.jpg"]   # explicit order, remaining files follow in natural order
```

Precedence: CLI, then the global config (`--config`, else `document-stitch.toml` next to the script), then
`document-stitch.toml` inside each document folder. Options are merged per option. Per-folder configs cannot
select folders. Relative `output-folder` values are relative to each document folder.

## Behaviour

- **Page order:** natural sort by default; `order` entries come first; with `--use-properties-file`, the order of the
  `pages:` list is used, matching files by full UUID or the first UUID segment in the file name.
- **Naming:** `--document-name`, then properties, then the folder name. Illegal characters become `_`; extension is `.pdf`.
  With `--documents-folders`, an absolute `--output-folder` and `--document-name`, `_N` numbering is appended.
- **Sizing:** image size in mm is taken from its DPI (300 if absent). Without cropping or stretching, larger images are
  scaled to fit and smaller ones are centred on white.
- **Pre-flight checks** run before anything is stitched: duplicate output paths (regardless of `--overwrite`),
  existing files without `--overwrite`, and folders without images abort the run.
- **Exit status:** 0 on success; non-zero on errors. A failing document does not stop the others.
  A summary is printed and logged.

## Development

```bash
uv run pytest
uv run black .
uv run pylint src
uv run pylint document_stitch.py
uv run pylint test
```
