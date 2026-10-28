/* ==========================================================================
   DailyLingo — 页面交互
   职责：阅读理解练习的判分（单选 + 填空）、答案反馈、可访问性状态维护，
        以及跨页面共用的本地设置（页面语音跟随 / 播完循环播放）。

   正确答案来自页面内嵌的 <script type="application/json" id="quiz-data">，
   与构建脚本生成的数据同源，因此自动判分与 Answers 区域显示的答案必然一致。

   判分规则集中在 judge() / normalizeAnswer() 中，并在无 DOM 环境（Node）下
   通过 globalThis.DailyLingo 暴露，以便自动化测试直接验证边界条件。
   ========================================================================== */

(function () {
  "use strict";

  /* 判分结果变更时抛给上层（study-completion.js）：
     文章页需要知道「是不是所有题目都答对了」，但只有这里知道判分结果。
     事件挂在 document 上，detail 就是当前快照，订阅方不必反查 DOM。 */
  var QUIZ_EVENT = "dailylingo:quiz";

  /* 与 scripts/build.py 的 normalize_answer() 保持一致：
     去首尾空白 → 压缩内部空白 → 去尾部标点 → 忽略大小写 */
  function normalizeAnswer(text) {
    return String(text == null ? "" : text)
      .normalize("NFKC")
      .trim()
      .replace(/\s+/g, " ")
      .replace(/[.!?。！？,，;；:：]+$/, "")
      .trim()
      .toLowerCase();
  }

  /**
   * 判定单个题目。
   * @returns {{status: "empty"|"correct"|"wrong", answer: string}}
   */
  function judge(entry, rawValue) {
    var empty = { status: "empty", answer: entry ? String(entry.answer || "") : "" };
    if (!entry) {
      return empty;
    }

    if (entry.type === "choice") {
      var chosen = String(rawValue == null ? "" : rawValue).trim().toUpperCase();
      if (!chosen) {
        return empty;
      }
      var correctKey = String(entry.answer || "").trim().toUpperCase();
      return { status: chosen === correctKey ? "correct" : "wrong", answer: correctKey };
    }

    var value = normalizeAnswer(rawValue);
    if (!value) {
      return empty; // 空白答案永远不判为正确
    }
    var list = (entry.acceptable && entry.acceptable.length ? entry.acceptable : [entry.answer])
      .map(normalizeAnswer)
      .filter(Boolean);
    return {
      status: list.indexOf(value) !== -1 ? "correct" : "wrong",
      answer: String(entry.answer || list.join(" / ")),
    };
  }

  function readQuizData() {
    var node = document.getElementById("quiz-data");
    if (!node) {
      return {};
    }
    try {
      return JSON.parse(node.textContent || "{}");
    } catch (err) {
      return {};
    }
  }

  /**
   * 当前答题快照。只数 DOM 上的 `is-correct` / `is-wrong` 标记 ——
   * 这两个 class 是判分唯一的事实来源，改动答案时会被 clearMarks() 清掉，
   * 因此「改完答案还没重新检查」不会被误判成答对。
   */
  function quizSnapshot() {
    var questions = Array.prototype.slice.call(document.querySelectorAll(".question"));
    var correct = 0;
    var answered = 0;
    questions.forEach(function (question) {
      if (question.classList.contains("is-correct")) {
        correct++;
        answered++;
      } else if (question.classList.contains("is-wrong")) {
        answered++;
      }
    });
    return {
      total: questions.length,
      correct: correct,
      answered: answered,
      allCorrect: questions.length > 0 && correct === questions.length,
    };
  }

  function reportQuiz() {
    if (typeof CustomEvent !== "function" || !document.dispatchEvent) {
      return;
    }
    document.dispatchEvent(new CustomEvent(QUIZ_EVENT, { detail: quizSnapshot() }));
  }

  function setFeedback(node, text, kind) {
    node.textContent = text;
    node.classList.remove("is-correct", "is-wrong", "is-hint");
    if (kind) {
      node.classList.add(kind);
    }
  }

  function clearMarks(question) {
    question.classList.remove("is-correct", "is-wrong");
    question.querySelectorAll(".option").forEach(function (opt) {
      opt.classList.remove("is-correct", "is-wrong", "is-selected");
    });
    var input = question.querySelector(".fill-input");
    if (input) {
      input.removeAttribute("aria-invalid");
    }
  }

  function markOptions(question, correctKey) {
    question.querySelectorAll(".option").forEach(function (opt) {
      var radio = opt.querySelector('input[type="radio"]');
      if (!radio) {
        return;
      }
      if (radio.checked) {
        opt.classList.add("is-selected");
      }
      if (radio.value === correctKey) {
        opt.classList.add("is-correct");
      } else if (radio.checked) {
        opt.classList.add("is-wrong");
      }
    });
  }

  function markSelection(question) {
    question.querySelectorAll(".option").forEach(function (opt) {
      var own = opt.querySelector('input[type="radio"]');
      opt.classList.toggle("is-selected", !!(own && own.checked));
    });
  }

  function bindQuestion(question, entry) {
    var feedback = question.querySelector(".feedback");
    if (!feedback) {
      return;
    }

    function check() {
      clearMarks(question);

      var raw;
      if (entry.type === "choice") {
        var chosen = question.querySelector('input[type="radio"]:checked');
        raw = chosen ? chosen.value : "";
      } else {
        var input = question.querySelector(".fill-input");
        raw = input ? input.value : "";
      }

      var result = judge(entry, raw);

      if (result.status === "empty") {
        setFeedback(
          feedback,
          entry.type === "choice"
            ? "请先选择一个答案。"
            : "请输入答案后再检查（空白答案不计为正确）。",
          "is-hint"
        );
        var fill = question.querySelector(".fill-input");
        if (fill && entry.type !== "choice") {
          fill.setAttribute("aria-invalid", "true");
        }
        reportQuiz();
        return;
      }

      var right = result.status === "correct";
      question.classList.add(right ? "is-correct" : "is-wrong");

      if (entry.type === "choice") {
        markOptions(question, String(entry.answer || "").toUpperCase());
        setFeedback(
          feedback,
          right ? "✅ 回答正确。" : "❌ 回答不正确。正确答案是 " + result.answer + "。",
          right ? "is-correct" : "is-wrong"
        );
      } else {
        if (!right) {
          var box = question.querySelector(".fill-input");
          if (box) {
            box.setAttribute("aria-invalid", "true");
          }
        }
        setFeedback(
          feedback,
          right ? "✅ 回答正确。" : "❌ 回答不正确。参考答案：" + result.answer,
          right ? "is-correct" : "is-wrong"
        );
      }

      reportQuiz();
    }

    function reset() {
      clearMarks(question);
      question.querySelectorAll('input[type="radio"]').forEach(function (radio) {
        radio.checked = false;
      });
      var input = question.querySelector(".fill-input");
      if (input) {
        input.value = "";
        input.focus();
      }
      setFeedback(feedback, "", null);
      reportQuiz();
    }

    var checkBtn = question.querySelector('[data-action="check"]');
    var resetBtn = question.querySelector('[data-action="reset"]');
    if (checkBtn) {
      checkBtn.addEventListener("click", check);
    }
    if (resetBtn) {
      resetBtn.addEventListener("click", reset);
    }

    var fill = question.querySelector(".fill-input");
    if (fill) {
      fill.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
          check();
        }
      });
    }

    question.querySelectorAll('input[type="radio"]').forEach(function (radio) {
      radio.addEventListener("change", function () {
        clearMarks(question);
        markSelection(question);
        setFeedback(feedback, "", null);
        reportQuiz(); // 改了选项 ⇒ 先前的「答对」作废，快照要跟着退回去
      });
    });
  }

  function init() {
    var data = readQuizData();
    document.querySelectorAll(".question").forEach(function (question) {
      var entry = data[question.getAttribute("data-qid")];
      if (entry) {
        bindQuestion(question, entry);
      }
    });
    reportQuiz(); // 给上层一个初始快照（题目总数 / 全部未答）
  }

  /* ---------------------------------------------------------------- 本地设置
     两个朗读相关开关，都是单独一个 localStorage 键，
     不混进学习进度的四键导出契约（那是跨端镜像的格式）。
     写入在首页设置面板（progress.js），读取在文章页（audio-player.js），
     两边都通过 globalThis.DailyLingo.* 走这一份实现。

     「页面语音跟随」：播放到哪句，正文要不要自动滚到那一句。
     默认**关闭** —— 很多人的用法是边听边做题，播放器每换一句就把页面滚一次，
     等于每隔几秒把人拽回正文，题目就做不成了。开启后才跟随。

     「播完循环播放」：音频播到结尾要不要回到开头重播。
     默认**开启** —— 单篇 40~70 秒，听完就静音几乎一定要手动再点一次播放；
     想精听某一段时才关掉。 */
  var READING_FOLLOW_KEY = "dailylingo_reading_follow_v1";
  var AUDIO_LOOP_KEY = "dailylingo_audio_loop_v1";

  function settingStorage() {
    if (typeof window === "undefined") {
      return null;
    }
    try {
      return window.localStorage || null;
    } catch (error) {
      return null; // 隐私模式下连取用 localStorage 本身都可能抛错
    }
  }

  function readingFollowEnabled() {
    var store = settingStorage();
    if (!store) {
      return false; // 存储不可用 ⇒ 用默认值（不跟随）
    }
    try {
      return store.getItem(READING_FOLLOW_KEY) === "1";
    } catch (error) {
      return false;
    }
  }

  function setReadingFollow(enabled) {
    var store = settingStorage();
    if (!store) {
      return false;
    }
    try {
      store.setItem(READING_FOLLOW_KEY, enabled ? "1" : "0");
      return true;
    } catch (error) {
      return false;
    }
  }

  /* 与 readingFollow 唯一的区别是**默认值反过来**：
     存储不可用、或者从没设置过，都按「循环」处理。
     判据写成「不等于 "0"」而不是「等于 "1"」，所以将来多出别的脏值也仍然按默认开启走。 */
  function audioLoopEnabled() {
    var store = settingStorage();
    if (!store) {
      return true; // 存储不可用 ⇒ 用默认值（循环）
    }
    try {
      return store.getItem(AUDIO_LOOP_KEY) !== "0";
    } catch (error) {
      return true;
    }
  }

  function setAudioLoop(enabled) {
    var store = settingStorage();
    if (!store) {
      return false;
    }
    try {
      store.setItem(AUDIO_LOOP_KEY, enabled ? "1" : "0");
      return true;
    } catch (error) {
      return false;
    }
  }

  /* 供自动化测试使用的纯逻辑导出（无 DOM 依赖） */
  if (typeof globalThis !== "undefined") {
    globalThis.DailyLingo = {
      normalizeAnswer: normalizeAnswer,
      judge: judge,
      readingFollow: {
        key: READING_FOLLOW_KEY,
        enabled: readingFollowEnabled,
        set: setReadingFollow
      },
      audioLoop: {
        key: AUDIO_LOOP_KEY,
        enabled: audioLoopEnabled,
        set: setAudioLoop
      }
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
