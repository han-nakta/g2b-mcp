import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from g2b_mcp import server


class PublicMcpToolTests(unittest.TestCase):
    def setUp(self):
        os.environ["G2B_ARTIFACT_DIR"] = str(ROOT / "artifacts")

    def test_list_services_public_safe(self):
        result = server.g2b_list_services()
        self.assertEqual(result["service_count"], 18)
        self.assertTrue(result["privacy"]["no_raw_rows"])
        self.assertIn("bid_public_info", {svc["slug"] for svc in result["services"]})

    def test_list_operations_summarizes_sensitive_fields(self):
        result = server.g2b_list_operations("bid_public_info")
        self.assertGreater(result["operation_count"], 0)
        op = result["operations"][0]
        self.assertIn("sensitive_field_count", op)
        self.assertNotIn("sample_output_fields", op)

    def test_describe_operation_can_include_safe_field_names_without_raw_rows(self):
        result = server.g2b_describe_operation("bid_public_info", "getBidPblancListInfoThng", include_fields=True)
        operation = result["operation"]
        self.assertIn("safe_response_field_names", operation)
        serialized = repr(result)
        self.assertNotRegex(serialized, r'serviceKey=[^&\\s\'\"]+')

    def test_relationship_queries(self):
        all_edges = server.g2b_graph_list_relationships()
        self.assertGreaterEqual(all_edges["edge_count"], 1)
        edge_id = all_edges["edges"][0]["id"]
        one = server.g2b_graph_get_edge_evidence(edge_id)
        self.assertEqual(one["edge"]["id"], edge_id)

    def test_dataset_status_does_not_read_private_cache(self):
        result = server.g2b_dataset_status()
        self.assertEqual(result["state"], "not_packaged")
        self.assertTrue(result["privacy"]["no_live_fetch"])

    def test_privacy_boundary_contract(self):
        boundary = server.g2b_privacy_boundary()
        self.assertIn("raw G2B response rows and operator caches", boundary["excluded"])
        self.assertTrue(boundary["no_credentials"])


if __name__ == "__main__":
    unittest.main()
