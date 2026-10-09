from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from link_doctor.check import check, render
from link_doctor.compile import compile_wiki
from link_doctor.markdown import index_markdown
from link_doctor.search import _chunks


class MarkdownIndexTests(unittest.TestCase):
    def test_ignores_code_and_tracks_duplicate_heading_anchors(self):
        doc = index_markdown("# 제목\n\n## 반복 제목\n## 반복 제목\n`[[inline]]`\n```md\n[[fenced]]\n```\n[[실제|별칭]]")
        self.assertEqual([heading.anchor for heading in doc.headings], ["제목", "반복-제목", "반복-제목-1"])
        self.assertEqual([link.target for link in doc.links], ["실제"])



class SearchChunkTests(unittest.TestCase):
    def test_tracks_real_lines_and_unique_chunk_numbers_across_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            words = [f"w{i}" for i in range(500)]
            (root / "notes.md").write_text("# Alpha\n" + " ".join(words[:420]) + "\n" + " ".join(words[420:]) + "\n## Beta\nfinal words\n", encoding="utf-8")
            chunks = _chunks(root)
            self.assertEqual([chunk["line"] for chunk in chunks], [2, 3, 5])
            self.assertEqual([chunk["chunk"] for chunk in chunks], [0, 1, 2])
            self.assertEqual([chunk["section"] for chunk in chunks], ["Alpha", "Alpha", "Beta"])

class CheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "guides").mkdir()
        (self.root / "other").mkdir()
        (self.root / "guides" / "시작 문서.md").write_text("# 시작\n\n## 설치\n내용\n", encoding="utf-8")
        (self.root / "other" / "시작 문서.md").write_text("# 시작\n", encoding="utf-8")
        (self.root / "index.md").write_text("""# 색인
aliases: 첫 화면, 홈
[[첫 화면|진입점]]
[[guides/시작 문서#설치]]
[[#색인]]
[[시작 문서]]
[한글](guides/%EC%8B%9C%EC%9E%91%20%EB%AC%B8%EC%84%9C.md#설치)
[나중 참조][가이드]
[[없음]]
[[guides]]
`[[코드]]`
```md
[[코드블록]]
```
[invalid](bad%GG.md)
[unsafe](../outside.md)
[가이드]: guides/%EC%8B%9C%EC%9E%91%20%EB%AC%B8%EC%84%9C.md#설치
""", encoding="utf-8")
        (self.root / "outside.md").write_text("outside", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_alias_anchor_duplicates_encoded_paths_and_code_exclusion(self):
        report = check(self.root)
        by_target = {item["target"]: item for item in report["results"] if item["source"] == "index.md"}
        self.assertEqual(by_target["첫 화면"]["status"], "ok")
        self.assertEqual(by_target["#색인"]["status"], "ok")
        self.assertEqual(by_target["#색인"]["reason"], "wiki target and anchor exist")
        self.assertTrue(any(item["target"].endswith("#설치") and item["source"] == "index.md" for item in report["results"]))
        self.assertEqual(by_target["guides/시작 문서#설치"]["status"], "ok")
        self.assertEqual(by_target["시작 문서"]["reason"], "ambiguous wiki target: guides/시작 문서.md, other/시작 문서.md")
        self.assertEqual(by_target["guides/%EC%8B%9C%EC%9E%91%20%EB%AC%B8%EC%84%9C.md#설치"]["status"], "ok")
        self.assertEqual(by_target["없음"]["status"], "missing")
        self.assertEqual(by_target["guides"]["reason"], "wiki target does not exist")
        self.assertEqual(by_target["../outside.md"]["status"], "skipped")
        self.assertEqual(by_target["bad%GG.md"]["status"], "skipped")
        self.assertNotIn("코드", by_target)
        self.assertNotIn("코드블록", by_target)
        self.assertTrue(all(w["kind"] == "orphan" and w["status"] == "warning" for w in report["warnings"]))

    def test_symlink_escape_skipped_and_report_escaping(self):
        external = Path(self.temp.name).parent / (Path(self.temp.name).name + "-outside.md")
        external.write_text("outside", encoding="utf-8")
        try:
            (self.root / "escape.md").symlink_to(external)
            (self.root / "index.md").write_text('[x](escape.md)\n[x]("<script>")\n', encoding="utf-8")
            report = check(self.root)
            self.assertEqual(report["results"][0]["status"], "skipped")
            html = render(report, "html")
            self.assertNotIn("<script>", html)
            self.assertIn("&lt;script&gt;", html)
        finally:
            external.unlink(missing_ok=True)


class CompileTests(unittest.TestCase):
    def test_uses_upstream_graph_rewriter_unicode_aliases_and_collision_safe_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "input"
            (root / "a").mkdir(parents=True)
            (root / "b").mkdir()
            (root / "a" / "index.md").write_text("# 항목\naliases: 별칭\n본문에서 한국어 별칭을 언급합니다.\n", encoding="utf-8")
            (root / "b" / "index.md").write_text("# 참고\n여기서 항목 이름을 언급합니다.\n", encoding="utf-8")
            output = Path(temp) / "out"
            result = compile_wiki(root, output)
            self.assertEqual(result["entities"], 2)
            self.assertTrue((output / "graph.json").is_file())
            graph = json.loads((output / "graph.json").read_text(encoding="utf-8"))
            self.assertEqual(graph["upstream_revision"], result["upstream_revision"])
            self.assertEqual(len(set(path.name for path in output.glob("*.md"))), 2)
            self.assertTrue(any(edge["incoming"] for edge in graph["entities"].values()))
            compiled = "\n".join(p.read_text(encoding="utf-8") for p in output.glob("*.md"))
            self.assertIn("## Related", compiled)

    def test_ambiguous_duplicate_names_do_not_create_arbitrary_graph_edges(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.md").write_text("# Shared Name\nmentions Shared Name here\n", encoding="utf-8")
            (root / "b.md").write_text("# Shared Name\nalso mentions Shared Name here\n", encoding="utf-8")
            result = compile_wiki(root)
            self.assertEqual(len(result["graph"]), 2)
            self.assertTrue(all(not edges["outgoing"] for edges in result["graph"].values()))


    def test_compiler_does_not_create_relations_from_inline_or_fenced_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "source.md").write_text("# Source\n`Target`\n```text\nTarget\n```\n", encoding="utf-8")
            (root / "target.md").write_text("# Target\nordinary unrelated text\n", encoding="utf-8")
            result = compile_wiki(root)
            self.assertTrue(all(not edges["outgoing"] for edges in result["graph"].values()))

if __name__ == "__main__":
    unittest.main()
