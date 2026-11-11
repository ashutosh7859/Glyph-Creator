using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace CadTextCreator.Core;

public sealed class GlyphRepository
{
    public const int SupportedSchemaVersion = 1;

    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        Converters = { new JsonStringEnumConverter(JsonNamingPolicy.CamelCase) }
    };

    private readonly Dictionary<string, FontFace> _faces;

    private GlyphRepository(GlyphLibrary library)
    {
        Library = library;
        _faces = library.Faces.ToDictionary(face => face.Id, StringComparer.Ordinal);
    }

    public GlyphLibrary Library { get; }
    public IReadOnlyCollection<FontFace> Faces => _faces.Values;

    public static GlyphRepository Load(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        GlyphLibrary library;
        try
        {
            using var stream = File.OpenRead(path);
            library = JsonSerializer.Deserialize<GlyphLibrary>(stream, JsonOptions)
                ?? throw new InvalidDataException("Glyph library JSON is empty.");
        }
        catch (JsonException error)
        {
            throw new InvalidDataException($"Glyph library JSON is invalid: {error.Message}", error);
        }

        Validate(library);
        return new GlyphRepository(library);
    }

    public FontFace GetFace(string faceId)
    {
        if (!_faces.TryGetValue(faceId, out var face))
        {
            throw new KeyNotFoundException($"Font face '{faceId}' is not in the glyph library.");
        }

        return face;
    }

    private static void Validate(GlyphLibrary library)
    {
        if (library.SchemaVersion != SupportedSchemaVersion)
        {
            throw new InvalidDataException(
                $"Unsupported glyph library schema version {library.SchemaVersion}; " +
                $"expected {SupportedSchemaVersion}.");
        }

        if (library.Faces is null || library.Faces.Count == 0)
        {
            throw new InvalidDataException("Glyph library must contain at least one font face.");
        }

        var faceIds = new HashSet<string>(StringComparer.Ordinal);
        foreach (var face in library.Faces)
        {
            if (face is null ||
                string.IsNullOrWhiteSpace(face.Id) || !faceIds.Add(face.Id))
            {
                throw new InvalidDataException("Font face IDs must be non-empty and unique.");
            }

            if (string.IsNullOrWhiteSpace(face.Family) ||
                string.IsNullOrWhiteSpace(face.Style) ||
                string.IsNullOrWhiteSpace(face.Version) ||
                string.IsNullOrWhiteSpace(face.SourceAssetName) ||
                string.IsNullOrWhiteSpace(face.SourceSha256) ||
                face.SourceSha256.Length != 64 ||
                !face.SourceSha256.All(Uri.IsHexDigit) ||
                string.IsNullOrWhiteSpace(face.License))
            {
                throw new InvalidDataException(
                    $"Font face '{face.Id}' is missing identity or source/license metadata.");
            }

            if (face.UnitsPerEm <= 0 ||
                !double.IsFinite(face.CurveToleranceFontUnits) ||
                face.CurveToleranceFontUnits <= 0 ||
                face.Glyphs is null)
            {
                throw new InvalidDataException($"Font face '{face.Id}' has invalid units or tolerance.");
            }

            var codePoints = new HashSet<int>();
            foreach (var glyph in face.Glyphs)
            {
                if (glyph is null ||
                    !Rune.IsValid(glyph.CodePoint) || !codePoints.Add(glyph.CodePoint))
                {
                    throw new InvalidDataException(
                        $"Font face '{face.Id}' has an invalid or duplicate Unicode code point.");
                }

                if (string.IsNullOrWhiteSpace(glyph.Name) ||
                    !double.IsFinite(glyph.AdvanceWidth) || glyph.AdvanceWidth < 0 ||
                    !double.IsFinite(glyph.LeftSideBearing) ||
                    glyph.IgnoredDegenerateContours < 0 ||
                    glyph.Contours is null)
                {
                    throw new InvalidDataException(
                        $"Glyph U+{glyph.CodePoint:X} in face '{face.Id}' has invalid metrics.");
                }

                foreach (var contour in glyph.Contours)
                {
                    if (contour is null)
                    {
                        throw new InvalidDataException(
                            $"Glyph U+{glyph.CodePoint:X} in face '{face.Id}' has a null contour.");
                    }
                    GeometryValidator.Validate(contour, $"U+{glyph.CodePoint:X}");
                }

                for (var index = 0; index < glyph.Contours.Count; index++)
                {
                    var contour = glyph.Contours[index];
                    var parentCount = glyph.Contours
                        .Where((_, otherIndex) => otherIndex != index)
                        .Count(parent => GeometryValidator.Contains(contour.Points[0], parent.Points));
                    if (parentCount != contour.Depth)
                    {
                        throw new InvalidDataException(
                            $"Contour nesting metadata is inconsistent in glyph U+{glyph.CodePoint:X}.");
                    }
                }
            }

            if (face.Glyphs.Count == 0)
            {
                throw new InvalidDataException($"Font face '{face.Id}' has no glyphs.");
            }

            face.BuildGlyphIndex();
        }
    }
}
