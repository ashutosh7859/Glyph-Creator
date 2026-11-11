import tempfile
import unittest
from pathlib import Path

from build_font_library import build_font_library


FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


@unittest.skipUnless(FONT.is_file(), "DejaVu Sans test font is not installed")
class FontLibraryBuilderTests(unittest.TestCase):
    def test_builds_glyph_metrics_and_counter_contours(self):
        library = build_font_library(
            FONT,
            "dejavu-sans-book-test",
            "Bitstream Vera / DejaVu license; see FONT-LICENSES.md",
            "ABO8 u",
        )
        face = library["faces"][0]
        glyphs = {glyph["codePoint"]: glyph for glyph in face["glyphs"]}

        self.assertEqual(1, library["schemaVersion"])
        self.assertGreater(face["unitsPerEm"], 0)
        self.assertEqual(6, len(glyphs))
        self.assertEqual([], glyphs[ord(" ")]["contours"])
        self.assertEqual(1, glyphs[ord("u")]["ignoredDegenerateContours"])
        self.assertEqual(3, len(glyphs[ord("B")]["contours"]))
        self.assertEqual(2, len(glyphs[ord("O")]["contours"]))
        self.assertTrue(all(c["closed"] for c in glyphs[ord("8")]["contours"]))
        self.assertEqual(
            {"outer", "hole"},
            {contour["role"] for contour in glyphs[ord("B")]["contours"]},
        )
        self.assertEqual(
            2,
            sum(contour["role"] == "hole" for contour in glyphs[ord("B")]["contours"]),
        )

    def test_requires_source_license_and_positive_tolerance(self):
        with self.assertRaisesRegex(ValueError, "license"):
            build_font_library(FONT, "font", "", "A")
        with self.assertRaisesRegex(ValueError, "tolerance"):
            build_font_library(FONT, "font", "license", "A", 0)

    def test_rejects_missing_glyphs(self):
        with self.assertRaisesRegex(ValueError, "does not contain a glyph"):
            build_font_library(FONT, "font", "license", "\U0010ffff")


if __name__ == "__main__":
    unittest.main()
