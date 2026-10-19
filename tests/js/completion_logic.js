/* ==========================================================================
   DailyLingo — 自动完成判定的纯逻辑测试（Node，无 DOM）
   用法：node completion_logic.js <audio-player.js> <study-completion.js>
   输出：一行 JSON，供 tests/test_auto_complete.py 断言。

   两个脚本在没有 document 的环境里只导出纯逻辑（addListenStep / shouldComplete），
   不绑定任何事件，所以可以直接在 vm 里跑。
   ========================================================================== */

'use strict';

const fs = require('fs');
const vm = require('vm');

const playerSource = fs.readFileSync(process.argv[2], 'utf8');
const completionSource = fs.readFileSync(process.argv[3], 'utf8');

const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(playerSource, sandbox);
vm.runInContext(completionSource, sandbox);

const P = sandbox.DailyLingoPlayer;
const C = sandbox.DailyLingoCompletion;

if (!P || !C) {
  console.error('缺少导出：DailyLingoPlayer / DailyLingoCompletion');
  process.exit(1);
}

const limit = P.LISTEN_STEP_LIMIT;
const quiz = (total, correct) => ({
  total: total,
  correct: correct,
  answered: correct,
  allCorrect: total > 0 && correct === total,
});

const out = {
  contract: {
    rates: P.RATES,
    listenEvent: P.LISTEN_EVENT,
    quizEvent: C.QUIZ_EVENT,
    listenEventMatchesPlayer: P.LISTEN_EVENT === C.LISTEN_EVENT,
    stepLimit: limit,
    requiredRatio: C.REQUIRED_RATIO,
  },
  steps: {
    firstTick: P.addListenStep(0, null, 1.0, limit),      // 只记基准，不加
    normal: P.addListenStep(0, 1.0, 1.25, limit),          // 正常 0.25 s ⇒ 累加
    exactLimit: P.addListenStep(0, 0, limit, limit),       // 恰好等于上限 ⇒ 累加
    seekForward: P.addListenStep(3.0, 1.0, 40.0, limit),   // 拖到中间 ⇒ 丢弃
    seekBackward: P.addListenStep(3.0, 5.0, 2.0, limit),   // 后退跳转 ⇒ 丢弃
    frozen: P.addListenStep(3.0, 5.0, 5.0, limit),         // 时间没动 ⇒ 不加
  },
  cases: {
    emptyQuiz: C.shouldComplete(1, quiz(0, 0)),
    noQuiz: C.shouldComplete(1, null),
    belowThreshold: C.shouldComplete(0.89, quiz(3, 3)),
    atThreshold: C.shouldComplete(0.9, quiz(3, 3)),
    complete: C.shouldComplete(0.97, quiz(3, 3)),
    notAllCorrect: C.shouldComplete(1, quiz(3, 2)),
    partialAnswers: C.shouldComplete(1, quiz(5, 0)),
  },
};

console.log(JSON.stringify(out));
