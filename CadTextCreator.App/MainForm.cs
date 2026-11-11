using CadTextCreator.Core;
using System.Drawing.Drawing2D;

namespace CadTextCreator.App;

public sealed class MainForm : Form
{
    private readonly TextBox _text = new() { Text = "Hello, 2026!" };
    private readonly ComboBox _facePicker = new() { DropDownStyle = ComboBoxStyle.DropDownList };
    private readonly NumericUpDown _height = NumberControl(20, 0.1m, 100000);
    private readonly NumericUpDown _widthFactor = NumberControl(1, 0.01m, 100);
    private readonly NumericUpDown _tracking = NumberControl(2, -10000, 10000);
    private readonly NumericUpDown _rotation = NumberControl(0, -3600, 3600);
    private readonly NumericUpDown _insertionX = NumberControl(0, -1000000000, 1000000000);
    private readonly NumericUpDown _insertionY = NumberControl(0, -1000000000, 1000000000);
    private readonly Panel _preview = new() { Dock = DockStyle.Fill, BackColor = Color.White };
    private readonly Label _status = new() { AutoSize = true, ForeColor = Color.DarkRed };
    private readonly GlyphRepository? _repository;
    private TextLayoutResult? _layout;

    public MainForm()
    {
        Text = "CAD Text Creator";
        Width = 1000;
        Height = 700;
        MinimumSize = new Size(720, 480);
        StartPosition = FormStartPosition.CenterScreen;

        try
        {
            var libraryPath = Path.Combine(AppContext.BaseDirectory, "font-library.json");
            _repository = GlyphRepository.Load(libraryPath);
            _facePicker.DataSource = _repository.Faces
                .OrderBy(face => face.Family, StringComparer.Ordinal)
                .ThenBy(face => face.Style, StringComparer.Ordinal)
                .Select(face => new FaceOption(face.Id, $"{face.Family} — {face.Style}"))
                .ToList();
            _facePicker.DisplayMember = nameof(FaceOption.DisplayName);
            _facePicker.ValueMember = nameof(FaceOption.Id);
        }
        catch (Exception error) when (error is IOException or InvalidDataException)
        {
            _status.Text = $"Could not load font library: {error.Message}";
        }

        BuildControls();
        _preview.Paint += DrawPreview;
        _preview.Resize += (_, _) => _preview.Invalidate();
        foreach (var control in new Control[]
        {
            _text, _facePicker, _height, _widthFactor, _tracking,
            _rotation, _insertionX, _insertionY
        })
        {
            control.TextChanged += (_, _) => RefreshLayout();
            if (control is NumericUpDown number)
            {
                number.ValueChanged += (_, _) => RefreshLayout();
            }
            if (control is ComboBox combo)
            {
                combo.SelectedValueChanged += (_, _) => RefreshLayout();
            }
        }

        RefreshLayout();
    }

    private void BuildControls()
    {
        var root = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 2,
            Padding = new Padding(12)
        };
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        Controls.Add(root);

        var settings = new TableLayoutPanel
        {
            Dock = DockStyle.Top,
            ColumnCount = 8,
            AutoSize = true,
            Margin = new Padding(0, 0, 0, 8)
        };
        settings.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        settings.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 30));
        settings.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        settings.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 20));
        settings.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        settings.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 20));
        settings.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        settings.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 30));
        root.Controls.Add(settings, 0, 0);

        AddSetting(settings, "Text", _text, 0, 0, 7);
        AddSetting(settings, "Font face", _facePicker, 0, 1, 7);
        AddSetting(settings, "Em height", _height, 0, 2);
        AddSetting(settings, "Width factor", _widthFactor, 2, 2);
        AddSetting(settings, "Tracking", _tracking, 4, 2);
        AddSetting(settings, "Rotation (deg)", _rotation, 6, 2);
        AddSetting(settings, "Origin X", _insertionX, 0, 3);
        AddSetting(settings, "Origin Y", _insertionY, 2, 3);

        var actionRow = new FlowLayoutPanel
        {
            AutoSize = true,
            Dock = DockStyle.Fill,
            WrapContents = false
        };
        var export = new Button { Text = "Export DXF...", AutoSize = true };
        export.Click += ExportDxf;
        actionRow.Controls.Add(export);
        actionRow.Controls.Add(_status);
        settings.Controls.Add(actionRow, 4, 3);
        settings.SetColumnSpan(actionRow, 4);

        root.Controls.Add(_preview, 0, 1);
        _preview.BorderStyle = BorderStyle.FixedSingle;
    }

    private static void AddSetting(
        TableLayoutPanel table,
        string label,
        Control control,
        int column,
        int row,
        int span = 1)
    {
        var labelControl = new Label
        {
            Text = label,
            AutoSize = true,
            Anchor = AnchorStyles.Left,
            Margin = new Padding(4, 8, 4, 4)
        };
        table.Controls.Add(labelControl, column, row);
        table.Controls.Add(control, column + 1, row);
        table.SetColumnSpan(control, span);
        control.Dock = DockStyle.Fill;
        control.Margin = new Padding(4);
    }

    private void RefreshLayout()
    {
        if (_repository is null || _facePicker.SelectedValue is not string faceId)
        {
            _layout = null;
            _preview.Invalidate();
            return;
        }

        try
        {
            _layout = TextComposer.Compose(
                _repository.GetFace(faceId),
                _text.Text,
                new TextLayoutOptions(
                    (double)_height.Value,
                    (double)_widthFactor.Value,
                    (double)_tracking.Value,
                    (double)_rotation.Value,
                    new Point2((double)_insertionX.Value, (double)_insertionY.Value)));
            _status.Text = $"{_layout.Contours.Count} contours";
            _status.ForeColor = Color.DarkGreen;
        }
        catch (Exception error) when (
            error is ArgumentException or KeyNotFoundException or InvalidDataException)
        {
            _layout = null;
            _status.Text = error.Message;
            _status.ForeColor = Color.DarkRed;
        }

        _preview.Invalidate();
    }

    private void DrawPreview(object? sender, PaintEventArgs args)
    {
        if (_layout is null || _layout.Contours.Count == 0)
        {
            return;
        }

        var allPoints = _layout.Contours.SelectMany(contour => contour.Points).ToList();
        var minX = allPoints.Min(point => point.X);
        var maxX = allPoints.Max(point => point.X);
        var minY = allPoints.Min(point => point.Y);
        var maxY = allPoints.Max(point => point.Y);
        var margin = 24f;
        var availableWidth = Math.Max(1, _preview.ClientSize.Width - margin * 2);
        var availableHeight = Math.Max(1, _preview.ClientSize.Height - margin * 2);
        var scaleX = availableWidth / (float)Math.Max(maxX - minX, 1e-9);
        var scaleY = availableHeight / (float)Math.Max(maxY - minY, 1e-9);
        var scale = Math.Min(scaleX, scaleY);
        var usedWidth = (float)(maxX - minX) * scale;
        var usedHeight = (float)(maxY - minY) * scale;
        var offsetX = margin + (availableWidth - usedWidth) / 2;
        var offsetY = margin + (availableHeight - usedHeight) / 2;
        PointF Project(Point2 point) => new(
            offsetX + (float)(point.X - minX) * scale,
            offsetY + (float)(maxY - point.Y) * scale);

        args.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        using var pen = new Pen(Color.DarkSlateBlue, 1.5f);
        foreach (var contour in _layout.Contours)
        {
            args.Graphics.DrawPolygon(pen, contour.Points.Select(Project).ToArray());
        }
    }

    private void ExportDxf(object? sender, EventArgs args)
    {
        if (_layout is null)
        {
            return;
        }

        using var dialog = new SaveFileDialog
        {
            AddExtension = true,
            DefaultExt = "dxf",
            Filter = "DXF files (*.dxf)|*.dxf",
            FileName = "text-outlines.dxf"
        };
        if (dialog.ShowDialog(this) != DialogResult.OK)
        {
            return;
        }

        try
        {
            DxfExporter.Export(_layout, dialog.FileName);
            _status.Text = $"Exported {dialog.FileName}";
            _status.ForeColor = Color.DarkGreen;
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException)
        {
            _status.Text = $"DXF export failed: {error.Message}";
            _status.ForeColor = Color.DarkRed;
        }
    }

    private static NumericUpDown NumberControl(decimal value, decimal minimum, decimal maximum) =>
        new()
        {
            DecimalPlaces = 3,
            Increment = 0.1m,
            Minimum = minimum,
            Maximum = maximum,
            Value = value,
            ThousandsSeparator = true
        };

    private sealed record FaceOption(string Id, string DisplayName);
}
