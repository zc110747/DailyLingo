/* ==========================================================================
   DailyLingo — 朗读高亮的真实 DOM 测试（jsdom）
   用法：node player_dom.js <article.html> <audio-player.js>
   输出：一行 JSON，形如 {"sentenceCount": 3, "at05": 0, ...}

   音频用替身（jsdom 不解码 WAV、也不能真的出声）：只记录事件监听，
   由测试手动推进 currentTime 并派发 timeupdate，验证「高亮跟着时间走」。

   jsdom 只是开发期的临时依赖（不随站点发布）；tests/test_player_dom.py 找不到
   jsdom 时会自动跳过本脚本对应的测试，因此 pytest 仍可在纯净环境跑通。
   ========================================================================== */

'use strict';

const fs = require('fs');
const { JSDOM } = require('jsdom');

const PAGE = process.argv[2];
const SCRIPT = process.argv[3];
const html = fs.readFileSync(PAGE, 'utf8');
const source = fs.readFileSync(SCRIPT, 'utf8');

const out = { errors: [] };
/* 记录 scrollIntoView 调用：用来验证「页面语音跟随」开关真的在管滚动 */
const scrollLog = [];

function fakeAudio() {
  const listeners = {};
  const audio = {
    currentTime: 0,
    duration: 0,
    paused: true,
    ended: false,
    volume: 1,
    playbackRate: 1,
    preload: '',
    src: '',
    buffered: { length: 0, end: function () { return 0; } },
    addEventListener: function (type, fn) {
      (listeners[type] = listeners[type] || []).push(fn);
    },
    removeEventListener: function () {},
    play: function () {
      audio.paused = false;
      emit('play');
      return Promise.resolve();
    },
    pause: function () {
      audio.paused = true;
      emit('pause');
    }
  };

  function emit(type) {
    (listeners[type] || []).forEach(function (fn) {
      try {
        fn({ type: type });
      } catch (err) {
        out.errors.push(type + ': ' + err.message);
      }
    });
  }

  audio.emit = emit;
  return audio;
}

async function boot() {
  const dom = new JSDOM(html, {
    url: 'https://example.test/src/page.html',
    runScripts: 'outside-only'
  });
  const w = dom.window;
  const audio = fakeAudio();
  w.Audio = function () {
    return audio;
  };
  // jsdom 不实现滚动：自己记一笔，方便断言「有没有滚」
  w.Element.prototype.scrollIntoView = function () {
    scrollLog.push(this.getAttribute('data-start'));
  };
  w.eval(source);
  // 真实浏览器里 audio-player.js 以 defer 执行：解析完成、load 之前
  await new Promise(function (resolve) {
    if (w.document.readyState === 'complete') {
      resolve();
    } else {
      w.addEventListener('load', resolve);
    }
  });
  return { w: w, audio: audio };
}

function activeIndex(w) {
  const spans = Array.prototype.slice.call(w.document.querySelectorAll('[data-start]'));
  const active = w.document.querySelector('.sentence.is-active');
  return active ? spans.indexOf(active) : -1;
}

(async function () {
  const env = await boot();
  const w = env.w;
  const audio = env.audio;
  const spans = Array.prototype.slice.call(w.document.querySelectorAll('[data-start]'));

  out.sentenceCount = spans.length;
  out.beforePlay = activeIndex(w); // 播放前不应有任何高亮

  audio.duration = parseFloat(spans[spans.length - 1].getAttribute('data-end'));
  audio.emit('loadedmetadata');

  // 播放中：时间推进 → 高亮跟着走
  audio.paused = false;
  audio.currentTime = 0.5;
  audio.emit('timeupdate');
  out.at05 = activeIndex(w);
  audio.currentTime = 2.0;
  audio.emit('timeupdate');
  out.at20 = activeIndex(w);
  audio.currentTime = 4.0;
  audio.emit('timeupdate');
  out.at40 = activeIndex(w);
  out.beforePlayStillNone = out.beforePlay === -1;

  // 点句子 → 从该句开头播放（这就是「联动」的另一半）
  spans[2].dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  out.afterClick = { time: audio.currentTime, active: activeIndex(w) };
  out.clickStart = parseFloat(spans[2].getAttribute('data-start'));
  out.clickedAndPlaying = audio.paused === false;

  // 选中文字后点击不应跳转（否则想复制一段就变成跳转）
  const before = audio.currentTime;
  w.getSelection = function () {
    return { toString: function () { return 'selected text'; } };
  };
  spans[0].dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  out.selectionGuard = { time: audio.currentTime, unchanged: audio.currentTime === before };
  delete w.getSelection;

  // 键盘快退（进度条聚焦时 ←）：高亮要跟着回退，不能留在旧句子
  const track = w.document.querySelector('[data-action="seek"]');
  track.focus();
  const backBefore = audio.currentTime;
  track.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
  out.seekBack = {
    before: backBefore,
    after: audio.currentTime,
    active: activeIndex(w)
  };

  // 高亮只应有一个
  out.activeCount = w.document.querySelectorAll('.sentence.is-active').length;

  /* 「页面语音跟随」：上面所有时间推进都没开过开关（main.js 未加载 ⇒ 视为关闭），
     因此一次都不该滚动；把开关置为开启后才允许滚，再关掉又要停。 */
  out.scrollWhileDefault = scrollLog.length;
  w.DailyLingo = { readingFollow: { enabled: function () { return true; } } };
  audio.currentTime = 2.0; // 换到第 2 句（此时当前句还停在第 1 句）
  audio.emit('timeupdate');
  out.scrollAfterEnable = {
    calls: scrollLog.length,
    last: scrollLog[scrollLog.length - 1]
  };
  w.DailyLingo = { readingFollow: { enabled: function () { return false; } } };
  audio.currentTime = 4.0;
  audio.emit('timeupdate');
  out.scrollAfterDisable = scrollLog.length;
  out.highlightStillFollows = activeIndex(w);

  process.stdout.write(JSON.stringify(out));
})();
