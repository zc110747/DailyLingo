using System.IO;
using System.Runtime.InteropServices;

namespace DailyLingo.Desktop;

/// <summary>
/// 无界面自检：验证进度文件的解析 / 序列化 / 落盘与网页端契约一致。
/// 用法：<c>DailyLingo.Desktop.exe --self-test</c>（不弹窗，退出码 0 表示全过）。
/// </summary>
internal static class SelfTest
{
    public static int Run()
    {
        ConsoleHost.Attach();

        var results = new List<(bool Ok, string Name, string Detail)>();
        void Check(string name, bool ok, string detail = "") => results.Add((ok, name, detail));

        // ---- ID 规整 ----
        Check("NormalizeId 补零到四位", ProgressStore.NormalizeId("1") == "0001");
        Check("NormalizeId 去空白", ProgressStore.NormalizeId(" 7 ") == "0007");
        Check("NormalizeId 五位不截断", ProgressStore.NormalizeId("00002") == "00002");
        Check("NormalizeId 拒绝非数字", ProgressStore.NormalizeId("abc") == "");
        Check("NormalizeId 拒绝负数", ProgressStore.NormalizeId("-1") == "");
        Check("NormalizeId 拒绝空串", ProgressStore.NormalizeId("   ") == "");

        // ---- 排序去重 ----
        var deduped = ProgressStore.Dedupe(new[] { "0002", "0001", "0002", "0010" });
        Check("Dedupe 去重并升序", string.Join(",", deduped) == "0001,0002,0010",
            string.Join(",", deduped));

        // ---- 解析：拒绝非法输入 ----
        Check("TryParse 拒绝空文本", !ProgressStore.TryParse("  ", out _, out _));
        Check("TryParse 拒绝非 JSON", !ProgressStore.TryParse("not json", out _, out _));
        Check("TryParse 拒绝数组顶层",
            !ProgressStore.TryParse("[1,2,3]", out _, out _));
        Check("TryParse 拒绝缺 schemaVersion",
            !ProgressStore.TryParse("{\"completedArticles\":[]}", out _, out _));
        Check("TryParse 拒绝版本不符",
            !ProgressStore.TryParse("{\"schemaVersion\":2,\"completedArticles\":[]}", out _, out _));
        Check("TryParse 拒绝 completedArticles 非数组",
            !ProgressStore.TryParse("{\"schemaVersion\":1,\"completedArticles\":\"0001\"}", out _, out _));

        // ---- 解析：网页端导出文件的真实形状 ----
        const string webExport = """
            {
              "schemaVersion": 1,
              "completedArticles": [
                "0001",
                "0002"
              ],
              "updatedAt": "2026-10-19T00:00:00.000Z",
              "exportedAt": "2026-10-19T00:05:00.000Z"
            }
            """;
        var parsedOk = ProgressStore.TryParse(webExport, out var parsed, out _);
        Check("TryParse 接受网页导出文件", parsedOk);
        Check("TryParse 保留顺序与时间",
            parsedOk && string.Join(",", parsed.CompletedArticles) == "0001,0002" &&
            parsed.UpdatedAt == "2026-10-19T00:00:00.000Z" &&
            parsed.ExportedAt == "2026-10-19T00:05:00.000Z");

        var mixed = ProgressStore.TryParse(
            "{\"schemaVersion\":1,\"completedArticles\":[3,\"0002\",\"x\",null]}",
            out var mixedDocument,
            out _);
        Check("TryParse 兼容数字 ID、丢弃非法项",
            mixed && string.Join(",", mixedDocument.CompletedArticles) == "0002,0003");

        // ---- 序列化：与网页端 JSON.stringify(payload, null, 2) + "\n" 同构 ----
        var serialized = ProgressStore.Serialize(new ProgressDocument
        {
            CompletedArticles = new List<string> { "0002", "0001" },
            UpdatedAt = "2026-10-19T00:00:00.000Z",
        });
        Check("Serialize 结尾换行", serialized.EndsWith("\n", StringComparison.Ordinal));
        Check("Serialize 两空格缩进", serialized.Contains("\n  \"schemaVersion\": 1,", StringComparison.Ordinal));
        var versionIndex = serialized.IndexOf("\"schemaVersion\"", StringComparison.Ordinal);
        var listIndex = serialized.IndexOf("\"completedArticles\"", StringComparison.Ordinal);
        var updatedIndex = serialized.IndexOf("\"updatedAt\"", StringComparison.Ordinal);
        var exportedIndex = serialized.IndexOf("\"exportedAt\"", StringComparison.Ordinal);
        Check("Serialize 键顺序与网页端一致",
            versionIndex >= 0 && versionIndex < listIndex && listIndex < updatedIndex && updatedIndex < exportedIndex);

        // ---- 落盘 / 回读 ----
        var folder = Path.Combine(Path.GetTempPath(), "dailylingo-selftest-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(folder);
        var file = Path.Combine(folder, ProgressStore.FileName);

        try
        {
            var store = ProgressStore.ForFile(file);
            var webState = "{\"schemaVersion\":1,\"completedArticles\":[\"0003\",\"0001\"],\"updatedAt\":\"2026-10-19T01:00:00.000Z\"}";
            Check("ApplyWebState 首次写盘", store.ApplyWebState(webState));
            Check("ApplyWebState 无变化时不重写", !store.ApplyWebState(webState));
            Check("进度文件已生成", File.Exists(file));

            var reloaded = ProgressStore.ForFile(file).Load();
            Check("回读得到同样的 ID",
                reloaded is not null && string.Join(",", reloaded.CompletedArticles) == "0001,0003");
            Check("回读保留 updatedAt",
                reloaded is not null && reloaded.UpdatedAt == "2026-10-19T01:00:00.000Z");
            Check("回读后导出时间已补齐", reloaded?.ExportedAt is { Length: > 0 });

            // 空状态（网页清空进度）也要落盘成空数组
            Check("空进度也能落盘", store.ApplyWebState(null));
            var empty = ProgressStore.ForFile(file).Load();
            Check("空进度写为空数组", empty is not null && empty.CompletedArticles.Count == 0);

            // 损坏文件：留档 + 忽略
            File.WriteAllText(file, "{ 这不是 JSON");
            var broken = ProgressStore.ForFile(file).Load();
            var backups = Directory.GetFiles(folder, "*corrupt*.json");
            Check("损坏文件返回 null", broken is null);
            Check("损坏文件已留档", backups.Length == 1);
        }
        finally
        {
            TryCleanup(folder);
        }

        Console.WriteLine("DailyLingo Desktop 自检");
        foreach (var (ok, name, detail) in results)
        {
            Console.WriteLine($"  [{(ok ? "PASS" : "FAIL")}] {name}{(detail.Length > 0 ? " — " + detail : "")}");
        }

        var passed = results.Count(result => result.Ok);
        var failed = results.Count - passed;
        Console.WriteLine($"结果：PASS {passed} / FAIL {failed}");
        Console.WriteLine($"进度文件位置：{Path.Combine(AppContext.BaseDirectory, ProgressStore.FileName)}");
        WriteLog(results, passed, failed);
        return failed == 0 ? 0 : 1;
    }

    private static void TryCleanup(string folder)
    {
        try
        {
            Directory.Delete(folder, recursive: true);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            // 临时目录清不掉不影响自检结论
        }
    }

    private static void WriteLog(List<(bool Ok, string Name, string Detail)> results, int passed, int failed)
    {
        try
        {
            var path = Path.Combine(Path.GetTempPath(), "dailylingo-selftest.log");
            var lines = new List<string> { "DailyLingo Desktop 自检" };
            lines.AddRange(results.Select(result =>
                $"  [{(result.Ok ? "PASS" : "FAIL")}] {result.Name}" +
                (result.Detail.Length > 0 ? " — " + result.Detail : "")));
            lines.Add($"结果：PASS {passed} / FAIL {failed}");
            File.WriteAllLines(path, lines);
            Console.WriteLine($"日志：{path}");
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            // 日志写不了就直接看控制台
        }
    }
}

/// <summary>WinExe 进程默认没有控制台，自检时挂到父进程的控制台上才能看到输出。</summary>
internal static class ConsoleHost
{
    private const int AttachParentProcess = -1;

    public static void Attach()
    {
        if (!AttachConsole(AttachParentProcess))
        {
            AllocConsole();
        }

        Console.SetOut(new StreamWriter(Console.OpenStandardOutput()) { AutoFlush = true });
        Console.SetError(new StreamWriter(Console.OpenStandardError()) { AutoFlush = true });
    }

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool AttachConsole(int processId);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool AllocConsole();
}
