/* ==========================================================================
   DailyLingo — 学习进度（本地存储 + 首页交互）
   职责：
     1. 每篇文章的「已完成」标记（localStorage 持久化）
     2. Chapter 汇总完成状态（由内部文章实时计算，不单独存储）
     3. 首页统计：已完成 / 总数 / 百分比 / 进度条
     4. 左上角设置入口里的进度导出与导入（合并 / 覆盖）

   同一份存储被两处使用：
     * 首页（本文档下半部分）：勾选 / 取消、统计、导入导出
     * 文章页（study-completion.js）：听完音频 + 全部题目答对 ⇒ 调用
       markCompleted() 自动写入同一条记录。首页下次打开就能看到勾。
   写作入口只有这里一处，避免两边各写一份 JSON 而造成格式漂移。

   设计约束：
     * 只依赖浏览器原生 API，无框架、无网络请求、无后端
     * 文章唯一 ID 用构建脚本写入的 `data-article-id`（四位补零的字符串）
     * 导出 / 导入用的 JSON 与 localStorage 同一结构，可互相读取
     * 纯逻辑（ID 规整、JSON 校验、去重、合并、统计、Chapter 判定）挂在
       globalThis.DailyLingoProgress 上，便于在 Node 里直接做自动化测试
   ========================================================================== */

(function () {
  "use strict";

  var STORAGE_KEY = "dailylingo_learning_progress_v1";
  var CORRUPT_KEY = STORAGE_KEY + "__corrupt"; // 损坏数据先留档，再重置
  var SCHEMA_VERSION = 1;

  /* ---------------------------------------------------------------- 纯逻辑 */

  function isPlainObject(value) {
    return !!value && typeof value === "object" && !Array.isArray(value);
  }

  /**
   * 把任意输入规整成文章 ID：四位补零的字符串，超过四位原样保留。
   * 数字 1 / 字符串 "1" / "0001" 都会得到 "0001"；非法输入返回 ""。
   */
  function normalizeId(raw) {
    var text;
    if (typeof raw === "number") {
      // 只接受非负整数；1.5 / -1 / NaN 一律判为非法，避免静默截断
      if (!isFinite(raw) || raw < 0 || Math.trunc(raw) !== raw) {
        return "";
      }
      text = String(raw);
    } else if (typeof raw === "string") {
      text = raw.trim();
    } else {
      return "";
    }
    if (!/^[0-9]+$/.test(text)) {
      return "";
    }
    if (text.length < 4) {
      text = ("0000" + text).slice(-4);
    }
    return text;
  }

  function uniqueSorted(ids) {
    var seen = Object.create(null);
    var out = [];
    for (var i = 0; i < ids.length; i++) {
      var id = ids[i];
      if (!seen[id]) {
        seen[id] = true;
        out.push(id);
      }
    }
    out.sort();
    return out;
  }

  function idsToSet(ids) {
    var set = Object.create(null);
    for (var i = 0; i < ids.length; i++) {
      set[ids[i]] = true;
    }
    return set;
  }

  /**
   * 校验一份进度对象（同时用于 localStorage 与导入文件）。
   * @returns {{ok: true, ids: string[], duplicates: number, invalidCount: number,
   *            rawCount: number, updatedAt: string} | {ok: false, error: string}}
   */
  function normalizeProgressObject(data) {
    if (!isPlainObject(data)) {
      return { ok: false, error: "文件结构不正确：顶层应当是 JSON 对象。" };
    }
    if (!Object.prototype.hasOwnProperty.call(data, "schemaVersion")) {
      return { ok: false, error: "缺少 schemaVersion，无法确认文件格式。" };
    }
    if (data.schemaVersion !== SCHEMA_VERSION) {
      return {
        ok: false,
        error:
          "不支持的版本：schemaVersion=" +
          String(data.schemaVersion) +
          "（本页只支持 " +
          SCHEMA_VERSION +
          "）。",
      };
    }
    var list = data.completedArticles;
    if (!Array.isArray(list)) {
      return { ok: false, error: "completedArticles 必须是数组。" };
    }
    var accepted = [];
    var invalid = 0;
    for (var i = 0; i < list.length; i++) {
      var id = normalizeId(list[i]);
      if (id) {
        accepted.push(id);
      } else {
        invalid++;
      }
    }
    var unique = uniqueSorted(accepted);
    return {
      ok: true,
      ids: unique,
      duplicates: accepted.length - unique.length,
      invalidCount: invalid,
      rawCount: list.length,
      updatedAt: typeof data.updatedAt === "string" ? data.updatedAt : "",
    };
  }

  /** 解析一段 JSON 文本（导入文件 / localStorage 原文共用）。 */
  function parseProgressPayload(text) {
    if (typeof text !== "string" || !text.trim()) {
      return { ok: false, error: "内容是空的。" };
    }
    var data;
    try {
      data = JSON.parse(text);
    } catch (err) {
      return { ok: false, error: "不是合法的 JSON 文本。" };
    }
    return normalizeProgressObject(data);
  }

  /** 把 ID 拆成「本项目存在」与「不存在」两组。 */
  function partition(ids, knownIds) {
    var known = idsToSet(knownIds);
    var valid = [];
    var unknown = [];
    for (var i = 0; i < ids.length; i++) {
      (known[ids[i]] ? valid : unknown).push(ids[i]);
    }
    return { valid: valid, unknown: unknown };
  }

  /** 合并：两者并集，不取消任何已有记录。 */
  function mergeIds(current, incoming) {
    return uniqueSorted(current.concat(incoming));
  }

  /**
   * 统计。只计入「实际存在的文章」；总数可以为 0，此时百分比按 0 处理，不做除法。
   */
  function computeStats(completedIds, knownIds) {
    var known = idsToSet(knownIds);
    var set = Object.create(null);
    var done = 0;
    for (var i = 0; i < completedIds.length; i++) {
      var id = completedIds[i];
      if (known[id] && !set[id]) {
        set[id] = true;
        done++;
      }
    }
    var total = knownIds.length;
    return {
      done: done,
      total: total,
      percent: total ? Math.round((done / total) * 100) : 0,
      ratio: total ? done / total : 0,
      set: set,
    };
  }

  /** Chapter 完成状态：按该 Chapter 实际存在的文章数判断，不假定 100 篇。 */
  function chapterStatus(chapterIds, completedSet) {
    var done = 0;
    for (var i = 0; i < chapterIds.length; i++) {
      if (completedSet[chapterIds[i]]) {
        done++;
      }
    }
    return {
      done: done,
      total: chapterIds.length,
      complete: chapterIds.length > 0 && done === chapterIds.length,
    };
  }

  function pad2(value) {
    return (value < 10 ? "0" : "") + value;
  }

  /** dailylingo-progress-YYYYMMDD.json */
  function exportFileName(now) {
    var date = now || new Date();
    return (
      "dailylingo-progress-" +
      date.getFullYear() +
      pad2(date.getMonth() + 1) +
      pad2(date.getDate()) +
      ".json"
    );
  }

  /** 导出对象：只含版本号、文章 ID 与时间，不含正文 / 音频 / 任何隐私数据。 */
  function buildExport(completedIds, updatedAt, now) {
    var stamp = (now || new Date()).toISOString();
    return {
      schemaVersion: SCHEMA_VERSION,
      completedArticles: uniqueSorted(completedIds),
      updatedAt: updatedAt || stamp,
      exportedAt: stamp,
    };
  }

  /* ---------------------------------------------------------------- 存储层 */

  function storageAvailable() {
    try {
      var probe = STORAGE_KEY + "__probe";
      window.localStorage.setItem(probe, "1");
      window.localStorage.removeItem(probe);
      return true;
    } catch (err) {
      return false;
    }
  }

  /**
   * 读取本地状态。任何异常都降级成「空进度 + 提示」，不让首页崩。
   * @returns {{status: "ok"|"empty"|"corrupt"|"unavailable", completed: string[],
   *            updatedAt: string, error: string}}
   */
  function loadState() {
    if (!storageAvailable()) {
      return { status: "unavailable", completed: [], updatedAt: "", error: "" };
    }
    var raw = null;
    try {
      raw = window.localStorage.getItem(STORAGE_KEY);
    } catch (err) {
      return { status: "unavailable", completed: [], updatedAt: "", error: String(err) };
    }
    if (raw == null || raw === "") {
      return { status: "empty", completed: [], updatedAt: "", error: "" };
    }
    var parsed = parseProgressPayload(raw);
    if (!parsed.ok) {
      // 先把坏数据另存一份（不销毁证据），再写回干净状态
      try {
        window.localStorage.setItem(CORRUPT_KEY, raw);
        window.localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ schemaVersion: SCHEMA_VERSION, completedArticles: [], updatedAt: "" })
        );
      } catch (err) {
        /* 备份失败也不影响首页可用 */
      }
      return { status: "corrupt", completed: [], updatedAt: "", error: parsed.error };
    }
    return { status: "ok", completed: parsed.ids, updatedAt: parsed.updatedAt, error: "" };
  }

  /** 写入本地状态。返回 null 表示成功，否则返回错误信息。 */
  function saveState(completedIds, updatedAt) {
    var payload = {
      schemaVersion: SCHEMA_VERSION,
      completedArticles: uniqueSorted(completedIds),
      updatedAt: updatedAt || new Date().toISOString(),
    };
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      return { ok: true, payload: payload };
    } catch (err) {
      return { ok: false, payload: payload, error: String(err && err.message ? err.message : err) };
    }
  }

  /**
   * 读取「已完成」编号（文章页用，只读不写）。
   * 存储不可用时返回空数组 —— 调用方靠 status 判断要不要提示。
   */
  function readCompleted() {
    return loadState();
  }

  /** 某篇文章是否已标记完成。 */
  function isCompleted(id) {
    var articleId = normalizeId(id);
    if (!articleId) {
      return false;
    }
    return loadState().completed.indexOf(articleId) !== -1;
  }

  /**
   * 把一篇文章标记为已完成（幂等）。
   *
   * 文章页的自动标记走这里：先读、再并集、再写，全程不碰别的编号，
   * 因此不会覆盖用户在首页做出的任何勾选 / 取消。
   *
   * @returns {{ok: boolean, already: boolean, completed: string[], error?: string}}
   */
  function markCompleted(id) {
    var articleId = normalizeId(id);
    if (!articleId) {
      return { ok: false, already: false, completed: [], error: "文章编号不合法。" };
    }
    var loaded = loadState();
    if (loaded.completed.indexOf(articleId) !== -1) {
      return { ok: true, already: true, completed: loaded.completed };
    }
    var next = uniqueSorted(loaded.completed.concat([articleId]));
    var saved = saveState(next, new Date().toISOString());
    if (!saved.ok) {
      return { ok: false, already: false, completed: loaded.completed, error: "本地存储不可用或已写满。" };
    }
    return { ok: true, already: false, completed: next };
  }

  /* -------------------------------------------------------------- DOM 层 */

  function init() {
    var items = Array.prototype.slice.call(document.querySelectorAll(".article-item"));
    if (!items.length && !document.querySelector("[data-progress-done]")) {
      return; // 不是首页
    }

    var knownIds = [];
    for (var i = 0; i < items.length; i++) {
      var id = items[i].getAttribute("data-article-id");
      if (id) {
        knownIds.push(id);
      }
    }

    var nodes = {
      done: document.querySelector("[data-progress-done]"),
      total: document.querySelector("[data-progress-total]"),
      percent: document.querySelector("[data-progress-percent]"),
      fill: document.querySelector("[data-progress-fill]"),
      bar: document.querySelector("[data-progress-bar]"),
      notice: document.querySelector("[data-progress-notice]"),
    };

    var loaded = loadState();
    var state = {
      completed: loaded.completed,
      updatedAt: loaded.updatedAt,
      persistent: loaded.status !== "unavailable",
    };

    function notify(text, kind) {
      if (!nodes.notice) {
        return;
      }
      nodes.notice.textContent = text || "";
      nodes.notice.classList.remove("is-ok", "is-err", "is-hint");
      if (kind) {
        nodes.notice.classList.add(kind === "ok" ? "is-ok" : kind === "err" ? "is-err" : "is-hint");
      }
      nodes.notice.hidden = !text;
    }

    function articleTitle(item) {
      var link = item.querySelector(".article-link");
      return link ? String(link.textContent || "").trim() : "";
    }

    function renderItems(stats) {
      for (var i = 0; i < items.length; i++) {
        var item = items[i];
        var id = item.getAttribute("data-article-id");
        var done = !!stats.set[id];
        var button = item.querySelector('[data-action="toggle-complete"]');
        if (button) {
          button.setAttribute("aria-pressed", done ? "true" : "false");
          button.setAttribute(
            "aria-label",
            "标记「" + articleTitle(item) + "」为" + (done ? "未完成" : "已完成")
          );
        }
        item.classList.toggle("is-done", done);
      }
    }

    function renderChapters(stats) {
      var chapters = Array.prototype.slice.call(document.querySelectorAll(".chapter"));
      for (var i = 0; i < chapters.length; i++) {
        var chapter = chapters[i];
        var chapterIds = [];
        var chapterItems = chapter.querySelectorAll(".article-item");
        for (var j = 0; j < chapterItems.length; j++) {
          var cid = chapterItems[j].getAttribute("data-article-id");
          if (cid) {
            chapterIds.push(cid);
          }
        }
        var status = chapterStatus(chapterIds, stats.set);
        var box = chapter.querySelector("[data-chapter-status]");
        if (!box) {
          continue;
        }
        var count = box.querySelector("[data-chapter-count]");
        var stateText = box.querySelector("[data-chapter-state]");
        var meter = box.querySelector("[data-chapter-fill]");
        var meterBar = box.querySelector("[data-chapter-bar]");
        if (count) {
          count.textContent = status.done + "/" + status.total;
        }
        if (stateText) {
          stateText.textContent = status.complete ? "已完成" : "未完成";
        }
        // 每章独立的进度条：宽度按本章完成比例算，不掺入其他 Chapter
        if (meter) {
          var ratio = status.total > 0 ? status.done / status.total : 0;
          meter.style.width = (ratio * 100).toFixed(1) + "%";
        }
        if (meterBar) {
          meterBar.setAttribute("aria-valuenow", String(status.done));
          meterBar.setAttribute("aria-valuemax", String(status.total));
          meterBar.setAttribute("aria-valuetext", status.done + "/" + status.total + " 篇");
        }
        box.classList.toggle("is-complete", status.complete);
        chapter.classList.toggle("is-complete", status.complete);
      }
    }

    function renderStats(stats) {
      if (nodes.done) {
        nodes.done.textContent = String(stats.done);
      }
      if (nodes.total) {
        nodes.total.textContent = String(stats.total);
      }
      if (nodes.percent) {
        nodes.percent.textContent = stats.percent + "%";
      }
      if (nodes.fill) {
        nodes.fill.style.width = (stats.ratio * 100).toFixed(1) + "%";
      }
      if (nodes.bar) {
        nodes.bar.setAttribute("aria-valuenow", String(stats.done));
        nodes.bar.setAttribute("aria-valuemax", String(stats.total));
        nodes.bar.setAttribute(
          "aria-valuetext",
          "共 " + stats.total + " 篇，已完成 " + stats.done + " 篇（" + stats.percent + "%）"
        );
      }
    }

    function refresh() {
      var stats = computeStats(state.completed, knownIds);
      renderItems(stats);
      renderChapters(stats);
      renderStats(stats);
    }

    function persist() {
      state.updatedAt = new Date().toISOString();
      var result = saveState(state.completed, state.updatedAt);
      if (!result.ok) {
        state.persistent = false;
        notify("保存失败：本地存储不可用或已写满，本次标记刷新后会丢失。", "err");
        return false;
      }
      return true;
    }

    function toggle(id) {
      var index = state.completed.indexOf(id);
      if (index === -1) {
        state.completed = state.completed.concat([id]);
      } else {
        state.completed = state.completed.slice(0, index).concat(state.completed.slice(index + 1));
      }
      persist();
      refresh();
    }

    function setCompleted(ids) {
      state.completed = uniqueSorted(ids);
      persist();
      refresh();
    }

    // ---- 文章完成按钮
    document.addEventListener("click", function (event) {
      var button = event.target.closest ? event.target.closest('[data-action="toggle-complete"]') : null;
      if (!button) {
        return;
      }
      // 图标只是状态开关：既不跳转文章，也不触发 Chapter 展开 / 折叠
      event.preventDefault();
      event.stopPropagation();
      var id = button.getAttribute("data-article-id");
      if (id) {
        toggle(id);
      }
    });

    refresh();

    // ---- 初始状态提示
    if (loaded.status === "unavailable") {
      notify("浏览器禁用了本地存储：标记只在当前页面有效，刷新后会丢失。", "err");
    } else if (loaded.status === "corrupt") {
      notify("本地学习记录已损坏（" + loaded.error + "），已备份原数据并重置为空白。", "err");
    } else {
      var orphan = partition(state.completed, knownIds).unknown.length;
      if (orphan > 0) {
        notify("有 " + orphan + " 条记录对应的文章已不存在，已忽略（不会被删除）。", "hint");
      } else {
        notify("", "");
      }
    }

    bindSettings({
      knownIds: knownIds,
      getCompleted: function () {
        return state.completed.slice();
      },
      setCompleted: setCompleted,
      notify: notify,
      isPersistent: function () {
        return state.persistent;
      },
    });
  }

  /* ------------------------------------------------------- 设置对话框 */

  function bindSettings(ctx) {
    var dialog = document.getElementById("settings-dialog");
    var openBtn = document.querySelector('[data-action="open-settings"]');
    if (!dialog || !openBtn) {
      return;
    }
    var settingsMsg = dialog.querySelector("[data-settings-message]");
    var preview = dialog.querySelector("[data-import-preview]");
    var confirmBox = dialog.querySelector("[data-import-confirm]");
    var importMsg = dialog.querySelector("[data-import-message]");
    var fileInput = dialog.querySelector("[data-import-input]");
    var followInput = dialog.querySelector('[data-setting="reading-follow"]');
    var loopInput = dialog.querySelector('[data-setting="audio-loop"]');
    var pending = null; // { valid: string[], unknown: number }

    /* 设置项的读写由 main.js 提供（文章页也要读同一个键），这里只负责界面。
       name 是 globalThis.DailyLingo 下的属性名，两个开关共用一套读写。 */
    function settingsApi(name) {
      var api = typeof globalThis !== "undefined" ? globalThis.DailyLingo : null;
      return api && api[name] ? api[name] : null;
    }

    function syncToggle(input, name) {
      if (!input) {
        return;
      }
      var api = settingsApi(name);
      input.checked = !!(api && typeof api.enabled === "function" && api.enabled());
    }

    function bindToggle(input, name, onText, offText) {
      if (!input) {
        return;
      }
      syncToggle(input, name);
      input.addEventListener("change", function () {
        var api = settingsApi(name);
        var wanted = !!input.checked;
        var saved = !!(api && typeof api.set === "function" && api.set(wanted));
        if (!saved) {
          // 存储不可用（隐私模式 / 被策略禁用）：把开关拨回去，别让人以为已经生效
          input.checked = !wanted;
          setMessage(settingsMsg, "当前浏览器无法保存设置（本地存储不可用）。", "err");
          return;
        }
        setMessage(settingsMsg, wanted ? onText : offText, "ok");
      });
    }

    function setMessage(node, text, kind) {
      if (!node) {
        return;
      }
      node.textContent = text || "";
      node.classList.remove("is-ok", "is-err", "is-hint");
      if (kind) {
        node.classList.add(kind === "ok" ? "is-ok" : kind === "err" ? "is-err" : "is-hint");
      }
    }

    function openDialog() {
      setMessage(settingsMsg, "", "");
      // 可能刚在别的标签页改过，每次打开都对齐一次
      syncToggle(followInput, "readingFollow");
      syncToggle(loopInput, "audioLoop");
      if (typeof dialog.showModal === "function") {
        try {
          dialog.showModal();
        } catch (err) {
          dialog.setAttribute("open", "");
        }
      } else {
        dialog.setAttribute("open", ""); // 老浏览器降级：以属性打开
        dialog.classList.add("is-fallback");
      }
      openBtn.setAttribute("aria-expanded", "true");
      var first = dialog.querySelector('[data-action="export-progress"]');
      if (first && typeof first.focus === "function") {
        first.focus();
      }
    }

    function closeDialog() {
      hidePreview();
      hideConfirm();
      setMessage(settingsMsg, "", "");
      if (typeof dialog.close === "function") {
        try {
          dialog.close();
        } catch (err) {
          dialog.removeAttribute("open");
        }
      } else {
        dialog.removeAttribute("open");
      }
      openBtn.setAttribute("aria-expanded", "false");
      if (typeof openBtn.focus === "function") {
        openBtn.focus();
      }
    }

    function hidePreview() {
      if (preview) {
        preview.hidden = true;
      }
      pending = null;
      if (fileInput) {
        fileInput.value = "";
      }
    }

    function hideConfirm() {
      if (confirmBox) {
        confirmBox.hidden = true;
      }
    }

    function fillPreview(parsed) {
      var parts = partition(parsed.ids, ctx.knownIds);
      var current = partition(ctx.getCompleted(), ctx.knownIds).valid;
      var mergedCount = mergeIds(current, parts.valid).length;

      var fileCount = dialog.querySelector("[data-import-file-count]");
      var currentCount = dialog.querySelector("[data-import-current-count]");
      var mergedField = dialog.querySelector("[data-import-merged-count]");
      var overwriteField = dialog.querySelector("[data-import-overwrite-count]");
      if (fileCount) {
        fileCount.textContent = String(parts.valid.length);
      }
      if (currentCount) {
        currentCount.textContent = String(current.length);
      }
      if (mergedField) {
        mergedField.textContent = String(mergedCount);
      }
      if (overwriteField) {
        overwriteField.textContent = String(parts.valid.length);
      }

      var notes = [];
      if (parts.unknown.length) {
        notes.push("忽略 " + parts.unknown.length + " 条不存在的文章编号");
      }
      if (parsed.duplicates) {
        notes.push("去重 " + parsed.duplicates + " 条重复编号");
      }
      if (parsed.invalidCount) {
        notes.push("跳过 " + parsed.invalidCount + " 条格式非法的编号");
      }
      setMessage(importMsg, notes.length ? notes.join("；") + "。" : "文件校验通过。", notes.length ? "hint" : "ok");

      pending = { valid: parts.valid, unknown: parts.unknown.length };
      if (preview) {
        preview.hidden = parts.valid.length === 0;
      }
      return parts.valid.length; // 0 表示这份文件对本项目毫无意义
    }

    function doExport() {
      try {
        var valid = partition(ctx.getCompleted(), ctx.knownIds).valid;
        var payload = buildExport(valid, "", new Date());
        var text = JSON.stringify(payload, null, 2) + "\n";
        var name = exportFileName(new Date());

        if (typeof Blob === "undefined" || typeof URL === "undefined" || !URL.createObjectURL) {
          throw new Error("当前浏览器不支持文件下载");
        }
        var url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
        var link = document.createElement("a");
        link.href = url;
        link.download = name;
        link.rel = "noopener";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(function () {
          try {
            URL.revokeObjectURL(url);
          } catch (err) {
            /* 忽略 */
          }
        }, 1000);
        setMessage(settingsMsg, "已导出 " + payload.completedArticles.length + " 条记录：" + name, "ok");
      } catch (err) {
        setMessage(
          settingsMsg,
          "导出失败：" + (err && err.message ? err.message : "未知错误") + "。可改用浏览器的「打印 / 另存为」备份本地记录。",
          "err"
        );
      }
    }

    function onFilePicked(event) {
      var file = event.target.files && event.target.files[0];
      if (!file) {
        return;
      }
      hideConfirm();
      setMessage(settingsMsg, "", "");
      if (typeof FileReader === "undefined") {
        setMessage(settingsMsg, "当前浏览器不支持读取本地文件。", "err");
        return;
      }
      var reader = new FileReader();
      reader.onerror = function () {
        setMessage(settingsMsg, "读取文件失败，请重试。", "err");
        if (fileInput) {
          fileInput.value = "";
        }
      };
      reader.onload = function () {
        var parsed = parseProgressPayload(String(reader.result || ""));
        if (!parsed.ok) {
          hidePreview();
          setMessage(settingsMsg, "导入失败：" + parsed.error + " 现有进度未被修改。", "err");
          return;
        }
        if (!parsed.ids.length) {
          hidePreview();
          setMessage(settingsMsg, "导入失败：文件里没有任何有效的文章编号。现有进度未被修改。", "err");
          return;
        }
        if (!fillPreview(parsed)) {
          hidePreview();
          setMessage(
            settingsMsg,
            "导入失败：文件的 " + parsed.ids.length + " 条编号在本项目中都不存在。现有进度未被修改。",
            "err"
          );
        }
      };
      reader.readAsText(file, "utf-8");
    }

    function commitImport(mode) {
      if (!pending) {
        return;
      }
      var before = partition(ctx.getCompleted(), ctx.knownIds).valid.length;
      var next = mode === "overwrite" ? pending.valid.slice() : mergeIds(ctx.getCompleted(), pending.valid);
      ctx.setCompleted(next);
      var after = partition(next, ctx.knownIds).valid.length;
      hideConfirm();
      hidePreview();
      var verb = mode === "overwrite" ? "覆盖" : "合并";
      var extra = ctx.isPersistent() ? "" : "（注意：本地存储不可用，本次结果刷新后会丢失）";
      setMessage(
        settingsMsg,
        "已" + verb + "导入：当前已完成 " + after + " 篇（导入前 " + before + " 篇）" + extra + "。",
        ctx.isPersistent() ? "ok" : "hint"
      );
    }

    function applyImport() {
      if (!pending) {
        return;
      }
      var mode = "merge";
      var chosen = dialog.querySelector('input[name="import-mode"]:checked');
      if (chosen && chosen.value === "overwrite") {
        mode = "overwrite";
      }
      if (mode === "overwrite") {
        // 覆盖会取消记录 ⇒ 必须二次确认
        if (confirmBox) {
          confirmBox.hidden = false;
          var confirmBtn = confirmBox.querySelector('[data-action="confirm-overwrite"]');
          if (confirmBtn && typeof confirmBtn.focus === "function") {
            confirmBtn.focus();
          }
        }
        return;
      }
      commitImport("merge");
    }

    openBtn.addEventListener("click", function (event) {
      event.preventDefault();
      openDialog();
    });
    dialog.addEventListener("close", function () {
      openBtn.setAttribute("aria-expanded", "false");
      hidePreview();
      hideConfirm();
    });
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) {
        closeDialog(); // 点遮罩关闭
      }
    });

    dialog.addEventListener("click", function (event) {
      var target = event.target.closest ? event.target.closest("[data-action]") : null;
      if (!target) {
        return;
      }
      var action = target.getAttribute("data-action");
      if (action === "close-settings") {
        closeDialog();
      } else if (action === "export-progress") {
        doExport();
      } else if (action === "pick-import" && fileInput) {
        fileInput.click();
      } else if (action === "apply-import") {
        applyImport();
      } else if (action === "cancel-import") {
        hidePreview();
        hideConfirm();
        setMessage(settingsMsg, "已取消导入，现有进度未被修改。", "hint");
      } else if (action === "confirm-overwrite") {
        commitImport("overwrite");
      } else if (action === "cancel-overwrite") {
        hideConfirm();
      }
    });

    if (fileInput) {
      fileInput.addEventListener("change", onFilePicked);
    }

    bindToggle(followInput, "readingFollow", "已开启页面语音跟随。", "已关闭页面语音跟随。");
    bindToggle(loopInput, "audioLoop", "已开启播完循环播放。", "已关闭播完循环播放。");
  }

  /* -------------------------------------------------------------- 启动 */

  /* 供自动化测试使用的纯逻辑（无 DOM / 无 localStorage 依赖） */
  if (typeof globalThis !== "undefined") {
    globalThis.DailyLingoProgress = {
      STORAGE_KEY: STORAGE_KEY,
      CORRUPT_KEY: CORRUPT_KEY,
      SCHEMA_VERSION: SCHEMA_VERSION,
      normalizeId: normalizeId,
      uniqueSorted: uniqueSorted,
      normalizeProgressObject: normalizeProgressObject,
      parseProgressPayload: parseProgressPayload,
      partition: partition,
      mergeIds: mergeIds,
      computeStats: computeStats,
      chapterStatus: chapterStatus,
      buildExport: buildExport,
      exportFileName: exportFileName,
      readCompleted: readCompleted,
      isCompleted: isCompleted,
      markCompleted: markCompleted,
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
