package com.dailylingo.app;

import org.json.JSONObject;

/**
 * 注入到网页里的桥接脚本：把 localStorage 与本机的进度文件双向对齐。
 *
 * <p>Android 的 WebView 没有「文档创建前执行脚本」的等价 API，所以脚本在
 * {@code onPageFinished} 之后注入。为了不出现「页面已经读了旧值、种子才写进去」的情况，
 * 脚本会把「是否刚刚写入过种子」作为返回值告诉宿主，宿主据此重载一次页面。</p>
 *
 * <p>页面侧通过 {@code window.DailyLingoNative.post(raw)} 把 localStorage 原文推给宿主。</p>
 */
final class ProgressBridge {

    private static final String SEED_PLACEHOLDER = "__DAILYLINGO_SEED__";

    private ProgressBridge() {
    }

    /** 生成注入脚本；{@code seedText} 为进度文件原文（null 表示不覆盖网页里的数据）。 */
    static String buildScript(String seedText) {
        // JSONObject.quote 生成的是合法的 JSON 字符串字面量，可直接当 JS 字面量用。
        String literal = seedText == null ? "null" : JSONObject.quote(seedText);
        return TEMPLATE.replace(SEED_PLACEHOLDER, literal);
    }

    private static final String TEMPLATE = """
            (function () {
              if (window.__dailylingoAndroidBridge) {
                return "ok";
              }
              window.__dailylingoAndroidBridge = true;

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
                  window.DailyLingoNative.post(raw === null ? "" : String(raw));
                } catch (error) {
                  /* 不是本应用的 WebView 时静默忽略 */
                }
              }

              // 1) 进度文件是权威副本：与网页里的旧数据不一致就覆盖。
              var seeded = false;
              if (typeof seed === "string" && seed.length > 0 && read() !== seed) {
                try {
                  window.localStorage.setItem(KEY, seed);
                  seeded = true;
                } catch (error) {
                  /* 存储被禁用时保持网页自身行为 */
                }
              }

              var last = read();

              function flush(force) {
                var raw = read();
                if (raw === null) {
                  /* 读不到存储（被禁用）时不要上报空状态，免得把本机进度清空 */
                  return;
                }
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

              // 3) 首屏同步一次，之后每 1.5 秒兜底比对（内容没变不发消息）。
              flush(true);
              document.addEventListener("DOMContentLoaded", function () { flush(true); });
              window.addEventListener("load", function () { flush(true); });
              setInterval(function () { flush(false); }, 1500);

              return seeded ? "seeded" : "ok";
            })();
            """;
}
