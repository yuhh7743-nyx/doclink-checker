# Doclink

A small command-line tool that finds broken file links and heading anchors in
Markdown documentation. Optional HTTP checks help catch dead web links too.

Doclink is a new project at version 0.1.0. It is intended for small documentation
repositories, with readable code and a small dependency footprint.

## Install

Requires Python 3.10 or newer. Open a terminal in this project folder.

```sh
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Or on macOS / Linux:

```sh
source .venv/bin/activate
```

Then install from the local source:

```sh
python -m pip install -e .
doclink --help
```

If PowerShell blocks activation, run `.venv\Scripts\python.exe -m pip install -e .`
and `.venv\Scripts\python.exe -m doclink .` instead. On systems where Python is
named `python3`, use that command to create the environment.

This project is not published on PyPI. Install from this folder; the package
name's availability on public registries has not been checked.

## Usage

```sh
doclink .
doclink . --exclude 'vendor' --exclude 'generated/*'
doclink . --online --timeout 5
doclink . --json
python -m doclink .
```

Pass the repository root so links such as `../README.md` remain inside the
checked tree. Leading-slash links resolve from that root. A missing file gives
output like:

```text
docs/guide.md:12: 'missing.md': file or directory does not exist
3 file(s), 7 link(s) checked, 2 skipped, 1 issue(s)
```

Exit codes: **0** = no issues among checked links, **1** = link/read issues,
**2** = invalid arguments or no Markdown files found. Skipped links are not
validated. Line numbers identify the beginning of the containing Markdown
block, so a link in a multiline paragraph can appear later in that block.

## What gets checked

- `.md` and `.markdown` files, recursively, including uppercase extensions.
- Inline links, images, defined reference links, and angle-bracket autolinks.
- Relative files, directories, percent-encoded paths, and local Markdown anchors.
- ATX and Setext headings, with lowercase IDs, punctuation removal, spaces
  changed to hyphens, and numbered duplicate IDs (`title`, `title-1`).
- HTTP(S) when `--online` is given: redirects followed, HEAD requests first,
  GET fallback for HTTP 405 or 501, with repeated URLs cached for that run.

Code spans and fenced code blocks are ignored. Default ignored directories:
`.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `build`, and `dist`.
Symlinks are not scanned; local targets that resolve outside the root are
reported. `--exclude` matches root-relative paths using Python shell-style
globs and can be repeated; `*` can match slashes. `.gitignore` is not read.

## Limits and HTTP behavior

This is a focused Markdown checker, not a full static-site renderer. Raw HTML
links and custom HTML IDs, MDX, front matter semantics, undefined reference
labels, bare URLs, and generated site routes are not interpreted. Heading
IDs are GitHub-style but may differ from a particular site's renderer for
unusual symbols or extensions. Fragments on non-Markdown files and remote
pages are not validated. Query strings are ignored for local paths.

Web checks are opt-in and request the URLs in your documents, including local
network URLs and redirect destinations. Use them on documentation you trust.
Checks run sequentially; the timeout applies to network operations, not the
total run. HTTP errors, network failures, and timeouts are reported as issues;
authentication, rate limits, and bot protection can cause false positives.
Other URL schemes and protocol-relative URLs are skipped.

## Development

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
doclink .
```

Tests use temporary files and a local HTTP server, without contacting public
websites. The only runtime dependency is markdown-it-py, used for Markdown
tokenization; networking and the CLI use Python's standard library.

See [contributing](CONTRIBUTING.md) for a first change and
[publishing](PUBLISHING.md) for creating your GitHub repository.

## License

[MIT](LICENSE).
