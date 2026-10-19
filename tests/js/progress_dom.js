/* ==========================================================================
   DailyLingo — 学习进度的真实 DOM 测试（jsdom）
   用法：node progress_dom.js <index.html> <progress.js> [main.js]
   输出：一行 JSON，形如 {"fresh": {...}, "toggle_one": {...}, ...}

   jsdom 只是开发期的临时依赖（不随站点发布）；tests/test_progress_dom.py 找不到
   jsdom 时会自动跳过本脚本对应的测试，因此 pytest 仍可在纯净环境跑通。
   ========================================================================== */

'use strict';

const fs = require('fs');
const { JSDOM } = require('jsdom');

const INDEX = process.argv[2];
const SCRIPT = process.argv[3];
const MAIN = process.argv[4]; // 可选：main.js（提供「页面语音跟随」设置）
const html = fs.readFileSync(INDEX, 'utf8');
const source = fs.readFileSync(SCRIPT, 'utf8');
const mainSource = MAIN ? fs.readFileSync(MAIN, 'utf8') : null;

const KEY = 'dailylingo_learning_progress_v1';
const FOLLOW_KEY = 'dailylingo_reading_follow_v1';
const out = {};

function tick(ms) {
  return new Promise(function (resolve) {
    setTimeout(resolve, ms || 20);
  });
}

async function boot(seed, options) {
  const dom = new JSDOM(
    html,
    Object.assign({ url: 'https://example.test/', runScripts: 'outside-only' }, options || {})
  );
  const w = dom.window;
  if (seed !== undefined && seed !== null) {
    w.localStorage.setItem(KEY, seed);
  }
  if (mainSource) {
    w.eval(mainSource); // 真实页面上 main.js 先于 progress.js 执行
  }
  w.eval(source);
  // 真实浏览器里 progress.js 以 defer 执行：解析完成、DOMContentLoaded 之前
  await new Promise(function (resolve) {
    if (w.document.readyState === 'complete') {
      resolve();
    } else {
      w.addEventListener('load', resolve);
    }
  });
  return w;
}

function q(w, sel) {
  return w.document.querySelector(sel);
}

function stats(w) {
  return {
    done: q(w, '[data-progress-done]').textContent,
    total: q(w, '[data-progress-total]').textContent,
    percent: q(w, '[data-progress-percent]').textContent,
    fill: q(w, '[data-progress-fill]').style.width,
    valuenow: q(w, '[data-progress-bar]').getAttribute('aria-valuenow'),
  };
}

function chapter(w, index) {
  const boxes = w.document.querySelectorAll('[data-chapter-status]');
  const box = boxes[index || 0];
  return {
    count: box.querySelector('[data-chapter-count]').textContent,
    state: box.querySelector('[data-chapter-state]').textContent,
    complete: box.classList.contains('is-complete'),
  };
}

function pressed(w) {
  return Array.prototype.map.call(w.document.querySelectorAll('.article-toggle'), function (b) {
    return b.getAttribute('aria-pressed');
  });
}

function stored(w) {
  return JSON.parse(w.localStorage.getItem(KEY) || 'null');
}

function toggleBtn(w, id) {
  return w.document.querySelector('[data-action="toggle-complete"][data-article-id="' + id + '"]');
}

async function pickFile(w, text, name) {
  const input = q(w, '[data-import-input]');
  const file = new w.File([text], name || 'progress.json', { type: 'application/json' });
  Object.defineProperty(input, 'files', { value: [file], configurable: true });
  input.dispatchEvent(new w.Event('change', { bubbles: true }));
  await tick(40);
}

(async function () {
  /* 1. 第一次访问：全未完成，无存储 */
  {
    const w = await boot(null);
    const items = w.document.querySelectorAll('.article-item');
    out.meta = {
      total: items.length,
      chapterTotal: Number(
        q(w, '[data-chapter-total]').getAttribute('data-chapter-total')
      ),
      ids: Array.prototype.map.call(items, function (el) {
        return el.getAttribute('data-article-id');
      }),
    };
    out.fresh = {
      stats: stats(w),
      chapter: chapter(w),
      pressed: pressed(w),
      storage: w.localStorage.getItem(KEY),
      notice: q(w, '[data-progress-notice]').textContent,
    };
    w.close();
  }

  /* 2. 勾选一篇：统计 / 章节 / 存储 / 不跳转 / 不折叠 */
  {
    const w = await boot(null);
    const before = w.location.href;
    const details = q(w, 'details.chapter');
    const wasOpen = details.open;
    toggleBtn(w, '0001').click();
    out.toggle_one = {
      stats: stats(w),
      chapter: chapter(w),
      pressed0001: toggleBtn(w, '0001').getAttribute('aria-pressed'),
      label0001: toggleBtn(w, '0001').getAttribute('aria-label'),
      itemDone: q(w, '.article-item[data-article-id="0001"]').classList.contains('is-done'),
      storage: stored(w),
      locationSame: w.location.href === before,
      detailsUnchanged: details.open === wasOpen,
    };

    /* 3. 再点一次取消 */
    toggleBtn(w, '0001').click();
    out.toggle_off = {
      stats: stats(w),
      chapter: chapter(w),
      pressed0001: toggleBtn(w, '0001').getAttribute('aria-pressed'),
      storage: stored(w),
    };
    w.close();
  }

  /* 4/5. 全部完成 -> 章节绿勾；取消一篇 -> 绿勾消失 */
  {
    const w = await boot(null);
    Array.prototype.forEach.call(w.document.querySelectorAll('.article-toggle'), function (b) {
      b.click();
    });
    out.all_done = { stats: stats(w), chapter: chapter(w) };
    toggleBtn(w, '0003').click();
    out.uncheck_one = { stats: stats(w), chapter: chapter(w) };
    out.reload_seed = w.localStorage.getItem(KEY);
    w.close();
  }

  /* 6. 刷新（把存储带进新实例）后状态恢复 */
  {
    const w = await boot(out.reload_seed);
    out.reload = {
      stats: stats(w),
      chapter: chapter(w),
      pressed0003: toggleBtn(w, '0003').getAttribute('aria-pressed'),
    };
    w.close();
  }

  /* 7. 本地数据损坏：提示 + 备份 + 重置，页面不崩 */
  {
    const w = await boot('{oops');
    out.corrupt = {
      notice: q(w, '[data-progress-notice]').textContent,
      backup: w.localStorage.getItem(KEY + '__corrupt'),
      stats: stats(w),
      rewritten: JSON.parse(w.localStorage.getItem(KEY)),
    };
    w.close();
  }

  /* 8. 本地存储不可用：仍然可用（内存态）+ 明确提示 */
  {
    const w = await boot(null, { url: 'about:blank' });
    const before = q(w, '[data-progress-notice]').textContent;
    toggleBtn(w, '0001').click();
    out.unavailable = {
      noticeBefore: before,
      noticeAfter: q(w, '[data-progress-notice]').textContent,
      stats: stats(w),
    };
    w.close();
  }

  /* 9. 合并导入：保留现有 + 并集 */
  {
    const w = await boot(null);
    toggleBtn(w, '0001').click();
    toggleBtn(w, '0002').click();
    await pickFile(w, JSON.stringify({ schemaVersion: 1, completedArticles: ['0003', '0004', '0001'] }));
    out.import_preview_merge = {
      fileCount: q(w, '[data-import-file-count]').textContent,
      currentCount: q(w, '[data-import-current-count]').textContent,
      mergedCount: q(w, '[data-import-merged-count]').textContent,
      overwriteCount: q(w, '[data-import-overwrite-count]').textContent,
      previewVisible: !q(w, '[data-import-preview]').hidden,
      message: q(w, '[data-import-message]').textContent,
    };
    q(w, '[data-action="apply-import"]').click();
    out.import_merge = {
      stats: stats(w),
      storage: stored(w),
      message: q(w, '[data-settings-message]').textContent,
    };
    w.close();
  }

  /* 10. 覆盖导入：需要二次确认，且能取消原有记录 */
  {
    const w = await boot(null);
    ['0001', '0002', '0003'].forEach(function (id) {
      toggleBtn(w, id).click();
    });
    await pickFile(w, JSON.stringify({ schemaVersion: 1, completedArticles: ['0005'] }));
    q(w, 'input[value="overwrite"]').checked = true;
    q(w, '[data-action="apply-import"]').click();
    out.import_overwrite_confirm = {
      confirmVisible: !q(w, '[data-import-confirm]').hidden,
      statsBeforeConfirm: stats(w),
      storageBeforeConfirm: stored(w),
    };
    q(w, '[data-action="confirm-overwrite"]').click();
    out.import_overwrite = { stats: stats(w), storage: stored(w) };
    w.close();
  }

  /* 11. 取消覆盖确认：进度不变 */
  {
    const w = await boot(null);
    toggleBtn(w, '0001').click();
    await pickFile(w, JSON.stringify({ schemaVersion: 1, completedArticles: ['0006'] }));
    q(w, 'input[value="overwrite"]').checked = true;
    q(w, '[data-action="apply-import"]').click();
    q(w, '[data-action="cancel-overwrite"]').click();
    out.import_overwrite_cancel = {
      confirmVisible: !q(w, '[data-import-confirm]').hidden,
      stats: stats(w),
    };
    w.close();
  }

  /* 12. 非法 JSON / 不支持的版本：不破坏现有进度 */
  {
    const w = await boot(null);
    toggleBtn(w, '0001').click();
    await pickFile(w, '{ not json');
    out.import_bad_json = {
      message: q(w, '[data-settings-message]').textContent,
      stats: stats(w),
      previewVisible: !q(w, '[data-import-preview]').hidden,
    };
    await pickFile(w, JSON.stringify({ schemaVersion: 2, completedArticles: ['0002'] }));
    out.import_bad_version = {
      message: q(w, '[data-settings-message]').textContent,
      stats: stats(w),
    };
    w.close();
  }

  /* 13. 含不存在编号：忽略并提示 */
  {
    const w = await boot(null);
    await pickFile(w, JSON.stringify({ schemaVersion: 1, completedArticles: ['0001', '9999', '8888'] }));
    out.import_unknown = {
      fileCount: q(w, '[data-import-file-count]').textContent,
      message: q(w, '[data-import-message]').textContent,
    };
    q(w, '[data-action="apply-import"]').click();
    out.import_unknown_after = { stats: stats(w), storage: stored(w) };
    w.close();
  }

  /* 14. 只含不存在编号：拒绝导入，进度不变 */
  {
    const w = await boot(null);
    toggleBtn(w, '0002').click();
    await pickFile(w, JSON.stringify({ schemaVersion: 1, completedArticles: ['9999'] }));
    out.import_all_unknown = {
      message: q(w, '[data-settings-message]').textContent,
      previewVisible: !q(w, '[data-import-preview]').hidden,
      stats: stats(w),
    };
    w.close();
  }

  /* 15. 导出：文件名 / JSON 结构 / 只含有效编号 */
  {
    const w = await boot(null);
    toggleBtn(w, '0001').click();
    toggleBtn(w, '0002').click();
    let captured = null;
    let downloaded = null;
    w.URL.createObjectURL = function (blob) {
      captured = blob;
      return 'blob:test';
    };
    w.URL.revokeObjectURL = function () {};
    const realClick = w.HTMLAnchorElement.prototype.click;
    w.HTMLAnchorElement.prototype.click = function () {
      downloaded = { download: this.download, href: this.href };
    };
    q(w, '[data-action="open-settings"]').click();
    q(w, '[data-action="export-progress"]').click();
    await tick(20);
    w.HTMLAnchorElement.prototype.click = realClick;
    const text = captured && captured.text ? await captured.text() : '';
    out.export = {
      downloaded: downloaded,
      message: q(w, '[data-settings-message]').textContent,
      payload: text ? JSON.parse(text) : null,
    };
    w.close();
  }

  /* 16. 设置对话框开关与 aria-expanded */
  {
    const w = await boot(null);
    const btn = q(w, '[data-action="open-settings"]');
    out.dialog_closed = {
      expanded: btn.getAttribute('aria-expanded'),
      open: q(w, '#settings-dialog').open,
    };
    btn.click();
    out.dialog_open = {
      expanded: btn.getAttribute('aria-expanded'),
      open: q(w, '#settings-dialog').hasAttribute('open'),
    };
    q(w, '[data-action="close-settings"]').click();
    out.dialog_after_close = {
      expanded: btn.getAttribute('aria-expanded'),
      previewVisible: !q(w, '[data-import-preview]').hidden,
    };
    w.close();
  }

  /* 17. 「页面语音跟随」开关：默认关闭、切换即写存储、重开对话框保持状态 */
  {
    const w = await boot(null);
    const input = q(w, '#setting-reading-follow');
    out.follow_default = {
      exists: !!input,
      checked: input ? input.checked : null,
      stored: w.localStorage.getItem(FOLLOW_KEY),
    };
    q(w, '[data-action="open-settings"]').click();
    input.checked = true;
    input.dispatchEvent(new w.Event('change', { bubbles: true }));
    out.follow_on = {
      checked: input.checked,
      stored: w.localStorage.getItem(FOLLOW_KEY),
      message: q(w, '[data-settings-message]').textContent,
    };
    q(w, '[data-action="close-settings"]').click();
    q(w, '[data-action="open-settings"]').click(); // 重开：应从存储恢复
    out.follow_reopen = { checked: input.checked };
    input.checked = false;
    input.dispatchEvent(new w.Event('change', { bubbles: true }));
    out.follow_off = {
      checked: input.checked,
      stored: w.localStorage.getItem(FOLLOW_KEY),
      message: q(w, '[data-settings-message]').textContent,
    };
    w.close();
  }

  process.stdout.write(JSON.stringify(out));
})().catch(function (err) {
  process.stderr.write(String((err && err.stack) || err));
  process.exit(1);
});
