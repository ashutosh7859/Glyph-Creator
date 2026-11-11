# CAD Text Creator project plan

## Current status

- **Architecture:** Migrated from a CAD-command-first proposal to a local
  WinForms UI, AutoCAD-independent C# runtime, and pre-generated glyph
  repository.
- **Completed in this increment:** repository audit; DejaVu Sans Book
  printable-ASCII library generation; JSON repository loading and validation;
  C# glyph lookup/composition; DXF export; initial WinForms UI; Python/C#
  tests; architecture, font-library, and validation documentation.
- **In progress:** Windows interactive UI validation and further geometry
  acceptance coverage.
- **Not run:** actual AutoCAD/Civil 3D import, REGION/SOLID conversion, and
  end-to-end host validation.
- **Last verified:** 2026-11-11.
- **Next action:** run the WinForms application on Windows, exercise supported
  text/layout/export flows, then import generated samples in a named
  AutoCAD/Civil 3D version.

`ARCHITECTURE.md` records the target architecture and migration decisions.
This file is the authoritative implementation status and checklist.

## Verified repository baseline

- The architecture is a UI-driven C# runtime that retrieves validated glyph
  geometry and exports DXF. AutoCAD command integration is not required.
- `glyph_creator.py` and `glyphs.json` contain 69 printable ASCII single-stroke
  definitions, lowercase aliases, and open `LWPOLYLINE` DXF output. Its six
  baseline tests passed. It is not filled font outline geometry.
- `font_outline_creator.py` already handled FontTools glyph outlines, curve
  flattening, simple layout, and closed DXF output, but had no glyph
  repository or dedicated tests.
- `PolylineSolids/SolidsFromPolylines.csproj` targets `net8.0-windows` and
  references Autodesk assemblies; it is a separate Civil 3D plugin, not a
  runtime foundation.
- `text_to_dxf` is a separate Python prototype and has its own uncommitted
  state. It was not changed or made a dependency.
- The available environment is Linux with .NET SDK 10 and no .NET 8 runtime.
  The WinForms app was compiled but cannot be run here.

## Migration decisions

| Action | Component/files | Rationale/status |
|---|---|---|
| Retain | `glyph_creator.py`, `glyphs.json`, `test_glyph_creator.py` | Preserve the useful, tested single-stroke DXF utility. Keep it separate from font outlines. |
| Refactor / adapt | `font_outline_creator.py`, `build_font_library.py` | Reuse the FontTools outline pen for offline ingestion. The builder records face/source identity, metrics, tolerance, contour nesting, and degenerate-contour counts. |
| Retain | `extract_text_details.lsp` | Independent AutoCAD text-style diagnostic; not a runtime dependency. |
| Add | `CadTextCreator.Core/` | .NET 8 AutoCAD-independent repository, Unicode-scalar lookup, geometry composition/validation, and ASCII DXF writer. |
| Add | `CadTextCreator.App/` | WinForms UI calling Core for preview and export. Build verified; interactive Windows run pending. |
| Add | `CadTextCreator.Tests/`, `test_font_library.py`, `test_csharp_pipeline.py` | Runtime harness and ingestion/DXF tests, with independent `ezdxf` parsing. |
| Add | `font-library.json` | Versioned JSON canonical runtime store; avoids a database dependency for the current 95-glyph sample. |
| Keep separate | `text_to_dxf/`, `PolylineSolids/` | Existing prototypes/plugins are not merged into this application and are not dependencies. |
| Deprecate as runtime input | Legacy `glyphs.json` | Its open strokes cannot be closed into correct font contours. The legacy command itself remains available. |

## Implemented behavior and limits

- The starter face is DejaVu Sans Book 2.37, 95 printable ASCII glyphs, 2048
  units-per-em, with source hash and license provenance. No source font binary
  is bundled. See `FONT-LICENSES.md`.
- The builder uses 1 font unit curve-flatness tolerance. Point/zero-area
  contours are ignored and counted; the source `u` glyph has one such
  non-rendering contour.
- The runtime uses schema-version-1 JSON, exact face ID, Unicode scalar
  mapping, stored advances, width factor, tracking, baseline insertion,
  rotation, containment depth, and outer/hole roles.
- Missing glyphs, invalid UTF-16, control characters, multiline input,
  malformed records, and unsupported schema versions fail explicitly.
- DXF is AC1021, `$INSUNITS=0`, one closed `LWPOLYLINE` per contour on
  `TEXT_OUTLINES`. Height and insertion coordinates use caller-selected
  drawing units.
- Layout is simple left-to-right; no shaping, kerning, bidirectional or
  complex-script layout, multiline text, or arbitrary installed-font support.

## Delivery phases

### Phase 0 — Audit and architecture baseline — complete

- [x] Inspect instructions, current plans, README/AGENTS, source, tests,
  dependencies, target frameworks, and nested Git state.
- [x] Map retained, adapted, separate, and deprecated runtime components.
- [x] Decide WinForms UI, C# runtime boundary, JSON repository, and offline
  font-ingestion boundary.
- [x] Record the migration in `ARCHITECTURE.md`.

**Evidence:** architecture decisions in `ARCHITECTURE.md`; implementation
status and validation evidence in this plan and `VALIDATION.md`.

### Phase 1 — Prove outline geometry — implementation complete

- [x] Select an available face and record its metadata, source hash, and
  license notice.
- [x] Generate printable ASCII outlines with composite resolution and
  1-font-unit curve tolerance.
- [x] Preserve counters and disconnected contours with containment depth and
  role metadata; exclude and count zero-area contours.
- [x] Validate stored polygons and export counter-heavy sample text to DXF.

**Evidence:** `test_font_library.py`, C# repository validation over all 95
glyph records, C# composition of `BO8 A`, and independent `ezdxf` parsing.
The host CAD interpretation and redistribution review are separate and
pending.

### Phase 2 — Glyph repository — complete for schema v1

- [x] Add JSON metadata, source identity/license, font units, metrics,
  codepoint mappings, contours, and schema version.
- [x] Load/validate the repository and resolve an exact face ID and glyph.

**Evidence:** C# pipeline integration test loads the bundled repository and
uses the `dejavu-sans-book` face. Additional faces are not included.

### Phase 3 — C# text composition — initial scope complete

- [x] Segment valid UTF-16 into Unicode scalars and reject controls/unsupported
  characters.
- [x] Apply stored advances, spaces, width factor, tracking, height, baseline
  origin, rotation, and translation; preserve contours and roles.
- [x] Test counter glyphs, explicit missing-glyph errors, and dimensions.

**Limit:** no shaping, kerning, bidirectional, complex-script, or
multiline support.

### Phase 4 — DXF export and parser validation — initial scope complete

- [x] Export contours as closed LWPOLYLINE entities with documented layer
  and unitless DXF units.
- [x] Reopen and inspect the generated sample with `ezdxf`; assert entity
  count, closure, layer, version, and expected bounds.

**Limit:** parser validation does not prove AutoCAD/Civil 3D import or solid
conversion.

### Phase 5 — UI integration — in progress

- [x] Add WinForms input, exact face selection, layout controls, preview, and
  DXF export wired to Core.
- [x] Cross-build the app on Linux with no warnings or errors.
- [ ] Run and exercise the app on Windows; verify startup, error display,
  preview, and export interactively.

### Phase 6 — CAD interoperability and library expansion — not started

- [ ] Import sample DXFs into a named AutoCAD/Civil 3D release.
- [ ] Verify region/solid behavior for counters and disconnected contours.
- [ ] Record host version, units, observed results, and limitations.
- [ ] Add further faces only after license review and the same ingestion and
  geometry-validation pipeline.

## Session evidence

Commands and results are recorded in `VALIDATION.md`. DXF geometry tests have
passed; WinForms runtime and actual CAD-host checks remain open.
