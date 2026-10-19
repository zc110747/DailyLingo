using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;

namespace DailyLingo.Desktop;

/// <summary>
/// 启动页：在 WebView 还没加载出内容（或正在连网）时显示，
/// 避免出现一片空白。中间是渐变艺术字 <c>Lingo</c>，下面有跳动的音量条与状态文字。
/// </summary>
internal sealed class SplashView : Control
{
    private const string Brand = "Lingo";
    private const string Tagline = "每天一篇小故事 · 听得见的英语";

    private static readonly Color PageBackground = Color.FromArgb(247, 249, 252);
    private static readonly Color Accent = Color.FromArgb(0x31, 0x66, 0xA4); // 与站点 theme-color 一致
    private static readonly Color AccentDeep = Color.FromArgb(0x1B, 0x45, 0x74);
    private static readonly Color AccentLight = Color.FromArgb(0x7C, 0xBE, 0xF0);
    private static readonly Color MutedColor = Color.FromArgb(0x5B, 0x66, 0x7A);

    private readonly System.Windows.Forms.Timer _timer;
    private string _status = "";
    private float _phase;

    public SplashView()
    {
        SetStyle(
            ControlStyles.AllPaintingInWmPaint |
            ControlStyles.OptimizedDoubleBuffer |
            ControlStyles.UserPaint |
            ControlStyles.ResizeRedraw,
            true);

        BackColor = PageBackground;
        Dock = DockStyle.Fill;

        _timer = new System.Windows.Forms.Timer { Interval = 90 };
        _timer.Tick += (_, _) =>
        {
            _phase += 0.12f;
            Invalidate();
        };
    }

    /// <summary>底部那行灰字（例如「正在连接 …」）。</summary>
    public string Status
    {
        get => _status;
        set
        {
            if (_status == value)
            {
                return;
            }

            _status = value;
            Invalidate();
        }
    }

    public void StartAnimation()
    {
        if (!_timer.Enabled)
        {
            _timer.Start();
        }
    }

    public void StopAnimation() => _timer.Stop();

    protected override void OnPaint(PaintEventArgs e)
    {
        e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        e.Graphics.TextRenderingHint = TextRenderingHint.AntiAliasGridFit;
        Render(e.Graphics, ClientSize);
    }

    /// <summary>按给定尺寸绘制整屏内容。抽出来是为了能不建窗口直接渲染成 PNG 做视觉校验。</summary>
    internal void Render(Graphics graphics, Size size)
    {
        graphics.SmoothingMode = SmoothingMode.AntiAlias;
        graphics.TextRenderingHint = TextRenderingHint.AntiAliasGridFit;
        using (var background = new SolidBrush(PageBackground))
        {
            graphics.FillRectangle(background, new Rectangle(Point.Empty, size));
        }

        var width = size.Width;
        var height = size.Height;
        var brandSize = Math.Clamp(height * 0.13f, 38f, 92f);
        using var brandFont = new Font("Segoe UI", brandSize, FontStyle.Bold, GraphicsUnit.Pixel);
        using var taglineFont = new Font("Microsoft YaHei UI", Math.Clamp(height * 0.021f, 9f, 14f), FontStyle.Regular);
        using var statusFont = new Font("Microsoft YaHei UI", Math.Clamp(height * 0.019f, 8.5f, 12.5f), FontStyle.Regular);

        const float letterSpacing = 6f;
        var widths = Brand
            .Select(glyph => graphics.MeasureString(
                glyph.ToString(), brandFont, PointF.Empty, StringFormat.GenericTypographic).Width)
            .ToArray();
        var brandWidth = widths.Sum() + letterSpacing * (Brand.Length - 1);
        var brandHeight = brandFont.GetHeight(graphics);
        var taglineHeight = taglineFont.GetHeight(graphics);
        var statusHeight = statusFont.GetHeight(graphics);

        const float barArea = 40f;
        var gapBrandTagline = brandSize * 0.16f;
        const float gapTaglineBars = 26f;
        const float gapBarsStatus = 24f;

        var totalHeight = brandHeight + gapBrandTagline + taglineHeight + gapTaglineBars + barArea +
                          gapBarsStatus + statusHeight;
        var top = Math.Max(0f, (height - totalHeight) / 2f - height * 0.04f);

        // 1) 品牌艺术字：逐字绘制以便加字距，纵向渐变 + 淡淡的投影。
        // 渐变矩形只覆盖字形本身（在字体的行高里偏上一点），否则大部分渐变被行高的留白吃掉，
        // 看起来会像纯色。
        var cursor = (width - brandWidth) / 2f;
        var brandRect = new RectangleF(
            cursor,
            top + brandSize * 0.12f,
            brandWidth,
            brandSize * 0.92f);
        using (var gradient = new LinearGradientBrush(brandRect, AccentDeep, AccentLight, LinearGradientMode.Vertical))
        using (var shadow = new SolidBrush(Color.FromArgb(26, Accent)))
        {
            for (var index = 0; index < Brand.Length; index++)
            {
                var glyph = Brand[index].ToString();
                graphics.DrawString(glyph, brandFont, shadow, cursor, top + brandSize * 0.05f, StringFormat.GenericTypographic);
                graphics.DrawString(glyph, brandFont, gradient, cursor, top, StringFormat.GenericTypographic);
                cursor += widths[index] + letterSpacing;
            }
        }

        // 2) 副标题
        var taglineY = top + brandHeight + gapBrandTagline;
        using (var muted = new SolidBrush(MutedColor))
        {
            var taglineSize = graphics.MeasureString(Tagline, taglineFont);
            graphics.DrawString(Tagline, taglineFont, muted, (width - taglineSize.Width) / 2f, taglineY);
        }

        // 3) 跳动的音量条（纯装饰，表示「正在加载」）
        var barsTop = taglineY + taglineHeight + gapTaglineBars;
        DrawBars(graphics, barsTop, barArea, width);

        // 4) 状态文字
        if (_status.Length > 0)
        {
            using var muted = new SolidBrush(MutedColor);
            var statusSize = graphics.MeasureString(_status, statusFont);
            graphics.DrawString(
                _status, statusFont, muted, (width - statusSize.Width) / 2f, barsTop + barArea + gapBarsStatus);
        }
    }

    private void DrawBars(Graphics graphics, float top, float area, float viewWidth)
    {
        const int count = 5;
        const float barWidth = 8f;
        const float gap = 9f;

        var barsWidth = count * barWidth + (count - 1) * gap;
        var left = (viewWidth - barsWidth) / 2f;
        var baseline = top + area;

        for (var index = 0; index < count; index++)
        {
            var wave = MathF.Sin(_phase + index * 0.9f);
            var barHeight = 10f + 20f * (0.5f + 0.5f * wave);
            var alpha = (int)Math.Clamp(110 + 110 * (0.5f + 0.5f * wave), 60f, 235f);
            using var brush = new SolidBrush(Color.FromArgb(alpha, index % 2 == 0 ? Accent : AccentLight));
            FillRoundedBar(graphics, brush, left + index * (barWidth + gap), baseline - barHeight, barWidth, barHeight);
        }
    }

    private static void FillRoundedBar(Graphics graphics, Brush brush, float x, float y, float width, float height)
    {
        if (height <= width)
        {
            graphics.FillEllipse(brush, x, y, width, height);
            return;
        }

        using var path = new GraphicsPath();
        path.AddArc(x, y, width, width, 180f, 180f);
        path.AddArc(x, y + height - width, width, width, 0f, 180f);
        path.CloseFigure();
        graphics.FillPath(brush, path);
    }
}
