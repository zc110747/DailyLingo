using System.Text.Json;

namespace DailyLingo.Desktop;

/// <summary>一条来自网页的消息。<c>Payload</c> 是 localStorage 原文（可能为 null）。</summary>
internal readonly record struct BridgeMessage(string Type, string? Payload);

/// <summary>
/// 注入到网页里的桥接脚本：把 localStorage 与桌面端的进度文件双向对齐。
/// <list type="bullet">
/// <item>脚本在 <c>AddScriptToExecuteOnDocumentCreatedAsync</c> 里注入，早于页面自身的
/// <c>progress.js</c>，所以种子进度一定先落地，页面初始化时读到的就是文件里的数据。</item>
/// <item>用 <c>Storage.prototype.setItem</c> 钩子捕捉页面的每一次写入，外加 2 秒轮询兜底，
/// 网页端任何写法的改动都会推给宿主写盘。</item>
/// </list>
/// </summary>
internal static class ProgressBridge
{
    /// <summary>与网页端 <c>progress.js</c> 相同的存储键。</summary>
    public const string StorageKey = "dailylingo_learning_progress_v1";

    private const string SeedPlaceholder = "__DAILYLINGO_SEED__";

    /// <summary>生成注入脚本；<paramref name="seedJson"/> 为进度文件原文（null 表示不覆盖网页里的数据）。</summary>
    public static string BuildScript(string? seedJson)
    {
        // 用 JSON 序列化得到一个安全的 JS 字符串字面量（引号、反斜杠、非 ASCII 都会被转义）。
        var literal = seedJson is null ? "null" : JsonSerializer.Serialize(seedJson);
        return ScriptTemplate.Replace(SeedPlaceholder, literal, StringComparison.Ordinal);
    }

    /// <summary>解析网页 postMessage 过来的 JSON。</summary>
    public static BridgeMessage? ParseMessage(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return null;
        }

        try
        {
            using var document = JsonDocument.Parse(json);
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return null;
            }

            if (!root.TryGetProperty("type", out var type) || type.ValueKind != JsonValueKind.String)
            {
                return null;
            }

            string? payload = null;
            if (root.TryGetProperty("value", out var value))
            {
                payload = value.ValueKind switch
                {
                    JsonValueKind.String => value.GetString(),
                    JsonValueKind.Null or JsonValueKind.Undefined => null,
                    _ => value.GetRawText(),
                };
            }

            return new BridgeMessage(type.GetString() ?? "", payload);
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private const string ScriptTemplate = """
        (function () {
          if (window.__dailylingoDesktopBridge) {
            return;
          }
          window.__dailylingoDesktopBridge = true;

          var KEY = "dailylingo_learning_progress_v1";
          var seed = __DAILYLINGO_SEED__;

          function read() {
            try {
              return window.localStorage.getItem(KEY);
            } catch (error) {
              return null;
            }
          }

          function post(raw) {
            try {
              window.chrome.webview.postMessage(JSON.stringify({ type: "progress", value: raw }));
            } catch (error) {
              /* 不是 WebView2 宿主（例如被普通浏览器打开）时静默忽略 */
            }
          }

          // 1) 用同目录的进度文件覆盖网页里的旧数据：桌面端的文件是权威副本。
          if (typeof seed === "string" && seed.length > 0) {
            try {
              if (read() !== seed) {
                window.localStorage.setItem(KEY, seed);
              }
            } catch (error) {
              /* 存储被禁用时保持网页自身行为 */
            }
          }

          var last = read();

          function flush(force) {
            var raw = read();
            if (!force && raw === last) {
              return;
            }
            last = raw;
            post(raw);
          }

          // 2) 钩住每一次写入：网页端 progress.js 全部走 localStorage.setItem。
          try {
            var proto = window.Storage && window.Storage.prototype;
            if (proto) {
              var nativeSetItem = proto.setItem;
              proto.setItem = function (key, value) {
                var result = nativeSetItem.apply(this, arguments);
                if (String(key) === KEY) {
                  setTimeout(function () { flush(true); }, 0);
                }
                return result;
              };

              var nativeRemoveItem = proto.removeItem;
              proto.removeItem = function (key) {
                var result = nativeRemoveItem.apply(this, arguments);
                if (String(key) === KEY) {
                  setTimeout(function () { flush(true); }, 0);
                }
                return result;
              };
            }
          } catch (error) {
            /* 钩不上也不影响轮询兜底 */
          }

          // 3) 首屏、加载完成各同步一次，之后每 2 秒兜底比对一次（内容没变不发消息）。
          document.addEventListener("DOMContentLoaded", function () { flush(true); });
          window.addEventListener("load", function () { flush(true); });
          setInterval(function () { flush(false); }, 2000);
        })();
        """;
}
