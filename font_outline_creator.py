#!/usr/bin/env python3
"""Convert text in a TrueType/OpenType font file to closed DXF contours."""

import argparse
import math
import sys
from pathlib import Path
from typing import Callable

from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont, TTLibError


Point = tuple[float, float]
Contour = list[Point]
MAX_CURVE_DEPTH = 18
MAX_CONTOUR_VERTICES = 20_000


def _is_finite(value: float) -> bool:
    return math.isfinite(value)


def _midpoint(first: Point, second: Point) -> Point:
    return ((first[0] + second[0]) / 2, (first[1] + second[1]) / 2)


def _point_segment_distance(point: Point, start: Point, end: Point) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    projection = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_squared
    projection = min(1.0, max(0.0, projection))
    closest = (start[0] + projection * dx, start[1] + projection * dy)
    return math.hypot(point[0] - closest[0], point[1] - closest[1])


def _cubic_is_flat(points: tuple[Point, Point, Point, Point], tolerance: float) -> bool:
    start, control1, control2, end = points
    return max(
        _point_segment_distance(control1, start, end),
        _point_segment_distance(control2, start, end),
    ) <= tolerance


def _flatten_cubic(
    points: tuple[Point, Point, Point, Point],
    tolerance: float,
    depth: int = 0,
) -> list[Point]:
    """Return cubic Bezier points after adaptive subdivision to a flatness bound."""
    if _cubic_is_flat(points, tolerance):
        return [points[-1]]
    if depth >= MAX_CURVE_DEPTH:
        raise ValueError(
            "Curve could not meet the requested tolerance before the subdivision limit."
        )

    start, control1, control2, end = points
    start_control = _midpoint(start, control1)
    control_midpoint = _midpoint(control1, control2)
    control_end = _midpoint(control2, end)
    left_midpoint = _midpoint(start_control, control_midpoint)
    right_midpoint = _midpoint(control_midpoint, control_end)
    middle = _midpoint(left_midpoint, right_midpoint)

    left = _flatten_cubic(
        (start, start_control, left_midpoint, middle), tolerance, depth + 1
    )
    right = _flatten_cubic(
        (middle, right_midpoint, control_end, end), tolerance, depth + 1
    )
    return left + right


class OutlinePen(BasePen):
    """Flatten font paths into closed contours in final drawing coordinates."""

    def __init__(
        self,
        glyph_set,
        transform: Callable[[Point], Point],
        tolerance: float,
        ignore_degenerate_contours: bool = False,
    ) -> None:
        super().__init__(glyph_set)
        self.transform = transform
        self.tolerance = tolerance
        self.ignore_degenerate_contours = ignore_degenerate_contours
        self.ignored_degenerate_contours = 0
        self.current: Contour | None = None
        self.contours: list[Contour] = []

    def _append(self, point: Point) -> None:
        if self.current is None:
            raise ValueError("Font outline contains a segment outside a contour.")
        transformed = self.transform((float(point[0]), float(point[1])))
        if not all(_is_finite(value) for value in transformed):
            raise ValueError("Font outline produced a non-finite coordinate.")
        if not self.current or transformed != self.current[-1]:
            self.current.append(transformed)
        if len(self.current) > MAX_CONTOUR_VERTICES:
            raise ValueError(
                f"Font contour exceeds the {MAX_CONTOUR_VERTICES} vertex limit."
            )

    def _moveTo(self, point: Point) -> None:
        if self.current is not None:
            raise ValueError("Font started a new contour before closing the previous one.")
        self.current = []
        self._append(point)

    def _lineTo(self, point: Point) -> None:
        self._append(point)

    def _curveToOne(self, control1: Point, control2: Point, end: Point) -> None:
        if self.current is None:
            raise ValueError("Font curve appears before the start of a contour.")
        start = self.current[-1]
        transformed = tuple(
            self.transform((float(point[0]), float(point[1])))
            for point in (control1, control2, end)
        )
        if not all(_is_finite(value) for point in transformed for value in point):
            raise ValueError("Font curve produced a non-finite coordinate.")
        flattened = _flatten_cubic(
            (start, transformed[0], transformed[1], transformed[2]), self.tolerance
        )
        for point in flattened:
            if not self.current or point != self.current[-1]:
                self.current.append(point)
            if len(self.current) > MAX_CONTOUR_VERTICES:
                raise ValueError(
                    f"Font contour exceeds the {MAX_CONTOUR_VERTICES} vertex limit."
                )

    def _qCurveToOne(self, control: Point, end: Point) -> None:
        if self.current is None:
            raise ValueError("Font curve appears before the start of a contour.")
        start = self.current[-1]
        control_point = self.transform((float(control[0]), float(control[1])))
        end_point = self.transform((float(end[0]), float(end[1])))
        # Convert the quadratic segment to an equivalent cubic segment.
        cubic_control1 = (
            start[0] + (2 / 3) * (control_point[0] - start[0]),
            start[1] + (2 / 3) * (control_point[1] - start[1]),
        )
        cubic_control2 = (
            end_point[0] + (2 / 3) * (control_point[0] - end_point[0]),
            end_point[1] + (2 / 3) * (control_point[1] - end_point[1]),
        )
        self._curveToOne(cubic_control1, cubic_control2, end_point)

    def _closePath(self) -> None:
        if self.current is None:
            return
        if len(self.current) > 1 and self.current[-1] == self.current[0]:
            self.current.pop()
        distinct = set(self.current)
        if len(distinct) < 3:
            if self.ignore_degenerate_contours:
                self.ignored_degenerate_contours += 1
                self.current = None
                return
            raise ValueError("Font contains a closed contour with fewer than three points.")
        self.contours.append(self.current)
        self.current = None

    def _endPath(self) -> None:
        if self.current:
            raise ValueError("Font contains an open contour; closed outlines are required.")
        self.current = None


def _font_cap_height(font: TTFont, glyph_set, cmap: dict[int, str]) -> float:
    """Use the font's Latin capital H top as the reference height."""
    glyph_name = cmap.get(ord("H"))
    if glyph_name is None or glyph_name not in glyph_set:
        raise ValueError("Font must contain a Unicode Latin capital H for height scaling.")
    bounds_pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(bounds_pen)
    if bounds_pen.bounds is None:
        raise ValueError("Font capital H has no outline bounds.")
    cap_height = float(bounds_pen.bounds[3])
    if not _is_finite(cap_height) or cap_height <= 0:
        raise ValueError("Font capital H must have a positive height above the baseline.")
    return cap_height


def layout_text(
    text: str,
    font_path: Path,
    height: float = 2.5,
    width_factor: float = 1.0,
    spacing: float = 0.0,
    curve_tolerance: float = 0.005,
    insertion: Point = (0.0, 0.0),
    rotation: float = 0.0,
) -> list[Contour]:
    """Lay out one line and return closed contours in drawing coordinates.

    ``height`` is the distance from the baseline to the top of the font's
    capital H. The insertion point is the text baseline origin. ``spacing``
    is additional distance after each character, in drawing units.
    """
    for name, value in (
        ("Height", height),
        ("Width factor", width_factor),
        ("Curve tolerance", curve_tolerance),
        ("Rotation", rotation),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not _is_finite(value):
            raise ValueError(f"{name} must be a finite number.")
    if height <= 0:
        raise ValueError("Height must be greater than zero.")
    if width_factor <= 0:
        raise ValueError("Width factor must be greater than zero.")
    if spacing < 0 or not _is_finite(spacing):
        raise ValueError("Spacing must be a finite, non-negative number.")
    if curve_tolerance <= 0:
        raise ValueError("Curve tolerance must be greater than zero.")
    if len(insertion) != 2 or any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not _is_finite(value)
        for value in insertion
    ):
        raise ValueError("Insertion point must contain two finite coordinates.")
    if not text:
        raise ValueError("Text cannot be empty.")
    if "\r" in text or "\n" in text:
        raise ValueError("Line breaks are not supported; provide a single line of text.")

    try:
        font = TTFont(str(font_path), lazy=False)
    except (OSError, TTLibError) as error:
        raise ValueError(f"Could not open font file {font_path}: {error}") from error

    try:
        if "head" not in font or "hmtx" not in font:
            raise ValueError("Font must contain head and hmtx tables.")
        units_per_em = float(font["head"].unitsPerEm)
        if not _is_finite(units_per_em) or units_per_em <= 0:
            raise ValueError("Font has invalid units-per-em metrics.")

        cmap = font.getBestCmap()
        if not cmap:
            raise ValueError("Font has no usable Unicode character map.")
        glyph_set = font.getGlyphSet()
        cap_height = _font_cap_height(font, glyph_set, cmap)
        scale = height / cap_height
        radians = math.radians(rotation)
        cosine = math.cos(radians)
        sine = math.sin(radians)
        cursor_x = 0.0
        contours: list[Contour] = []

        for character in text:
            glyph_name = cmap.get(ord(character))
            if glyph_name is None:
                raise ValueError(f"Font does not contain a glyph for {character!r}.")
            if glyph_name not in glyph_set:
                raise ValueError(f"Font glyph {glyph_name!r} is unavailable.")

            def transform(point: Point, advance_offset: float = cursor_x) -> Point:
                local_x = advance_offset + point[0] * scale * width_factor
                local_y = point[1] * scale
                return (
                    insertion[0] + local_x * cosine - local_y * sine,
                    insertion[1] + local_x * sine + local_y * cosine,
                )

            pen = OutlinePen(glyph_set, transform, curve_tolerance)
            try:
                glyph_set[glyph_name].draw(pen)
            except (KeyError, TTLibError, ValueError) as error:
                raise ValueError(f"Could not extract outline for {character!r}: {error}") from error
            if pen.current is not None:
                raise ValueError(f"Font glyph {character!r} ended with an open contour.")
            contours.extend(pen.contours)

            try:
                advance_width = float(font["hmtx"].metrics[glyph_name][0])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Font has no valid advance width for {character!r}.") from error
            if not _is_finite(advance_width) or advance_width < 0:
                raise ValueError(f"Font has an invalid advance width for {character!r}.")
            cursor_x += advance_width * scale * width_factor + spacing

        return contours
    finally:
        font.close()


def export_dxf(contours: list[Contour], output: Path) -> None:
    try:
        import ezdxf
    except ImportError as error:
        raise RuntimeError(
            "DXF export requires ezdxf. Install dependencies with "
            "'python -m pip install -r requirements.txt'."
        ) from error

    document = ezdxf.new("R2010")
    document.header["$INSUNITS"] = 0  # Coordinates use the caller's drawing units.
    modelspace = document.modelspace()
    for contour in contours:
        modelspace.add_lwpolyline(
            contour,
            close=True,
            dxfattribs={"layer": "TEXT_OUTLINES"},
        )
    document.saveas(output)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create closed polyline contours from a TrueType/OpenType font."
    )
    parser.add_argument("text", help="Single line of text to outline.")
    parser.add_argument("--font", required=True, type=Path, help="TTF or OTF font file.")
    parser.add_argument("-o", "--output", type=Path, default=Path("text_outlines.dxf"))
    parser.add_argument(
        "--height",
        type=float,
        default=2.5,
        help="Capital-H height in drawing units (default: 2.5).",
    )
    parser.add_argument(
        "--width-factor",
        type=float,
        default=1.0,
        help="Horizontal scale factor (default: 1.0).",
    )
    parser.add_argument(
        "--spacing",
        type=float,
        default=0.0,
        help="Extra gap between characters in drawing units (default: 0).",
    )
    parser.add_argument(
        "--curve-tolerance",
        type=float,
        default=0.005,
        help="Maximum curve flatness deviation in drawing units (default: 0.005).",
    )
    parser.add_argument(
        "--insertion",
        nargs=2,
        type=float,
        metavar=("X", "Y"),
        default=(0.0, 0.0),
        help="Baseline insertion point (default: 0 0).",
    )
    parser.add_argument(
        "--rotation",
        type=float,
        default=0.0,
        help="Text rotation in degrees (default: 0).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        contours = layout_text(
            args.text,
            args.font,
            height=args.height,
            width_factor=args.width_factor,
            spacing=args.spacing,
            curve_tolerance=args.curve_tolerance,
            insertion=tuple(args.insertion),
            rotation=args.rotation,
        )
        export_dxf(contours, args.output)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(f"Created {args.output} with {len(contours)} closed contours.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
