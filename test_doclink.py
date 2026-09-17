import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import URLError

from doclink.cli import check, discover, main, parse_document, web_error


class ParserTests(unittest.TestCase):
    def test_commonmark_links_and_code(self):
        links, _ = parse_document('''[nested](a(b).md)
![image](pic.png)
[reference][id]
<https://example.com>
`[ignored](bad.md)`

```
[ignored](bad.md)
```

[id]: other.md "Title"
''')
        self.assertEqual([url for _, url in links],
                         ["a(b).md", "pic.png", "other.md", "https://example.com"])

    def test_formatted_unicode_and_duplicate_headings(self):
        _, anchors = parse_document("# Hello *World*!\n# Hello World!\n# Hello World-1\n# Café\nTitle\n===\n")
        self.assertEqual(anchors, {"hello-world", "hello-world-1", "hello-world-1-1", "café", "title"})


class FileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_local_links_and_fragments(self):
        source = self.write("README.md", "[ok](docs/a%20b.md#caf%C3%A9)\n\n[bad](gone.md)\n\n[heading](docs/a%20b.md#missing)\n\n![image](pic.png)\n")
        self.write("docs/a b.md", "# Café\n")
        self.write("pic.png", "placeholder")
        result = check(self.root, [source])
        self.assertEqual(result["checked"], 4)
        self.assertEqual([(i["line"], i["target"]) for i in result["issues"]],
                         [(3, "gone.md"), (5, "docs/a%20b.md#missing")])

    def test_root_relative_self_query_and_escape(self):
        source = self.write("docs/a.md", "# Start\n[self](#start)\n[root](/README.md?raw=1#home)\n[out](../../outside.md)\n")
        self.write("README.md", "# Home\n")
        result = check(self.root, [source])
        self.assertEqual(len(result["issues"]), 1)
        self.assertIn("outside", result["issues"][0]["message"])

    def test_offline_and_other_schemes_are_skipped(self):
        source = self.write("a.md", "[web](https://example.com) [email](mailto:a@example.com) [cdn](//example.com/a)")
        result = check(self.root, [source])
        self.assertEqual((result["checked"], result["skipped"], result["issues"]), (0, 3, []))

    def test_exclusions_and_default_ignored_directories(self):
        self.write("README.md", "")
        self.write("docs/a.MD", "")
        self.write("vendor/a.md", "")
        self.write(".venv/a.md", "")
        self.assertEqual([p.relative_to(self.root).as_posix() for p in discover(self.root, ["vendor", "docs/*.MD"])], ["README.md"])

    def test_invalid_utf8_is_reported(self):
        source = self.root / "bad.md"
        source.write_bytes(b"\xff")
        self.assertIn("cannot read", check(self.root, [source])["issues"][0]["message"])

    def test_cli_json_and_exit_codes(self):
        source = self.write("README.md", "[bad](missing.md)")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main([str(self.root), "--json"]), 1)
        self.assertEqual(json.loads(output.getvalue())["issues"][0]["file"], "README.md")
        source.write_text("# Good\n[ok](#good)", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.root)]), 0)

    def test_empty_root_and_invalid_arguments_exit_two(self):
        for args in ([str(self.root)], [str(self.root / "missing")], ["--timeout", "nan"], ["--timeout", "0"]):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(args)
            self.assertEqual(caught.exception.code, 2)


class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/ok")
        else:
            self.send_response({"/ok": 200, "/fallback": 405}.get(self.path, 404))
        self.end_headers()

    def do_GET(self):
        self.send_response(200 if self.path in {"/ok", "/fallback"} else 404)
        self.end_headers()

    def log_message(self, *args):
        pass


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_success_redirect_fallback_and_missing(self):
        for endpoint in ("/ok", "/redirect", "/fallback"):
            with self.subTest(endpoint=endpoint):
                self.assertIsNone(web_error(self.base + endpoint, 2))
        self.assertIn("HTTP 404", web_error(self.base + "/missing", 2))

    def test_online_check_integration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source = root / "a.md"
            source.write_text(f"[ok]({self.base}/ok#ignored) [bad]({self.base}/missing)", encoding="utf-8")
            report = check(root, [source], online=True, timeout=2)
            self.assertEqual(report["checked"], 2)
            self.assertEqual(len(report["issues"]), 1)

    def test_network_errors_are_reported(self):
        for error in (URLError("connection refused"), TimeoutError("timed out")):
            with self.subTest(error=error), patch("doclink.cli.urlopen", side_effect=error):
                self.assertIn("request failed", web_error(self.base, 0.1))

    def test_repeated_urls_share_one_request(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source = root / "a.md"
            source.write_text("[a](https://example.com/a#one) [b](https://example.com/a#two)", encoding="utf-8")
            with patch("doclink.cli.web_error", return_value=None) as request:
                result = check(root, [source], online=True)
            request.assert_called_once_with("https://example.com/a", 10)
            self.assertEqual(result["checked"], 2)


if __name__ == "__main__":
    unittest.main()
