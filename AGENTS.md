# CAD Text Creator project instructions

## Start each session

1. Read `PROJECT_PLAN.md`, `README.md`, and `ARCHITECTURE.md`.
2. Verify the current source, tests, build state, and available version-control
   roots before relying on a prior handoff.
3. Resume at the earliest incomplete plan phase. Record actual test evidence
   and unrun checks; do not mark work complete from intent alone.

## Architecture constraints

- `CadTextCreator.Core` owns runtime repository access, exact glyph lookup,
  text composition, contour validation, and DXF export. It must not depend on
  AutoCAD APIs or the UI.
- `CadTextCreator.App` is the WinForms presentation layer and calls Core
  services; do not put font extraction, geometry algorithms, or DXF encoding
  in event handlers.
- `font-library.json` is the versioned canonical runtime repository.
  `build_font_library.py` is an offline authoring tool; normal runtime use
  must not require Python or a font file.
- Do not silently substitute font faces or skip missing glyphs. Do not treat
  the legacy `glyphs.json` open strokes as filled font outlines.
- Preserve contour closure, containment depth, and outer/hole roles. Keep
  text height, width, tracking, baseline, rotation, origin, and drawing units
  explicit.
- AutoCAD/Civil 3D is an optional DXF consumer. Do not add a CAD command,
  Autodesk dependency, service, or network requirement without a documented
  architecture decision.
- Check font rights before adding or distributing font assets or extracted
  geometry. Keep license and source-hash provenance with each face.

## Validation and documentation

- Run `python -m unittest -v` and build both the Core and WinForms projects
  after related changes.
- Keep current setup in `README.md`, technical decisions in
  `ARCHITECTURE.md`, glyph format/licensing details in `FONT_LIBRARY.md`,
  and verified/unrun checks in `VALIDATION.md`.
- Distinguish DXF-parser checks from actual Windows UI and CAD-host checks.
  This Linux environment cannot execute WinForms or AutoCAD/Civil 3D.
- Do not commit generated DXF previews, temporary output, local font files,
  `bin/`, or `obj/` outputs as source assets.
