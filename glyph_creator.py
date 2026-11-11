#!/usr/bin/env python3
"""Generate single-stroke glyph geometry and export it as a DXF file."""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_GLYPHS = PROJECT_DIR / "glyphs.json"


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def load_glyphs(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as glyph_file:
            data = json.load(glyph_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not load glyph definitions from {path}: {error}") from error

    if not isinstance(data, dict) or not isinstance(data.get("glyphs"), dict):
        raise ValueError("Glyph JSON must contain a 'glyphs' object.")
    if not isinstance(data.get("aliases", {}), dict):
        raise ValueError("Glyph JSON 'aliases' must be an object.")
    return data


def resolve_glyph(character: str, data: dict[str, Any]) -> dict[str, Any]:
    glyphs = data["glyphs"]
    aliases = data.get("aliases", {})
    key = aliases.get(character, character)
    glyph = glyphs.get(key)
    if not isinstance(glyph, dict):
        raise ValueError(f"No glyph is defined for {character!r}.")

    advance = glyph.get("advance")
    strokes = glyph.get("strokes")
    if not _is_finite_number(advance) or advance <= 0:
        raise ValueError(f"Glyph {key!r} must have a positive numeric advance.")
    if not isinstance(strokes, list):
        raise ValueError(f"Glyph {key!r} must have a strokes array.")
    for stroke in strokes:
        if not isinstance(stroke, list) or len(stroke) < 2:
            raise ValueError(f"Every stroke in glyph {key!r} must have at least two points.")
        for point in stroke:
            if (
                not isinstance(point, list)
                or len(point) != 2
                or any(not _is_finite_number(value) for value in point)
            ):
                raise ValueError(f"Glyph {key!r} contains an invalid point.")
    return glyph


def layout_text(
    text: str,
    data: dict[str, Any],
    height: float,
    spacing: float,
) -> list[list[tuple[float, float]]]:
    if not _is_finite_number(height) or height <= 0:
        raise ValueError("Height must be greater than zero.")
    if not _is_finite_number(spacing) or spacing < 0:
        raise ValueError("Spacing cannot be negative.")

    scale = height / 7
    cursor_x = 0.0
    polylines: list[list[tuple[float, float]]] = []
    for character in text:
        if character in "\r\n":
            raise ValueError("Line breaks are not supported; provide a single line of text.")
        glyph = resolve_glyph(character, data)
        for stroke in glyph["strokes"]:
            polylines.append(
                [(cursor_x + point[0] * scale, point[1] * scale) for point in stroke]
            )
        cursor_x += glyph["advance"] * scale + spacing
    return polylines


def export_dxf(polylines: list[list[tuple[float, float]]], output: Path) -> None:
    try:
        import ezdxf
    except ImportError as error:
        raise RuntimeError(
            "DXF export requires ezdxf. Install project dependencies with "
            "'python -m pip install -r requirements.txt'."
        ) from error

    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    for polyline in polylines:
        modelspace.add_lwpolyline(polyline, close=False, dxfattribs={"layer": "GLYPHS"})
    document.saveas(output)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create polyline glyphs from text and export them to DXF."
    )
    parser.add_argument("text", nargs="?", help="Text to turn into glyph polylines.")
    parser.add_argument("-o", "--output", type=Path, default=Path("glyphs.dxf"))
    parser.add_argument(
        "--height", type=float, default=20.0, help="Glyph height in drawing units (default: 20)."
    )
    parser.add_argument(
        "--spacing", type=float, default=2.0, help="Gap between glyphs (default: 2)."
    )
    parser.add_argument(
        "--glyphs",
        type=Path,
        default=DEFAULT_GLYPHS,
        help=f"JSON glyph definitions (default: {DEFAULT_GLYPHS.name}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    text = args.text
    if text is None:
        if sys.stdin.isatty():
            text = input("Text to create: ")
        else:
            text = sys.stdin.read().rstrip("\r\n")

    try:
        glyph_data = load_glyphs(args.glyphs)
        polylines = layout_text(text, glyph_data, args.height, args.spacing)
        export_dxf(polylines, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(f"Created {args.output} with {len(polylines)} polylines.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
