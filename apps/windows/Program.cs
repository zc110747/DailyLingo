using System.Windows.Forms;

namespace DailyLingo.Desktop;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        // 无界面自检：验证进度文件契约（不建窗口，供命令行 / CI 使用）。
        if (HasSwitch(args, "--self-test", "/self-test"))
        {
            return SelfTest.Run();
        }

        // 无窗口渲染启动页，便于在没有桌面会话时核对版式。
        if (HasSwitch(args, "--render-preview", "/render-preview"))
        {
            return PreviewRenderer.Run(GetOptionValue(args, "--render-preview", "/render-preview") ?? ".");
        }

        // 调试：加载完成后把 WebView 画面存成 PNG 再退出（用来核对线上页面在壳里的实际渲染）。
        var capturePath = GetOptionValue(args, "--capture", "/capture");
        if (capturePath is not null)
        {
            MainForm.CapturePath = capturePath;
        }

        Application.SetHighDpiMode(HighDpiMode.PerMonitorV2);
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
        Application.ThreadException += (_, args) => DiagnosticsLog.Error("UI 线程未处理异常", args.Exception);
        AppDomain.CurrentDomain.UnhandledException += (_, args) =>
            DiagnosticsLog.Error("未处理异常", args.ExceptionObject as Exception ?? new InvalidOperationException("未知异常"));

        try
        {
            Application.Run(new MainForm());
            return 0;
        }
        catch (Exception ex)
        {
            DiagnosticsLog.Error("主循环异常退出", ex);
            return 1;
        }
    }

    private static bool HasSwitch(string[] args, params string[] names) =>
        args.Any(arg => names.Any(name => arg.Equals(name, StringComparison.OrdinalIgnoreCase)));

    /// <summary>取 <c>--render-preview</c> 后面那个值；没有就返回 null。</summary>
    private static string? GetOptionValue(string[] args, params string[] names)
    {
        for (var index = 0; index < args.Length; index++)
        {
            if (!names.Any(name => args[index].Equals(name, StringComparison.OrdinalIgnoreCase)))
            {
                continue;
            }

            var next = index + 1;
            if (next < args.Length && !args[next].StartsWith("--", StringComparison.Ordinal))
            {
                return args[next];
            }
        }

        return null;
    }
}
