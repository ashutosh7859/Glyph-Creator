import json
import tempfile
import unittest
from pathlib import Path

import ezdxf

from glyph_creator import DEFAULT_GLYPHS, export_dxf, layout_text, load_glyphs


class GlyphCreatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_glyphs(DEFAULT_GLYPHS)

    def test_definitions_include_ascii_printable_characters(self):
        for character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
            with self.subTest(character=character):
                self.assertIn(character, self.data["glyphs"])
        for character in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ ":
            with self.subTest(character=character):
                self.assertIn(character, self.data["glyphs"])

    def test_lowercase_uses_uppercase_strokes(self):
        self.assertEqual(
            layout_text("a", self.data, 14, 0),
            layout_text("A", self.data, 14, 0),
        )

    def test_layout_scales_and_advances_glyphs(self):
        lines = layout_text("AA", self.data, 14, 2)
        self.assertEqual(4, len(lines))
        self.assertEqual((1.0, 11.0), lines[0][1])
        self.assertEqual(15.0, lines[2][0][0])

    def test_dxf_export_writes_open_glyph_polylines(self):
        lines = layout_text("A", self.data, 20, 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "glyph.dxf"
            export_dxf(lines, path)
            modelspace = ezdxf.readfile(path).modelspace()
            entities = list(modelspace.query("LWPOLYLINE"))
        self.assertEqual(len(lines), len(entities))
        self.assertTrue(all(not entity.closed for entity in entities))
        self.assertTrue(all(entity.dxf.layer == "GLYPHS" for entity in entities))

    def test_unsupported_character_is_reported(self):
        with self.assertRaisesRegex(ValueError, "No glyph is defined"):
            layout_text("\N{SNOWMAN}", self.data, 20, 2)

    def test_invalid_definition_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "glyphs.json"
            path.write_text(json.dumps({"glyphs": [], "aliases": {}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must contain a 'glyphs' object"):
                load_glyphs(path)


if __name__ == "__main__":
    unittest.main()
