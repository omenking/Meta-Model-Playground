"""Focused tests for generate_jolly_sheet helpers (stdlib unittest, no network)."""

import tempfile
import unittest
from pathlib import Path

import generate_jolly_sheet as gen


class TestBuildInput(unittest.TestCase):
    def test_text_only_returns_prompt_string(self):
        self.assertEqual(gen.build_input("hello", None), "hello")

    def test_reference_image_attaches_data_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / "ref.webp"
            img.write_bytes(b"\x00\x01\x02")
            result = gen.build_input("hello", [str(img)])
            parts = result[0]["content"]
            self.assertEqual(parts[0], {"type": "input_text", "text": "hello"})
            self.assertEqual(parts[1]["type"], "input_image")
            self.assertTrue(
                parts[1]["image_url"].startswith("data:image/webp;base64,")
            )


class TestEnsureOutAvailable(unittest.TestCase):
    def test_missing_path_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = gen.ensure_out_available(Path(tmp) / "new.webp", False)
            self.assertFalse(out.exists())

    def test_existing_path_is_refused_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / "sheet.webp"
            existing.write_bytes(b"x")
            with self.assertRaises(RuntimeError):
                gen.ensure_out_available(existing, False)

    def test_existing_path_is_allowed_with_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / "sheet.webp"
            existing.write_bytes(b"x")
            self.assertEqual(gen.ensure_out_available(existing, True), existing)


if __name__ == "__main__":
    unittest.main()
