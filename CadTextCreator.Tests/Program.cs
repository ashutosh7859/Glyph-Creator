using CadTextCreator.Core;

if (args.Length != 3)
{
    Console.Error.WriteLine(
        "Usage: CadTextCreator.Tests <glyph-library.json> <face-id> <output.dxf>");
    return 2;
}

var repository = GlyphRepository.Load(args[0]);
var face = repository.GetFace(args[1]);
var options = new TextLayoutOptions(
    Height: 20,
    WidthFactor: 1.25,
    Tracking: 2,
    RotationDegrees: 15,
    Insertion: new Point2(100, -50));

var layout = TextComposer.Compose(face, "BO8 A", options);
Check(layout.Contours.Count == 10, "All contours and counters must be retained.");
Check(layout.Contours.All(contour => contour.Points.Count >= 3), "Contours must have vertices.");
Check(layout.Contours.Any(contour => contour.Role == ContourRole.Hole), "Counters must be retained.");
Check(layout.Contours.Count(contour => contour.Role == ContourRole.Hole) == 6,
    "Outer/counter roles must match the source glyph topology.");
Check(layout.Contours.Any(contour => contour.Points.Any(point => point.X > 100)),
    "Insertion and rotation must affect output coordinates.");
var expectedAdvance = "BO8 A".Sum(character =>
    face.Glyphs.Single(glyph => glyph.CodePoint == character).AdvanceWidth * 1.25 * 20 / face.UnitsPerEm)
    + 4 * 2;
Check(Math.Abs(layout.AdvanceWidth - expectedAdvance) < 1e-9,
    "Glyph advances and tracking must produce predictable text width.");

var unitLayout = TextComposer.Compose(
    face, "A A", new TextLayoutOptions(Height: 20, Tracking: 2));
var spaceLayout = TextComposer.Compose(
    face, "AA", new TextLayoutOptions(Height: 20, Tracking: 2));
Check(unitLayout.AdvanceWidth > spaceLayout.AdvanceWidth,
    "Spaces must advance using glyph metrics.");

Expect<KeyNotFoundException>(
    () => TextComposer.Compose(face, "\U0001F9EA", new TextLayoutOptions(20)),
    "Missing glyphs must fail explicitly.");
Expect<ArgumentException>(
    () => TextComposer.Compose(face, "A\nB", new TextLayoutOptions(20)),
    "Multi-line text must fail explicitly.");

DxfExporter.Export(layout, args[2]);
Console.WriteLine(
    $"PASS: repository, Unicode lookup, spacing, layout, validation, and DXF export " +
    $"({layout.Contours.Count} contours).");
return 0;

static void Check(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}

static void Expect<TException>(Action action, string message) where TException : Exception
{
    try
    {
        action();
    }
    catch (TException)
    {
        return;
    }

    throw new InvalidOperationException(message);
}
