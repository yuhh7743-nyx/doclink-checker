"""Small, deliberately synchronous documentation checker."""

import argparse
from dataclasses import asdict, dataclass
import fnmatch
import json
import math
import os
from pathlib import Path
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urldefrag, urlsplit
from urllib.request import Request, urlopen

from markdown_it import MarkdownIt

MARKDOWN = {".md", ".markdown"}
IGNORED = {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist"}


@dataclass
class Issue:
    file: str
    line: int
    target: str
    message: str


def parse_document(text):
    """Return links (block-start line, URL) and GitHub-style heading IDs."""
    tokens = MarkdownIt("commonmark").enable(["table", "strikethrough"]).parse(text)
    links, anchors = [], set()
    for i, token in enumerate(tokens):
        if token.type != "inline":
            continue
        children = token.children or []
        line = token.map[0] + 1 if token.map else 1
        for child in children:
            if child.type in {"link_open", "image"}:
                links.append((line, child.attrGet("href" if child.type == "link_open" else "src")))
        if i and tokens[i - 1].type == "heading_open":
            label = "".join(c.content if c.type in {"text", "code_inline", "image"}
                            else " " if c.type in {"softbreak", "hardbreak"} else ""
                            for c in children).lower()
            slug = "".join(c for c in label if c in "_- " or
                           unicodedata.category(c)[0] in {"L", "N", "M"}).replace(" ", "-")
            anchor, suffix = slug, 0
            while anchor in anchors:
                suffix += 1
                anchor = f"{slug}-{suffix}"
            anchors.add(anchor)
    return links, anchors


def web_error(url, timeout):
    """Follow redirects, trying GET when a server rejects HEAD."""
    for method in ("HEAD", "GET"):
        try:
            request = Request(url, method=method, headers={"User-Agent": "doclink-checker/0.1"})
            with urlopen(request, timeout=timeout):
                return None
        except HTTPError as exc:
            exc.close()
            if method == "HEAD" and exc.code in {405, 501}:
                continue
            return f"HTTP {exc.code} (may require authentication or allowlisting)"
        except (URLError, OSError, ValueError) as exc:
            return f"request failed: {exc}"


def discover(root, excludes):
    def scan_error(error):
        raise error

    files = []
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=scan_error):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED and
                         not Path(directory, d).is_symlink() and
                         not any(fnmatch.fnmatch(Path(directory, d).relative_to(root).as_posix(), p)
                                 for p in excludes))
        for name in sorted(names):
            path = Path(directory, name)
            relative = path.relative_to(root).as_posix()
            if path.suffix.lower() in MARKDOWN and not path.is_symlink() and not any(
                    fnmatch.fnmatch(relative, p) for p in excludes):
                files.append(path)
    return sorted(files)


def check(root, files, online=False, timeout=10):
    issues, documents, urls = [], {}, {}
    checked = skipped = 0

    def document(path):
        if path not in documents:
            documents[path] = parse_document(path.read_text(encoding="utf-8-sig"))
        return documents[path]

    for source in files:
        relative = source.relative_to(root).as_posix()
        try:
            links, _ = document(source)
        except (OSError, UnicodeError) as exc:
            issues.append(Issue(relative, 1, "", f"cannot read Markdown: {exc}"))
            continue
        for line, target in links:
            message = None
            try:
                parts = urlsplit(target)
                if parts.scheme in {"http", "https"}:
                    if not online:
                        skipped += 1
                        continue
                    checked += 1
                    url = urldefrag(target)[0]
                    if url not in urls:
                        urls[url] = web_error(url, timeout)
                    message = urls[url]
                elif parts.scheme or parts.netloc:
                    skipped += 1
                    continue
                else:
                    checked += 1
                    raw = unquote(parts.path)
                    if raw.startswith("/"):
                        path = root / raw.lstrip("/")
                    else:
                        path = source.parent / raw if raw else source
                    path = path.resolve()
                    if not path.is_relative_to(root):
                        message = "target is outside the documentation root"
                    elif not path.exists():
                        message = "file or directory does not exist"
                    elif parts.fragment and path.suffix.lower() in MARKDOWN and path.is_file():
                        if unquote(parts.fragment) not in document(path)[1]:
                            message = f"heading #{unquote(parts.fragment)} does not exist"
            except (OSError, UnicodeError, ValueError) as exc:
                message = f"cannot check target: {exc}"
            if message:
                issues.append(Issue(relative, line, target, message))
    return {"files": len(files), "checked": checked, "skipped": skipped,
            "issues": [asdict(issue) for issue in issues]}


def positive_timeout(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("timeout must be a finite positive number")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check Markdown links in a directory (offline by default).")
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--online", action="store_true", help="also request HTTP(S) URLs")
    parser.add_argument("--timeout", type=positive_timeout, default=10, help="HTTP timeout in seconds (default: 10)")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB", help="skip root-relative paths; repeatable")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")
    try:
        files = discover(root, args.exclude)
    except OSError as exc:
        parser.error(f"cannot scan directory: {exc}")
    if not files:
        parser.error("no Markdown files found")
    result = check(root, files, args.online, args.timeout)
    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        for issue in result["issues"]:
            print(f"{issue['file']}:{issue['line']}: {issue['target']!r}: {issue['message']}")
        print(f"{result['files']} file(s), {result['checked']} link(s) checked, "
              f"{result['skipped']} skipped, {len(result['issues'])} issue(s)")
    return 1 if result["issues"] else 0
