#!/usr/bin/env python3
"""Build a versioned JSON glyph library from a licensed TrueType/OpenType font."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont, TTLibError

from font_outline_creator import OutlinePen


def _name(font: TTFont, name_id: int, fallback: str) -> str:
    for record in font["name"].names:
        if record.nameID == name_id:
            try:
                value = record.toUnicode().strip()
            except UnicodeDecodeError:
                continue
            if value:
                return value
    return fallback


def _signed_area(points: list[tuple[float, float]]) -> float:
    return sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    ) / 2


def _contains(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        if (first[1] > y) != (second[1] > y):
            crossing_x = (second[0] - first[0]) * (y - first[1]) / (
                second[1] - first[1]
            ) + first[0]
            if x < crossing_x:
                inside = not inside
    return inside


def _contour_records(
    contours: list[list[tuple[float, float]]],
) -> list[dict[str, Any]]:
    for contour in contours:
        if len(set(contour)) < 3 or not math.isfinite(_signed_area(contour)):
            raise ValueError("Font contains a degenerate outline contour.")
        if abs(_signed_area(contour)) <= 1e-9:
            raise ValueError("Font contains a zero-area outline contour.")

    records = []
    for index, contour in enumerate(contours):
        depth = sum(
            _contains(contour[0], parent)
            for other_index, parent in enumerate(contours)
            if other_index != index
        )
        records.append(
            {
                "depth": depth,
                "role": "hole" if depth % 2 else "outer",
                "closed": True,
                "points": [{"x": x, "y": y} for x, y in contour],
            }
        )
    return records


def build_font_library(
    font_path: Path,
    face_id: str,
    license_name: str,
    characters: str = "".join(chr(codepoint) for codepoint in range(32, 127)),
    curve_tolerance_font_units: float = 1.0,
) -> dict[str, Any]:
    if not face_id.strip():
        raise ValueError("Face ID cannot be empty.")
    if not license_name.strip():
        raise ValueError("Source font license must be recorded.")
    if not math.isfinite(curve_tolerance_font_units) or curve_tolerance_font_units <= 0:
        raise ValueError("Curve tolerance must be a positive finite number.")
    if len(set(characters)) != len(characters):
        raise ValueError("Character list must not contain duplicates.")

    try:
        font = TTFont(str(font_path), lazy=False)
    except (OSError, TTLibError) as error:
        raise ValueError(f"Could not open font file {font_path}: {error}") from error

    try:
        if "head" not in font or "hmtx" not in font or "name" not in font:
            raise ValueError("Font must contain head, hmtx, and name tables.")
        units_per_em = int(font["head"].unitsPerEm)
        if units_per_em <= 0:
            raise ValueError("Font has invalid units-per-em metrics.")
        cmap = font.getBestCmap()
        if not cmap:
            raise ValueError("Font has no usable Unicode character map.")
        glyph_set = font.getGlyphSet()
        glyphs = []
        seen_codepoints = set()

        for character in characters:
            codepoint = ord(character)
            if codepoint in seen_codepoints:
                continue
            seen_codepoints.add(codepoint)
            glyph_name = cmap.get(codepoint)
            if glyph_name is None or glyph_name not in glyph_set:
                raise ValueError(f"Font does not contain a glyph for {character!r}.")

            pen = OutlinePen(
                glyph_set,
                lambda point: point,
                curve_tolerance_font_units,
                ignore_degenerate_contours=True,
            )
            try:
                glyph_set[glyph_name].draw(pen)
            except (KeyError, TTLibError, ValueError) as error:
                raise ValueError(
                    f"Could not extract outline for {character!r}: {error}"
                ) from error
            if pen.current is not None:
                raise ValueError(f"Font glyph {character!r} ended with an open contour.")

            try:
                advance, side_bearing = font["hmtx"].metrics[glyph_name]
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"Font has no valid metrics for {character!r}."
                ) from error
            glyphs.append(
                {
                    "codePoint": codepoint,
                    "name": glyph_name,
                    "advanceWidth": float(advance),
                    "leftSideBearing": float(side_bearing),
                    "ignoredDegenerateContours": pen.ignored_degenerate_contours,
                    "contours": _contour_records(pen.contours),
                }
            )

        return {
            "schemaVersion": 1,
            "faces": [
                {
                    "id": face_id,
                    "family": _name(font, 1, font_path.stem),
                    "style": _name(font, 2, "Regular"),
                    "version": _name(font, 5, "unknown"),
                    "sourceAssetName": font_path.name,
                    "sourceSha256": hashlib.sha256(font_path.read_bytes()).hexdigest(),
                    "license": license_name.strip(),
                    "unitsPerEm": units_per_em,
                    "curveToleranceFontUnits": curve_tolerance_font_units,
                    "glyphs": glyphs,
                }
            ],
        }
    finally:
        font.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract font outlines and metrics into a JSON glyph library."
    )
    parser.add_argument("--font", required=True, type=Path, help="TTF or OTF font file.")
    parser.add_argument("--face-id", required=True, help="Stable exact face identifier.")
    parser.add_argument(
        "--license",
        required=True,
        dest="license_name",
        help="Source font license identifier or notice; verify it before distribution.",
    )
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument(
        "--characters",
        default="".join(chr(codepoint) for codepoint in range(32, 127)),
        help="Exact characters to extract (default: printable ASCII).",
    )
    parser.add_argument(
        "--curve-tolerance",
        type=float,
        default=1.0,
        help="Maximum curve flatness deviation in font units (default: 1).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        library = build_font_library(
            args.font,
            args.face_id,
            args.license_name,
            args.characters,
            args.curve_tolerance,
        )
        args.output.write_text(
            json.dumps(library, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, TTLibError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    glyph_count = len(library["faces"][0]["glyphs"])
    print(f"Created {args.output} with {glyph_count} glyphs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
