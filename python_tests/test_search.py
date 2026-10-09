from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

if importlib.util.find_spec("numpy"):
    import numpy as np
    from link_doctor import search as search_module
else:
    np = None


@unittest.skipIf(np is None, "search-extra NumPy is not installed")
class SearchCacheTests(unittest.TestCase):
    def test_query_document_and_symmetric_embeddings_cache_and_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "notes"
            root.mkdir()
            (root / "a.md").write_text("# Alpha\n\n## First\nshared retrieval content", encoding="utf-8")
            (root / "b.md").write_text("# Beta\n\n## Second\nrelated shared content", encoding="utf-8")
            vectors = {
                "SearchDocument": np.zeros((2, 128), dtype=np.float32),
                "SentenceSimilarity": np.zeros((2, 128), dtype=np.float32),
            }
            vectors["SearchDocument"][0, 0] = 1
            vectors["SearchDocument"][1, 1] = 1
            vectors["SentenceSimilarity"][0, 0] = 1
            vectors["SentenceSimilarity"][1, :2] = (0.8, 0.6)
            def encode(_model, texts, task, dimension):
                if len(texts) == 1:
                    query = np.zeros((1, dimension), dtype=np.float32)
                    query[0, 0] = 1
                    return query
                return vectors[task]
            with patch.object(search_module, "_load_model", return_value=object()), patch.object(search_module, "_encode", side_effect=encode):
                first = search_module.search(root, "shared", top_k=2, dimension=128)
                second = search_module.search(root, "shared", top_k=2, dimension=128)
            self.assertFalse(first["cache_reused"])
            self.assertTrue(second["cache_reused"])
            self.assertEqual(first["results"][0]["source"], "a.md")
            self.assertTrue(first["relation_candidates"])
            self.assertEqual(first["relation_candidates"][0]["status"], "unverified semantic relation candidate")
            self.assertEqual(first["dimension"], 128)
            (root / "a.md").write_text("# Alpha\n\n## First\nchanged content invalidates vector index", encoding="utf-8")
            with patch.object(search_module, "_load_model", return_value=object()), patch.object(search_module, "_encode", side_effect=encode):
                changed = search_module.search(root, "shared", top_k=2, dimension=128)
            self.assertFalse(changed["cache_reused"])


if __name__ == "__main__":
    unittest.main()
