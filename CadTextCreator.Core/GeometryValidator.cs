namespace CadTextCreator.Core;

public static class GeometryValidator
{
    public static void Validate(GlyphContour contour, string context)
    {
        if (contour.Points is null)
        {
            throw new InvalidDataException($"Contour in {context} has no vertex list.");
        }

        if (!contour.Closed)
        {
            throw new InvalidDataException($"Contour in {context} is not closed.");
        }

        if (contour.Depth < 0 ||
            contour.Role != (contour.Depth % 2 == 0 ? ContourRole.Outer : ContourRole.Hole))
        {
            throw new InvalidDataException($"Contour nesting role is invalid in {context}.");
        }

        if (contour.Points.Count < 3)
        {
            throw new InvalidDataException($"Contour in {context} has fewer than three vertices.");
        }

        for (var index = 0; index < contour.Points.Count; index++)
        {
            var point = contour.Points[index];
            var next = contour.Points[(index + 1) % contour.Points.Count];
            if (!double.IsFinite(point.X) || !double.IsFinite(point.Y))
            {
                throw new InvalidDataException($"Contour in {context} has a non-finite vertex.");
            }

            if (point == next)
            {
                throw new InvalidDataException($"Contour in {context} has a zero-length edge.");
            }
        }

        var area = SignedArea(contour.Points);
        if (!double.IsFinite(area) || Math.Abs(area) <= 1e-9)
        {
            throw new InvalidDataException($"Contour in {context} has zero area.");
        }

        for (var first = 0; first < contour.Points.Count; first++)
        {
            var firstNext = (first + 1) % contour.Points.Count;
            for (var second = first + 1; second < contour.Points.Count; second++)
            {
                var secondNext = (second + 1) % contour.Points.Count;
                if (first == second || firstNext == second || secondNext == first)
                {
                    continue;
                }

                if (SegmentsIntersect(
                    contour.Points[first], contour.Points[firstNext],
                    contour.Points[second], contour.Points[secondNext]))
                {
                    throw new InvalidDataException($"Contour in {context} self-intersects.");
                }
            }
        }
    }

    public static bool Contains(Point2 point, IReadOnlyList<Point2> polygon)
    {
        var inside = false;
        for (var index = 0; index < polygon.Count; index++)
        {
            var first = polygon[index];
            var second = polygon[(index + 1) % polygon.Count];
            if ((first.Y > point.Y) != (second.Y > point.Y))
            {
                var crossingX = (second.X - first.X) * (point.Y - first.Y)
                    / (second.Y - first.Y) + first.X;
                if (point.X < crossingX)
                {
                    inside = !inside;
                }
            }
        }

        return inside;
    }

    private static double SignedArea(IReadOnlyList<Point2> points)
    {
        var area = 0.0;
        for (var index = 0; index < points.Count; index++)
        {
            var first = points[index];
            var second = points[(index + 1) % points.Count];
            area += first.X * second.Y - second.X * first.Y;
        }

        return area / 2;
    }

    private static bool SegmentsIntersect(Point2 a, Point2 b, Point2 c, Point2 d)
    {
        var abC = Orientation(a, b, c);
        var abD = Orientation(a, b, d);
        var cdA = Orientation(c, d, a);
        var cdB = Orientation(c, d, b);
        if (abC != 0 && abD != 0 && abC != abD &&
            cdA != 0 && cdB != 0 && cdA != cdB)
        {
            return true;
        }

        return abC == 0 && OnSegment(a, c, b) ||
            abD == 0 && OnSegment(a, d, b) ||
            cdA == 0 && OnSegment(c, a, d) ||
            cdB == 0 && OnSegment(c, b, d);
    }

    private static int Orientation(Point2 a, Point2 b, Point2 c)
    {
        var cross = (b.X - a.X) * (c.Y - a.Y) - (b.Y - a.Y) * (c.X - a.X);
        return cross > 0 ? 1 : cross < 0 ? -1 : 0;
    }

    private static bool OnSegment(Point2 start, Point2 point, Point2 end) =>
        point.X >= Math.Min(start.X, end.X) && point.X <= Math.Max(start.X, end.X) &&
        point.Y >= Math.Min(start.Y, end.Y) && point.Y <= Math.Max(start.Y, end.Y);
}
