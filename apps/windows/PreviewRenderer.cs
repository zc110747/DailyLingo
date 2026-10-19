using System.Drawing;
using System.Drawing.Imaging;
using System.IO;

namespace DailyLingo.Desktop;

/// <summary>
/// 不建窗口、直接把启动页渲染成 PNG 的调试入口
/// （<c>--render-preview &lt;目录&gt;</c>），用于在没有桌面会话的环境里核对版式。
/// </summary>
internal static class PreviewRenderer
{
    public static int Run(string directory)
    {
        ConsoleHost.Attach();
        Directory.CreateDirectory(directory);

        var sizes = new[] { new Size(1080, 820), new Size(460, 620) };
        using var view = new SplashView { Status = "正在连接 zc110747.github.io …" };

        foreach (var size in sizes)
        {
            using var bitmap = new Bitmap(size.Width, size.Height);
            using (var graphics = Graphics.FromImage(bitmap))
            {
                view.Render(graphics, size);
            }

            var path = Path.Combine(directory, $"splash-{size.Width}x{size.Height}.png");
            bitmap.Save(path, ImageFormat.Png);
            Console.WriteLine($"已渲染 {path}");
        }

        return 0;
    }
}
