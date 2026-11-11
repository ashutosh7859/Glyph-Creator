using System.Buffers;
using System.Text;

namespace CadTextCreator.Core;

public static class TextComposer
{
    public static TextLayoutResult Compose(
        FontFace face,
        string text,
        TextLayoutOptions options)
    {
        ArgumentNullException.ThrowIfNull(face);
        ArgumentNullException.ThrowIfNull(text);
        ValidateOptions(options);
        if (text.Length == 0)
        {
            throw new ArgumentException("Text cannot be empty.", nameof(text));
        }

        var runes = new List<Rune>();
        var remaining = text.AsSpan();
        while (!remaining.IsEmpty)
        {
            var status = Rune.DecodeFromUtf16(remaining, out var rune, out var consumed);
            if (status != OperationStatus.Done)
            {
                throw new ArgumentException("Text contains invalid UTF-16.", nameof(text));
            }

            if (Rune.IsControl(rune))
            {
                throw new ArgumentException(
                    "Line breaks and control characters are not supported.", nameof(text));
            }

            runes.Add(rune);
            remaining = remaining[consumed..];
        }

        var scale = options.Height / face.UnitsPerEm;
        var radians = options.RotationDegrees * Math.PI / 180;
        var cosine = Math.Cos(radians);
        var sine = Math.Sin(radians);
        var cursor = 0.0;
        var output = new List<ComposedContour>();

        for (var glyphIndex = 0; glyphIndex < runes.Count; glyphIndex++)
        {
            var rune = runes[glyphIndex];
            if (!face.TryGetGlyph(rune.Value, out var glyph))
            {
                throw new KeyNotFoundException(
                    $"Font face '{face.Id}' has no glyph for U+{rune.Value:X}.");
            }

            foreach (var contour in glyph.Contours)
            {
                var transformed = contour.Points.Select(point =>
                {
                    var localX = (cursor + point.X * options.WidthFactor) * scale;
                    var localY = point.Y * scale + options.BaselineOffset;
                    return new Point2(
                        options.Insertion.X + localX * cosine - localY * sine,
                        options.Insertion.Y + localX * sine + localY * cosine);
                }).ToList();
                var composed = new GlyphContour
                {
                    Closed = true,
                    Depth = contour.Depth,
                    Role = contour.Role,
                    Points = transformed
                };
                GeometryValidator.Validate(composed, $"U+{rune.Value:X} after layout");
                output.Add(new ComposedContour(
                    rune.Value, contour.Depth, contour.Role, transformed));
            }

            cursor += glyph.AdvanceWidth * options.WidthFactor;
            if (glyphIndex < runes.Count - 1)
            {
                cursor += options.Tracking / scale;
            }
        }

        return new TextLayoutResult(output, cursor * scale);
    }

    private static void ValidateOptions(TextLayoutOptions options)
    {
        if (!double.IsFinite(options.Height) || options.Height <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(options), "Height must be positive.");
        }

        if (!double.IsFinite(options.WidthFactor) || options.WidthFactor <= 0)
        {
            throw new ArgumentOutOfRangeException(
                nameof(options), "Width factor must be positive.");
        }

        if (!double.IsFinite(options.Tracking) ||
            !double.IsFinite(options.RotationDegrees) ||
            !double.IsFinite(options.BaselineOffset) ||
            !double.IsFinite(options.Insertion.X) ||
            !double.IsFinite(options.Insertion.Y))
        {
            throw new ArgumentOutOfRangeException(
                nameof(options), "Layout settings must be finite numbers.");
        }
    }
}
