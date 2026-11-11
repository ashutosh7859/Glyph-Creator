# CAD Text Creator

CAD Text Creator is a local Windows desktop application that composes text
from stored font glyph outlines and exports editable closed `LWPOLYLINE`
contours to DXF. AutoCAD/Civil 3D is an optional downstream consumer; the
application does not run as an AutoCAD command and does not require AutoCAD.

The current library supports printable ASCII (U+0020–U+007E) in the exact
**DejaVu Sans Book 2.37** face. Missing characters and unsupported text are
reported rather than substituted or dropped. Shaping, kerning, bidirectional
layout, complex scripts, and multiline text are not implemented.

## Run the desktop app

Requires Windows and the .NET 8 SDK/runtime, including Windows Desktop
Runtime.

```powershell
dotnet run --project CadTextCreator.App/CadTextCreator.App.csproj
```

The UI provides text entry, exact face selection, height, width factor,
tracking, rotation, insertion origin, a geometry preview, and DXF export.
Height scales the font's units-per-em to drawing units. Width factor scales
horizontal glyph geometry and advances. Tracking is an additional drawing
unit gap between adjacent characters (negative tracking tightens spacing).
Rotation is counter-clockwise about
the baseline insertion origin. DXF `$INSUNITS` is unitless; output uses the
user's drawing units.

The app ships with `font-library.json`, a geometry-only library. It does not
bundle the source font binary; see [FONT-LICENSES.md](FONT-LICENSES.md).

## Build and validate

```bash
dotnet build CadTextCreator.Core/CadTextCreator.Core.csproj
dotnet build CadTextCreator.App/CadTextCreator.App.csproj
python -m pip install -r requirements.txt
python -m unittest -v
```

The Python suite checks ingestion, the legacy utility, and C#-to-DXF output
with the independent `ezdxf` reader. Windows UI interaction and AutoCAD/Civil
3D import have not been validated in this Linux workspace. See
[VALIDATION.md](VALIDATION.md) for exact evidence and limits.

## Build a glyph library

Font extraction is an offline authoring step. Use a font and license that
allow your intended use. The builder requires an explicit license note and
records the source file hash; that is provenance, not a legal determination.

```bash
python build_font_library.py \
  --font /path/to/YourFace.ttf \
  --face-id your-family-regular-v1 \
  --license "License name and notice reference" \
  --curve-tolerance 1 \
  --output font-library.json
```

By default, the builder requires all printable ASCII glyphs. The C# runtime
reads the versioned JSON repository; it does not parse fonts or require
Python. Read [FONT_LIBRARY.md](FONT_LIBRARY.md) for schema, scope, and
licensing guidance.

## Retained utilities

- `glyph_creator.py` and `glyphs.json` remain a standalone single-stroke
  artwork utility. Its open polylines are **not** font outlines and are not
  used by the desktop app.
- `font_outline_creator.py` remains a standalone outline-to-DXF CLI and
  supplies its curve-flattening pen to the offline repository builder.
- `extract_text_details.lsp` remains an independent AutoCAD diagnostic for
  reporting TEXT/MTEXT style and placement details.

The architecture and migration decisions are in [ARCHITECTURE.md](ARCHITECTURE.md);
the current implementation plan is [PROJECT_PLAN.md](PROJECT_PLAN.md).
