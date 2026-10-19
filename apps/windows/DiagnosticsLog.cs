using System.IO;
using System.Text;

namespace DailyLingo.Desktop;

/// <summary>
/// 极简诊断日志：写在 <c>%TEMP%\dailylingo-desktop.log</c>，只记启动阶段与未处理异常。
/// 程序没有控制台，出问题时靠这份日志定位（超过 64 KB 时自动重开一份）。
/// </summary>
internal static class DiagnosticsLog
{
    private static readonly object Gate = new();
    private static readonly string LogPath = Path.Combine(Path.GetTempPath(), "dailylingo-desktop.log");
    private const long MaxBytes = 64 * 1024;

    public static string FilePath => LogPath;

    public static void Info(string message)
    {
        try
        {
            lock (Gate)
            {
                var file = new FileInfo(LogPath);
                if (file.Exists && file.Length > MaxBytes)
                {
                    File.Delete(LogPath);
                }

                File.AppendAllText(
                    LogPath,
                    $"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} {message}{Environment.NewLine}",
                    Encoding.UTF8);
            }
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            // 日志写不了就算了，绝不能因为日志把程序搞崩
        }
    }

    public static void Error(string message, Exception exception)
    {
        Info($"[ERROR] {message}{Environment.NewLine}{exception}");
    }
}
