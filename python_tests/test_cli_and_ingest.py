from __future__ import annotations

import io
import json
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from link_doctor.cli import main
from link_doctor.ingest import ingest


class CliTests(unittest.TestCase):
    def test_check_exit_policy_and_output_formats(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("# A\n[[missing]]\n", encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["check", str(root), "--format", "json"]), 1)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["counts"]["missing"], 1)
            html_path = root.parent / (root.name + "-report.html")
            try:
                self.assertEqual(main(["check", str(root), "--format", "html", "--output", str(html_path)]), 1)
                self.assertIn("<table>", html_path.read_text(encoding="utf-8"))
            finally:
                html_path.unlink(missing_ok=True)

    def test_html_output_cannot_overwrite_markdown_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "index.md"
            source.write_text("# Safe input", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["check", str(root), "--format", "html", "--output", str(source)]), 2)
            self.assertEqual(source.read_text(encoding="utf-8"), "# Safe input")

    def test_compile_html_keeps_stdout_valid_and_sends_summary_to_stderr(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "input"
            root.mkdir()
            (root / "a.md").write_text("# A\n", encoding="utf-8")
            output = Path(temp) / "compiled"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(main(["compile", str(root), "--output", str(output), "--format", "html"]), 0)
            self.assertTrue(stdout.getvalue().startswith("<!doctype html>"))
            self.assertIn("Compiled 1 pages", stderr.getvalue())

    def test_missing_docling_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sample.pdf").write_bytes(b"not a pdf")
            # Force lazy dependency path independent of the local extras installation.
            with patch.dict(sys.modules, {"docling_core": None, "docling_core.types": None, "docling_core.types.doc": None}):
                with self.assertRaisesRegex(RuntimeError, "install with.*ingest"):
                    ingest(root, root.parent / (root.name + "-out"))

    def test_ingest_writes_manifest_without_mutating_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "input"
            root.mkdir()
            original = root / "report.pdf"
            original.write_bytes(b"fixture bytes")
            output = Path(temp) / "out"
            class Item:
                text = "Title"
                prov = [types.SimpleNamespace(page_no=2)]
            class Document:
                def iterate_items(self):
                    yield Item(), 0
                def export_to_markdown(self, **kwargs):
                    return "# Title\n\nText\n"
            class Converter:
                def convert(self, source):
                    self.source = source
                    return types.SimpleNamespace(document=Document())
            fake_modules = {
                "docling_core": types.ModuleType("docling_core"),
                "docling_core.types": types.ModuleType("docling_core.types"),
                "docling_core.types.doc": types.ModuleType("docling_core.types.doc"),
                "docling": types.ModuleType("docling"),
                "docling.document_converter": types.ModuleType("docling.document_converter"),
            }
            fake_modules["docling_core.types.doc"].ImageRefMode = types.SimpleNamespace(REFERENCED="referenced")
            fake_modules["docling.document_converter"].DocumentConverter = Converter
            with patch.dict(sys.modules, fake_modules):
                result = ingest(root, output)
            self.assertEqual(original.read_bytes(), b"fixture bytes")
            self.assertEqual(result["schema_version"], 1)
            manifest = json.loads((output / ".link-doctor" / "provenance.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["documents"][0]["provenance"][0]["page"], 2)
            self.assertEqual(manifest["documents"][0]["provenance"][0]["markdown_line"], 1)


if __name__ == "__main__":
    unittest.main()
