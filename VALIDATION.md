# Validation record

Last checked: 2026-11-11.

## Verified in this workspace

- `python -m unittest -v` passed 10 tests. This covered the existing
  single-stroke CLI regressions, counter contours and metrics for DejaVu Sans,
  explicit missing-glyph and license/tolerance failures, and the C#-to-DXF
  independent-reader integration check.
- `font-library.json` was built with:

  ```bash
  python build_font_library.py \
    --font /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
    --face-id dejavu-sans-book \
    --license "Bitstream Vera / DejaVu; see FONT-LICENSES.md" \
    --curve-tolerance 1 \
    --output font-library.json
  ```

  Result: 95 printable ASCII glyph records, 2048 units-per-em. The generated
  metadata records the source SHA-256 and one degenerate zero-area contour
  excluded from `u`; no TTF was copied into the project.
- `dotnet build CadTextCreator.Core/CadTextCreator.Core.csproj --no-restore`
  passed with 0 warnings and 0 errors.
- `dotnet build CadTextCreator.App/CadTextCreator.App.csproj --no-restore`
  passed with 0 warnings and 0 errors. This is a compile check only; WinForms
  was not launched on Linux.
- The C# runtime harness composed `BO8 A`, checked contour roles, metrics,
  spacing, translation/rotation, explicit missing-glyph and multiline errors,
  then exported `/tmp/cad-text-test.dxf`. Because this Linux image has .NET
  9/10 runtimes but not .NET 8, execution used `DOTNET_ROLL_FORWARD=Major`.
- A second library build to `/tmp/font-library-repro.json` compared byte-for-
  byte equal with the checked-in `font-library.json`.
- Independent `ezdxf` parsing of that file reported AC1021 with 10 closed
  `LWPOLYLINE` entities, all on `TEXT_OUTLINES`. Bounds were approximately
  `(98.596407, -49.364958, 182.659763, -15.565815)`.
- Baseline `dotnet build SolidsFromPolylines.csproj --no-restore` succeeded
  before migration work; this separate plugin is not part of the new app.

## Not validated

- The WinForms app has not been run interactively on Windows.
- No DXF has been imported into AutoCAD or Civil 3D. REGION/SOLID conversion,
  units in a real drawing, and target-host compatibility remain unverified.
- Font redistribution is not a general project guarantee. The included
  DejaVu-derived geometry has a recorded notice, but downstream redistribution
  should be reviewed against the source font license.
- The sample subset does not establish support for arbitrary fonts, scripts,
  shaping, kerning, or complex Unicode text.

## Repeatable checks

```bash
python -m unittest -v
dotnet build CadTextCreator.Core/CadTextCreator.Core.csproj
dotnet build CadTextCreator.App/CadTextCreator.App.csproj
```

The Python suite includes a C#-to-DXF integration test when `dotnet` and
`ezdxf` are available.
