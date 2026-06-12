import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from g2b_mcp import server


class ApiKeySetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env_file = Path(self.tmp.name) / "g2b.env"
        self.env_patcher = patch.dict(
            os.environ,
            {
                "G2B_SERVICE_KEY": "",
                "G2B_BID_PUBLIC_INFO_API_KEY": "",
                "G2B_ENABLE_LIVE_FETCH": "",
            },
            clear=False,
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()
        self.tmp.cleanup()

    def test_setup_writes_user_key_to_0600_env_file_without_echoing_secret(self):
        result = server.setup_api_key_env_file("TOPSECRET", self.env_file)
        self.assertTrue(result["saved"])
        self.assertEqual(result["env_file"], str(self.env_file))
        self.assertEqual(result["env_name"], "G2B_SERVICE_KEY")
        self.assertFalse(result["key_exposed"])
        self.assertNotIn("TOPSECRET", repr(result))
        self.assertEqual(self.env_file.read_text(encoding="utf-8"), "G2B_SERVICE_KEY=TOPSECRET\n")
        mode = stat.S_IMODE(self.env_file.stat().st_mode)
        self.assertEqual(mode, 0o600)

    def test_setup_preserves_other_lines_and_replaces_existing_key(self):
        self.env_file.write_text("# note\nOTHER=value\nG2B_SERVICE_KEY=OLD\n", encoding="utf-8")
        os.chmod(self.env_file, 0o644)
        result = server.setup_api_key_env_file("NEWSECRET", self.env_file)
        self.assertTrue(result["saved"])
        text = self.env_file.read_text(encoding="utf-8")
        self.assertIn("# note\n", text)
        self.assertIn("OTHER=value\n", text)
        self.assertIn("G2B_SERVICE_KEY=NEWSECRET\n", text)
        self.assertNotIn("OLD", text)
        mode = stat.S_IMODE(self.env_file.stat().st_mode)
        self.assertEqual(mode, 0o600)

    def test_load_env_file_does_not_override_existing_process_env_by_default(self):
        self.env_file.write_text("G2B_SERVICE_KEY=FILESECRET\n", encoding="utf-8")
        os.environ["G2B_SERVICE_KEY"] = "PROCESSSECRET"
        loaded = server.load_env_file(self.env_file)
        self.assertEqual(loaded, {"G2B_SERVICE_KEY": "loaded"})
        self.assertEqual(os.environ["G2B_SERVICE_KEY"], "PROCESSSECRET")

    def test_load_env_file_can_set_missing_key_without_returning_value(self):
        self.env_file.write_text("G2B_SERVICE_KEY=FILESECRET\n", encoding="utf-8")
        os.environ["G2B_SERVICE_KEY"] = ""
        loaded = server.load_env_file(self.env_file)
        self.assertEqual(loaded, {"G2B_SERVICE_KEY": "loaded"})
        self.assertEqual(os.environ["G2B_SERVICE_KEY"], "FILESECRET")
        self.assertNotIn("FILESECRET", repr(loaded))

    def test_env_file_cannot_enable_live_fetch_by_itself(self):
        self.env_file.write_text("G2B_SERVICE_KEY=FILESECRET\nG2B_ENABLE_LIVE_FETCH=1\n", encoding="utf-8")
        os.environ["G2B_SERVICE_KEY"] = ""
        os.environ["G2B_ENABLE_LIVE_FETCH"] = ""
        loaded = server.load_env_file(self.env_file)
        self.assertEqual(loaded, {"G2B_SERVICE_KEY": "loaded"})
        self.assertEqual(os.environ["G2B_SERVICE_KEY"], "FILESECRET")
        self.assertEqual(os.environ["G2B_ENABLE_LIVE_FETCH"], "")
        self.assertFalse(server.g2b_check_api_key()["live_fetch_enabled"])

    def test_live_enabled_can_use_loaded_env_file_key_without_exposing_it(self):
        server.setup_api_key_env_file("FILESECRET", self.env_file)
        os.environ["G2B_ENABLE_LIVE_FETCH"] = "1"
        os.environ["G2B_SERVICE_KEY"] = ""
        loaded = server.load_env_file(self.env_file)
        result = server.g2b_check_api_key()
        self.assertEqual(loaded, {"G2B_SERVICE_KEY": "loaded"})
        self.assertTrue(result["configured"])
        self.assertEqual(result["configured_env"], "G2B_SERVICE_KEY")
        self.assertNotIn("FILESECRET", repr(result))


if __name__ == "__main__":
    unittest.main()
