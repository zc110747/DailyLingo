/* ==========================================================================
   DailyLingo — 文章页「自动完成」标记
   条件：**音频听到结尾附近** 且 **全部题目答对**，两者同时满足即自动把本篇
        标记为已完成（写入 dailylingo_learning_progress_v1，与首页同一份数据）。

   它只管「什么时候该打勾」，不碰存储细节：
     * 收听进度 ← audio-player.js 抛的 `dailylingo:listen`（ratio 0–1）
     * 判分结果 ← main.js 抛的 `dailylingo:quiz`（total / correct / allCorrect）
     * 落库       ← progress.js 的 markCompleted()（幂等，只增不减）

   设计取舍：
     * **只自动打勾，不自动取消**。答完后又改错一题，已经获得的完成记录保留 ——
       完成是「做到过」的事实，撤销权留给用户（首页手动取消）。
       否则一次误改答案就把记录抹掉，比不自动更烦人。
     * 阈值 0.9：要求真的听到尾巴（最后一个 timeupdate 与结尾的差值已由播放器补齐）。
       播放器的累计会丢弃「跳转产生的巨大增量」，所以拖进度条到结尾刷不出完成。
     * 没有音频或没有题目 ⇒ 自动标记不可能成立，构建期就已写死文案，
       这里直接不接管（`data-study-auto="false"`），避免给出永远不成立的进度提示。
   ========================================================================== */

(function () {
  "use strict";

  var LISTEN_EVENT = "dailylingo:listen";
  var QUIZ_EVENT = "dailylingo:quiz";
  var REQUIRED_RATIO = 0.9;

  /** 纯判定：听够了没有 + 是不是全对。抽出来便于在 Node 里直接测边界。 */
  function shouldComplete(listenRatio, quiz) {
    if (!quiz || !quiz.total || !quiz.allCorrect) {
      return false;
    }
    return typeof listenRatio === "number" && listenRatio >= REQUIRED_RATIO - 1e-6;
  }

  function init() {
    var body = document.body;
    var status = document.querySelector("[data-study-status]");
    var articleId = body ? body.getAttribute("data-article-id") : "";
    var api = typeof globalThis !== "undefined" ? globalThis.DailyLingoProgress : null;
    if (!articleId || !status || !api) {
      return;
    }

    var autoable = status.getAttribute("data-study-auto") === "true";
    var ratio = 0;
    var quiz = null;
    var done = false;
    var saveFailed = false;

    function paint() {
      status.classList.remove("is-done", "is-error");
      if (done) {
        status.textContent = "✅ 本篇已标记为完成（可在首页取消勾选）。";
        status.classList.add("is-done");
        return;
      }
      if (saveFailed) {
        status.textContent = "⚠️ 收听与答题条件都已满足，但本地存储不可用，完成标记没能保存。";
        status.classList.add("is-error");
        return;
      }
      if (!autoable || !quiz || !quiz.total) {
        return; // 保持构建期文案（无音频 / 无题目 / 还没开始答题）
      }
      status.textContent =
        "听力 " +
        Math.round(ratio * 100) +
        "% · 答对 " +
        quiz.correct +
        "/" +
        quiz.total +
        "（听完并全部答对后自动标记）";
    }

    function evaluate() {
      if (done || !autoable || !shouldComplete(ratio, quiz)) {
        paint();
        return;
      }
      var result = api.markCompleted(articleId);
      if (result && result.ok) {
        done = true;
        saveFailed = false;
      } else {
        saveFailed = true;
      }
      paint();
    }

    done = !!api.isCompleted(articleId);
    paint();

    if (!autoable) {
      return;
    }

    document.addEventListener(QUIZ_EVENT, function (event) {
      var detail = event.detail;
      quiz = detail && typeof detail.total === "number" ? detail : null;
      evaluate();
    });

    document.addEventListener(LISTEN_EVENT, function (event) {
      var detail = event.detail;
      if (detail && typeof detail.ratio === "number" && detail.ratio > ratio) {
        ratio = Math.min(1, detail.ratio);
      }
      evaluate();
    });
  }

  /* 供自动化测试使用的纯逻辑 */
  if (typeof globalThis !== "undefined") {
    globalThis.DailyLingoCompletion = {
      LISTEN_EVENT: LISTEN_EVENT,
      QUIZ_EVENT: QUIZ_EVENT,
      REQUIRED_RATIO: REQUIRED_RATIO,
      shouldComplete: shouldComplete,
    };
  }

  if (typeof document === "undefined") {
    return; // 非浏览器环境（测试）不绑定事件
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
