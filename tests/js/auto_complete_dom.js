/* ==========================================================================
   DailyLingo — 文章页「自动完成」的真实 DOM 测试（jsdom）
   用法：node auto_complete_dom.js <article.html> <progress.js> <main.js> <study-completion.js>
   输出：一行 JSON，`out.<scenario>` 是各场景的观测值。

   做法：在真实生成的**文章页**里执行三个真实脚本（不加载 audio-player.js，
   改用直接派发同名事件来模拟播放器上报），然后用真实 click 完成答题。
   播放器的「累计收听时长」算法由 tests/test_audio_listen.py 直接对着
   audio-player.js 里的常量与事件名做契约断言，两条测试互补。
   ========================================================================== */

'use strict';

const fs = require('fs');
const { JSDOM } = require('jsdom');

const PAGE = process.argv[2];
const PROGRESS = process.argv[3];
const MAIN = process.argv[4];
const COMPLETION = process.argv[5];

const html = fs.readFileSync(PAGE, 'utf8');
const progressSource = fs.readFileSync(PROGRESS, 'utf8');
const mainSource = fs.readFileSync(MAIN, 'utf8');
const completionSource = fs.readFileSync(COMPLETION, 'utf8');

const KEY = 'dailylingo_learning_progress_v1';
const PAGE_ID = (html.match(/data-article-id="(\d+)"/) || [, ''])[1];
const out = {};

async function boot(seed, options) {
  const dom = new JSDOM(
    html,
    Object.assign({ url: 'https://example.test/', runScripts: 'outside-only' }, options || {})
  );
  const w = dom.window;
  if (seed !== undefined && seed !== null) {
    w.localStorage.setItem(KEY, seed);
  }
  // 真实页面的加载顺序：main.js → progress.js → study-completion.js（都是 defer）
  w.eval(mainSource);
  w.eval(progressSource);
  w.eval(completionSource);
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

function status(w) {
  const node = q(w, '[data-study-status]');
  return {
    text: node.textContent,
    done: node.classList.contains('is-done'),
    error: node.classList.contains('is-error'),
    autoable: node.getAttribute('data-study-auto'),
  };
}

function stored(w) {
  return JSON.parse(w.localStorage.getItem(KEY) || 'null');
}

function articleId(w) {
  return w.document.body.getAttribute('data-article-id');
}

/* 全部答对：按 quiz-data 里给的答案真实填写并点「检查答案」 */
function answerAllCorrect(w) {
  const data = JSON.parse(q(w, '#quiz-data').textContent);
  let count = 0;
  Array.prototype.forEach.call(w.document.querySelectorAll('.question'), function (item) {
    const entry = data[item.getAttribute('data-qid')];
    if (!entry) {
      return;
    }
    if (entry.type === 'choice') {
      const radio = item.querySelector('input[type="radio"][value="' + entry.answer + '"]');
      radio.checked = true;
      radio.dispatchEvent(new w.Event('change', { bubbles: true }));
    } else {
      item.querySelector('.fill-input').value = entry.answer;
    }
    item.querySelector('[data-action="check"]').click();
    count++;
  });
  return count;
}

/* 模拟 audio-player.js 的上报（同一个事件名、同一个 detail 结构） */
function listen(w, ratio, ended) {
  const target = q(w, '[data-player]') || w.document.body;
  target.dispatchEvent(
    new w.CustomEvent('dailylingo:listen', {
      bubbles: true,
      detail: { ratio: ratio, seconds: ratio * 100, duration: 100, ended: !!ended },
    })
  );
}

(async function () {
  out.meta = {
    articleId: PAGE_ID,
    questions: (html.match(/class="question"/g) || []).length,
    hasPlayer: /data-player/.test(html),
    autoAttr: (html.match(/data-study-auto="(true|false)"/) || [, ''])[1],
  };

  /* 1. 首次进入：什么都没做 ⇒ 不标记，保持构建期文案 */
  {
    const w = await boot(null);
    out.fresh = { status: status(w), storage: w.localStorage.getItem(KEY) };
    w.close();
  }

  /* 2. 只答对题、没听 ⇒ 不标记，提示里要能看出答对了几题 */
  {
    const w = await boot(null);
    const answered = answerAllCorrect(w);
    out.quiz_only = {
      answered: answered,
      status: status(w),
      storage: w.localStorage.getItem(KEY),
    };
    w.close();
  }

  /* 3. 只听够、没答题 ⇒ 不标记 */
  {
    const w = await boot(null);
    listen(w, 0.95, true);
    out.listen_only = { status: status(w), storage: w.localStorage.getItem(KEY) };
    w.close();
  }

  /* 4. 听了一半 + 全答对 ⇒ 仍不标记（阈值 0.9） */
  {
    const w = await boot(null);
    answerAllCorrect(w);
    listen(w, 0.5, false);
    out.partial = { status: status(w), storage: w.localStorage.getItem(KEY) };
    w.close();
  }

  /* 5. 听够 + 全答对 ⇒ 自动标记并落库 */
  {
    const w = await boot(null);
    answerAllCorrect(w);
    listen(w, 0.95, true);
    out.complete = {
      status: status(w),
      storage: stored(w),
      id: articleId(w),
    };
    w.close();
  }

  /* 5b. 顺序反过来（先听完、再答题）同样要打勾 */
  {
    const w = await boot(null);
    listen(w, 0.95, true);
    const before = stored(w);
    answerAllCorrect(w);
    out.listen_then_quiz = {
      beforeQuiz: before,
      status: status(w),
      storage: stored(w),
    };
    w.close();
  }

  /* 6. 已标记的页面再打开 ⇒ 直接显示已完成 */
  {
    const w = await boot(JSON.stringify({
      schemaVersion: 1,
      completedArticles: [PAGE_ID],
      updatedAt: '2026-10-19T00:00:00.000Z',
    }));
    out.reopen_done = { status: status(w), storage: stored(w) };
    w.close();
  }

  /* 7. 标记完成后再改答案 ⇒ 不自动取消（撤销权留给用户） */
  {
    const w = await boot(null);
    answerAllCorrect(w);
    listen(w, 0.96, true);
    const before = stored(w);
    const firstChoice = w.document.querySelector('.question[data-type="choice"] input[type="radio"]');
    if (firstChoice) {
      firstChoice.checked = true;
      firstChoice.dispatchEvent(new w.Event('change', { bubbles: true }));
      firstChoice.closest('.question').querySelector('[data-action="check"]').click();
    }
    out.change_after_done = {
      status: status(w),
      before: before,
      after: stored(w),
    };
    w.close();
  }

  /* 8. 已有别的记录 ⇒ 自动标记是并集，不覆盖别人的勾 */
  {
    const seed = JSON.stringify({
      schemaVersion: 1,
      completedArticles: ['0002', '0003'],
      updatedAt: '2026-10-19T00:00:00.000Z',
    });
    const w = await boot(seed);
    answerAllCorrect(w);
    listen(w, 1, true);
    out.union_with_existing = { storage: stored(w), id: articleId(w) };
    w.close();
  }

  /* 9. 存储里是坏数据 ⇒ 先留档再重置，本次标记照样写进去 */
  {
    const w = await boot('{oops');
    answerAllCorrect(w);
    listen(w, 1, true);
    out.corrupt = {
      status: status(w),
      storage: stored(w),
      backup: w.localStorage.getItem(KEY + '__corrupt'),
    };
    w.close();
  }

  /* 10. 本地存储不可用 ⇒ 条件满足但要明说「没保存」 */
  {
    const w = await boot(null);
    w.Storage.prototype.setItem = function () {
      throw new Error('denied');
    };
    answerAllCorrect(w);
    listen(w, 1, true);
    out.storage_unavailable = { status: status(w) };
    w.close();
  }

  console.log(JSON.stringify(out));
})().catch(function (err) {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
