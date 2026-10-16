/* ==========================================================================
   DailyLingo — 页面交互
   职责：阅读理解练习的判分（单选 + 填空）、答案反馈、可访问性状态维护。

   正确答案来自页面内嵌的 <script type="application/json" id="quiz-data">，
   与构建脚本生成的数据同源，因此自动判分与 Answers 区域显示的答案必然一致。

   判分规则集中在 judge() / normalizeAnswer() 中，并在无 DOM 环境（Node）下
   通过 globalThis.DailyLingo 暴露，以便自动化测试直接验证边界条件。
   ========================================================================== */

(function () {
  "use strict";

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
  }

  /* 供自动化测试使用的纯逻辑导出（无 DOM 依赖） */
  if (typeof globalThis !== "undefined") {
    globalThis.DailyLingo = { normalizeAnswer: normalizeAnswer, judge: judge };
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
