from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ArtifactPackagingTests(unittest.TestCase):
    def test_core_artifacts_are_valid_json(self):
        for name in [
            "catalog.json",
            "entity_dictionary.json",
            "graph_schema.json",
            "join_map.json",
            "relationship_evidence_graph.json",
            "ontology_pack.json",
        ]:
            with self.subTest(name=name):
                path = ROOT / "artifacts" / name
                self.assertTrue(path.exists(), name)
                json.loads(path.read_text(encoding="utf-8"))

    def test_no_cache_directory_packaged(self):
        self.assertFalse((ROOT / "cache").exists())


if __name__ == "__main__":
    unittest.main()
