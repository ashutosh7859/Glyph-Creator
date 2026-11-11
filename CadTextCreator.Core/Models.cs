namespace CadTextCreator.Core;

public sealed class GlyphLibrary
{
    public int SchemaVersion { get; set; }
    public List<FontFace> Faces { get; set; } = [];
}

public sealed class FontFace
{
    public string Id { get; set; } = "";
    public string Family { get; set; } = "";
    public string Style { get; set; } = "";
    public string Version { get; set; } = "";
    public string SourceAssetName { get; set; } = "";
    public string SourceSha256 { get; set; } = "";
    public string License { get; set; } = "";
    public int UnitsPerEm { get; set; }
    public double CurveToleranceFontUnits { get; set; }
    public List<GlyphRecord> Glyphs { get; set; } = [];

    private Dictionary<int, GlyphRecord> _glyphIndex = [];

    public bool TryGetGlyph(int codePoint, out GlyphRecord glyph) =>
        _glyphIndex.TryGetValue(codePoint, out glyph!);

    internal void BuildGlyphIndex() =>
        _glyphIndex = Glyphs.ToDictionary(glyph => glyph.CodePoint);
}

public sealed class GlyphRecord
{
    public int CodePoint { get; set; }
    public string Name { get; set; } = "";
    public double AdvanceWidth { get; set; }
    public double LeftSideBearing { get; set; }
    public int IgnoredDegenerateContours { get; set; }
    public List<GlyphContour> Contours { get; set; } = [];
}

public sealed class GlyphContour
{
    public int Depth { get; set; }
    public ContourRole Role { get; set; }
    public bool Closed { get; set; }
    public List<Point2> Points { get; set; } = [];
}

public enum ContourRole
{
    Outer,
    Hole
}

public readonly record struct Point2(double X, double Y);

public sealed record TextLayoutOptions(
    double Height,
    double WidthFactor = 1,
    double Tracking = 0,
    double RotationDegrees = 0,
    Point2 Insertion = default,
    double BaselineOffset = 0);

public sealed record ComposedContour(
    int CodePoint,
    int Depth,
    ContourRole Role,
    IReadOnlyList<Point2> Points);

public sealed record TextLayoutResult(
    IReadOnlyList<ComposedContour> Contours,
    double AdvanceWidth);
