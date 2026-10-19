using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace DailyLingo.Desktop;

/// <summary>
/// 一份学习进度文档。字段名、顺序、缩进都对齐网页端「导出进度」的 JSON
/// （<c>JSON.stringify(payload, null, 2) + "\n"</c>），两份文件可以直接互换。
/// </summary>
internal sealed class ProgressDocument
{
    [JsonPropertyName("schemaVersion")]
    public int SchemaVersion { get; set; } = ProgressStore.SchemaVersion;

    [JsonPropertyName("completedArticles")]
    public List<string> CompletedArticles { get; set; } = new();

    [JsonPropertyName("updatedAt")]
    public string UpdatedAt { get; set; } = "";

    [JsonPropertyName("exportedAt")]
    public string? ExportedAt { get; set; }
}

/// <summary>
/// 进度文件的读写。文件固定放在程序同目录（<see cref="FileName"/>），
/// 结构与网页端的导出文件完全一致，因此可以把它交给网页端的「导入进度」直接使用。
/// </summary>
internal sealed class ProgressStore
{
    /// <summary>进度 schema 版本，必须与网页端 <c>progress.js</c> 的 <c>SCHEMA_VERSION</c> 一致。</summary>
    public const int SchemaVersion = 1;

    /// <summary>进度文件名（与程序同目录）。</summary>
    public const string FileName = "dailylingo-progress.json";

    private const string TimestampFormat = "yyyy-MM-dd'T'HH:mm:ss.fff'Z'";

    private static readonly Regex IdPattern = new("^[0-9]+$", RegexOptions.CultureInvariant);

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    private static readonly UTF8Encoding Utf8NoBom = new(encoderShouldEmitUTF8Identifier: false);

    private readonly Action<string>? _log;

    /// <summary>上次落盘内容的指纹，用来跳过无变化的写盘。</summary>
    private string? _lastSignature;

    private ProgressStore(string filePath, Action<string>? log)
    {
        FilePath = filePath;
        _log = log;
    }

    /// <summary>进度文件路径（绝对路径）。</summary>
    public string FilePath { get; }

    /// <summary>当前内存中的进度；<see cref="Load"/> 之前为 null。</summary>
    public ProgressDocument? Current { get; private set; }

    /// <summary>已完成文章数。</summary>
    public int CompletedCount => Current?.CompletedArticles.Count ?? 0;

    /// <summary>程序同目录下的进度文件。</summary>
    public static ProgressStore ForApplicationDirectory(Action<string>? log = null) =>
        new(Path.Combine(AppContext.BaseDirectory, FileName), log);

    /// <summary>指定路径（自检用）。</summary>
    public static ProgressStore ForFile(string filePath, Action<string>? log = null) =>
        new(Path.GetFullPath(filePath), log);

    /// <summary>把任意输入规整成四位补零的文章 ID；非法输入返回空串。</summary>
    public static string NormalizeId(string? raw)
    {
        if (raw is null)
        {
            return "";
        }

        var text = raw.Trim();
        if (text.Length == 0 || !IdPattern.IsMatch(text))
        {
            return "";
        }

        return text.Length < 4 ? text.PadLeft(4, '0') : text;
    }

    /// <summary>去重后按字典序排序，与网页端 <c>uniqueSorted()</c> 一致。</summary>
    public static List<string> Dedupe(IEnumerable<string> ids)
    {
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var result = new List<string>();
        foreach (var id in ids)
        {
            if (seen.Add(id))
            {
                result.Add(id);
            }
        }

        result.Sort(StringComparer.Ordinal);
        return result;
    }

    /// <summary>当前 UTC 时间，格式与 JS 的 <c>toISOString()</c> 一致。</summary>
    public static string Timestamp() =>
        DateTime.UtcNow.ToString(TimestampFormat, CultureInfo.InvariantCulture);

    /// <summary>
    /// 解析一段进度 JSON（同网页端 <c>parseProgressPayload()</c>：要求对象、<c>schemaVersion</c> 匹配、
    /// <c>completedArticles</c> 是数组，非法 ID 逐条丢弃）。
    /// </summary>
    public static bool TryParse(string? text, out ProgressDocument document, out string error)
    {
        document = new ProgressDocument();
        error = "";

        if (string.IsNullOrWhiteSpace(text))
        {
            error = "内容是空的。";
            return false;
        }

        JsonDocument json;
        try
        {
            json = JsonDocument.Parse(text);
        }
        catch (JsonException)
        {
            error = "不是合法的 JSON 文本。";
            return false;
        }

        using (json)
        {
            var root = json.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                error = "文件结构不正确：顶层应当是 JSON 对象。";
                return false;
            }

            if (!root.TryGetProperty("schemaVersion", out var version))
            {
                error = "缺少 schemaVersion，无法确认文件格式。";
                return false;
            }

            if (version.ValueKind != JsonValueKind.Number || !version.TryGetInt32(out var versionValue))
            {
                error = "schemaVersion 必须是整数。";
                return false;
            }

            if (versionValue != SchemaVersion)
            {
                error = $"不支持的版本：schemaVersion={versionValue}（本程序只支持 {SchemaVersion}）。";
                return false;
            }

            if (!root.TryGetProperty("completedArticles", out var list) || list.ValueKind != JsonValueKind.Array)
            {
                error = "completedArticles 必须是数组。";
                return false;
            }

            var ids = new List<string>();
            var invalid = 0;
            foreach (var item in list.EnumerateArray())
            {
                var id = item.ValueKind switch
                {
                    JsonValueKind.String => NormalizeId(item.GetString()),
                    JsonValueKind.Number when item.TryGetInt64(out var number) && number >= 0 =>
                        NormalizeId(number.ToString(CultureInfo.InvariantCulture)),
                    _ => "",
                };

                if (id.Length == 0)
                {
                    invalid++;
                }
                else
                {
                    ids.Add(id);
                }
            }

            var updatedAt = root.TryGetProperty("updatedAt", out var updated) &&
                            updated.ValueKind == JsonValueKind.String
                ? updated.GetString() ?? ""
                : "";

            var exportedAt = root.TryGetProperty("exportedAt", out var exported) &&
                             exported.ValueKind == JsonValueKind.String
                ? exported.GetString()
                : null;

            document = new ProgressDocument
            {
                SchemaVersion = SchemaVersion,
                CompletedArticles = Dedupe(ids),
                UpdatedAt = updatedAt,
                ExportedAt = exportedAt,
            };

            if (invalid > 0)
            {
                error = $"已忽略 {invalid} 条非法的文章 ID。";
            }

            return true;
        }
    }

    /// <summary>序列化成与网页端导出文件逐字节同构的文本（2 空格缩进 + 结尾换行）。</summary>
    public static string Serialize(ProgressDocument document)
    {
        var payload = new ProgressDocument
        {
            SchemaVersion = SchemaVersion,
            CompletedArticles = Dedupe(document.CompletedArticles),
            UpdatedAt = string.IsNullOrWhiteSpace(document.UpdatedAt) ? Timestamp() : document.UpdatedAt,
            ExportedAt = document.ExportedAt ?? Timestamp(),
        };

        return JsonSerializer.Serialize(payload, JsonOptions) + "\n";
    }

    /// <summary>读取同目录的进度文件；不存在或损坏时返回 null（损坏文件会先留档）。</summary>
    public ProgressDocument? Load()
    {
        if (!File.Exists(FilePath))
        {
            Current = null;
            return null;
        }

        string text;
        try
        {
            text = File.ReadAllText(FilePath, Encoding.UTF8);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            _log?.Invoke($"读取进度文件失败：{ex.Message}");
            Current = null;
            return null;
        }

        if (!TryParse(text, out var document, out var error))
        {
            _log?.Invoke($"进度文件无法解析（{error}），已备份后忽略。");
            BackupBrokenFile();
            Current = null;
            return null;
        }

        if (error.Length > 0)
        {
            _log?.Invoke($"进度文件：{error}");
        }

        Current = document;
        _lastSignature = Signature(document);
        return document;
    }

    /// <summary>注入网页 localStorage 用的种子文本；没有可用文件时返回 null。</summary>
    public string? LoadSeedText()
    {
        var document = Load();
        return document is null ? null : Serialize(document);
    }

    /// <summary>
    /// 接收网页推送的 localStorage 原文并落盘。返回是否真的写了文件
    /// （内容没有变化时不写，避免每 2 秒轮询都触发一次磁盘写入）。
    /// </summary>
    public bool ApplyWebState(string? rawJson)
    {
        ProgressDocument document;
        if (string.IsNullOrWhiteSpace(rawJson))
        {
            document = new ProgressDocument { SchemaVersion = SchemaVersion, UpdatedAt = "" };
        }
        else if (!TryParse(rawJson, out document, out var error))
        {
            _log?.Invoke($"网页进度无法解析，已忽略：{error}");
            return false;
        }

        Current = document;

        var signature = Signature(document);
        if (signature == _lastSignature)
        {
            return false;
        }

        _lastSignature = signature;
        return Write(document);
    }

    /// <summary>把文档写入进度文件（先写临时文件再替换，避免半截文件）。</summary>
    public bool Write(ProgressDocument document)
    {
        document.ExportedAt = Timestamp();
        var text = Serialize(document);

        try
        {
            var directory = Path.GetDirectoryName(FilePath);
            if (!string.IsNullOrEmpty(directory))
            {
                Directory.CreateDirectory(directory);
            }

            var temporary = FilePath + ".tmp";
            File.WriteAllText(temporary, text, Utf8NoBom);
            File.Move(temporary, FilePath, overwrite: true);
            _lastSignature = Signature(document);
            Current = document;
            return true;
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            _log?.Invoke($"写入进度文件失败：{ex.Message}");
            return false;
        }
    }

    private static string Signature(ProgressDocument document) =>
        document.UpdatedAt + "|" + string.Join(",", Dedupe(document.CompletedArticles));

    private void BackupBrokenFile()
    {
        try
        {
            var suffix = DateTime.Now.ToString("yyyyMMddHHmmss", CultureInfo.InvariantCulture);
            var backup = Path.Combine(
                Path.GetDirectoryName(FilePath) ?? ".",
                $"{Path.GetFileNameWithoutExtension(FilePath)}.corrupt-{suffix}.json");

            File.Copy(FilePath, backup, overwrite: true);
            File.Delete(FilePath);
            _log?.Invoke($"损坏的进度文件已备份为 {Path.GetFileName(backup)}。");
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            _log?.Invoke($"备份损坏的进度文件失败：{ex.Message}");
        }
    }
}
