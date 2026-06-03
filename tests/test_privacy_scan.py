import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_FILE_SUFFIXES = {".py", ".md", ".toml", ".json", ".yml", ".yaml", ".example"}


class PublicPrivacyScanTests(unittest.TestCase):
    def iter_public_text_files(self):
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {".git", ".pytest_cache", "__pycache__", ".venv"} for part in path.parts):
                continue
            if path.suffix in TEXT_FILE_SUFFIXES or path.name in {"Dockerfile", "LICENSE"}:
                yield path

    def test_no_authenticated_urls_or_obvious_contact_values(self):
        combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in self.iter_public_text_files())
        self.assertNotRegex(combined, r"(?:serviceKey|ServiceKey|OC|api_key|token)=[A-Za-z0-9%+/_=-]{12,}")
        self.assertNotRegex(combined, r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
        self.assertNotRegex(combined, r"(?<!\d)0\d{1,2}[-. ]?\d{3,4}[-. ]?\d{4}(?!\d)")

    def test_public_repo_does_not_package_raw_data_directories(self):
        for name in ["cache", "data", "raw", "bronze", "silver", "gold"]:
            self.assertFalse((ROOT / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
