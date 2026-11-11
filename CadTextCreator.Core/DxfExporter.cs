using System.Globalization;
using System.Text;

namespace CadTextCreator.Core;

public static class DxfExporter
{
    public static void Export(TextLayoutResult layout, string path)
    {
        ArgumentNullException.ThrowIfNull(layout);
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        foreach (var contour in layout.Contours)
        {
            GeometryValidator.Validate(
                new GlyphContour
                {
                    Closed = true,
                    Depth = contour.Depth,
                    Role = contour.Role,
                    Points = contour.Points.ToList()
                },
                $"U+{contour.CodePoint:X} output");
        }

        var dxf = new StringBuilder();
        Pair(dxf, 0, "SECTION");
        Pair(dxf, 2, "HEADER");
        Pair(dxf, 9, "$ACADVER");
        Pair(dxf, 1, "AC1021");
        Pair(dxf, 9, "$INSUNITS");
        Pair(dxf, 70, "0");
        Pair(dxf, 0, "ENDSEC");
        Pair(dxf, 0, "SECTION");
        Pair(dxf, 2, "TABLES");
        Pair(dxf, 0, "TABLE");
        Pair(dxf, 2, "LTYPE");
        Pair(dxf, 70, "1");
        Pair(dxf, 0, "LTYPE");
        Pair(dxf, 100, "AcDbSymbolTableRecord");
        Pair(dxf, 100, "AcDbLinetypeTableRecord");
        Pair(dxf, 2, "CONTINUOUS");
        Pair(dxf, 70, "0");
        Pair(dxf, 3, "Solid line");
        Pair(dxf, 72, "65");
        Pair(dxf, 73, "0");
        Pair(dxf, 40, "0");
        Pair(dxf, 0, "ENDTAB");
        Pair(dxf, 0, "TABLE");
        Pair(dxf, 2, "LAYER");
        Pair(dxf, 70, "2");
        Pair(dxf, 0, "LAYER");
        Pair(dxf, 100, "AcDbSymbolTableRecord");
        Pair(dxf, 100, "AcDbLayerTableRecord");
        Pair(dxf, 2, "0");
        Pair(dxf, 70, "0");
        Pair(dxf, 62, "7");
        Pair(dxf, 6, "CONTINUOUS");
        Pair(dxf, 0, "LAYER");
        Pair(dxf, 100, "AcDbSymbolTableRecord");
        Pair(dxf, 100, "AcDbLayerTableRecord");
        Pair(dxf, 2, "TEXT_OUTLINES");
        Pair(dxf, 70, "0");
        Pair(dxf, 62, "7");
        Pair(dxf, 6, "CONTINUOUS");
        Pair(dxf, 0, "ENDTAB");
        Pair(dxf, 0, "ENDSEC");
        Pair(dxf, 0, "SECTION");
        Pair(dxf, 2, "ENTITIES");

        foreach (var contour in layout.Contours)
        {
            Pair(dxf, 0, "LWPOLYLINE");
            Pair(dxf, 100, "AcDbEntity");
            Pair(dxf, 8, "TEXT_OUTLINES");
            Pair(dxf, 100, "AcDbPolyline");
            Pair(dxf, 90, contour.Points.Count.ToString(CultureInfo.InvariantCulture));
            Pair(dxf, 70, "1");
            foreach (var point in contour.Points)
            {
                Pair(dxf, 10, point.X.ToString("G17", CultureInfo.InvariantCulture));
                Pair(dxf, 20, point.Y.ToString("G17", CultureInfo.InvariantCulture));
            }
        }

        Pair(dxf, 0, "ENDSEC");
        Pair(dxf, 0, "EOF");
        File.WriteAllText(path, dxf.ToString(), new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
    }

    private static void Pair(StringBuilder output, int groupCode, string value) =>
        output.Append(groupCode.ToString(CultureInfo.InvariantCulture))
            .Append('\n')
            .Append(value)
            .Append('\n');
}
