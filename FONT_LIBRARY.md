# Glyph library

## Current library

`font-library.json` is the runtime's canonical, schema-version-1 JSON
repository. It currently contains one exact face: **DejaVu Sans Book 2.37**,
with printable ASCII characters U+0020–U+007E (95 glyph records). Its font
source is not bundled. The face metadata records the source filename,
SHA-256, license reference, units-per-em, and extraction tolerance.
See [FONT-LICENSES.md](FONT-LICENSES.md) before copying or publishing the
library.

Coordinates and advances are stored in font units. The curve-flatness
tolerance is 1 font unit for the starter data. A contour stores ordered
vertices without repeating its first vertex, `closed: true`, containment
`depth`, and `role` (`outer` at even depth, `hole` at odd depth). Glyphs with
no visible outline, such as space, retain advance metrics and have no
contours. Any degenerate point contour excluded by the builder is counted in
`ignoredDegenerateContours`; this is not a missing visible outline.

The C# loader rejects unknown schema versions, duplicate face IDs/codepoints,
invalid metrics, open/degenerate/self-intersecting contours, and inconsistent
nesting. Face IDs and glyph mappings are exact; missing glyphs are reported.

## Building another face

Use a font file you are entitled to use and preserve its license information.
The builder records a SHA-256 fingerprint but does not establish licensing
rights. A stable face ID must distinguish style and source version.

```bash
python -m pip install -r requirements.txt
python build_font_library.py \
  --font /path/to/YourFace.ttf \
  --face-id your-family-regular-v1 \
  --license "License name and notice reference" \
  --curve-tolerance 1 \
  --output font-library.json
```

By default, the builder requires every printable ASCII character and fails
explicitly if a requested mapping is absent. Use `--characters` to build a
smaller deliberate subset; pass the exact characters as one shell argument.
Review the source license, metadata, generated contours, counters,
disconnected components, and DXF validation before replacing the bundled
library. Never assume that extracted geometry is cleared for redistribution
just because the source font is installed.

The builder uses FontTools at authoring time only. The WinForms application
and C# runtime do not require a separate Python installation or font file.
