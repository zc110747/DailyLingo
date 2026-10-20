# DailyLingo — 项目长期记忆

> 每次会话先读这里；细节看 `YYYY-MM-DD.md` 日志。

## 定位与布局
纯静态英语学习站（无后端/DB/远程 API），GitHub Pages 项目子路径
`https://zc110747.github.io/DailyLingo/`；只用 HTML/CSS/原生 JS；构建与校验**只用 Python 标准库**。
`content/*.md` 是唯一源；`index.html` + `src/*.html` 由构建生成且**必须提交**（Pages 以仓库根为站点根）；
`sources/*.wav` 由外部 TTS 写；`assets/`、`scripts/{build,validate,watch,timeline}.py`、`tests/` 可手改。
`README.md`（英，默认）+ `README-CH.md`（中）**必须同步、H2 数相等**；凡随篇数线性增长的列举一律
「第一条 + `…`」并注明省略。

## 硬约定（违反会直接报错或线上出问题）
1. 编号=永久 ID：四位补零、超四位不截断；`NNNN.Title_With_Underscores.md`；编号/文件名/front matter 三者一致。
2. **文件名只用 ASCII，无空格无标点**（同时是 URL 片段与音频名；`'`/`’` 会引出三层转义）。
   改名配套：改 H1 → 改相邻 `## Continue` → 重生成 WAV → 删旧 WAV/HTML → 重建。
3. 标题统一 `build.display_title()`；Chapter **每 25 篇一组**（`CHUNK = 25`），只输出有文章的组，
   首组 `<details open>`；每章 summary 有**自己独立的进度条**（`data-chapter-bar/fill`），
   分母取 `data-chapter-total`（该章实际篇数），progress.js 逐章更新、互不影响。
4. 文章页五区固定：Article / Words / Questions / Answers / Continue；Answers 默认折叠；判分数据内嵌 `#quiz-data`（与 Answers 同源）。
5. Article 区内：`<h2>` → 播放器 → `<hr class="player-divider">` → 正文；播放器 `sticky top:8px`。
6. 全站相对路径，禁止 `/…` 开头；`validate.py` 断言。
7. 构建不生成音频/不调 TTS；缺 WAV 只警告。**改了 `## Article` 必须重生成同名 WAV**（`--audio` 只补缺失）。
8. 输入不变 ⇒ 输出字节级一致（validate 重建到临时目录比对）。
9. 构建**不删文件**：改名/删除要手删旧 `src/*.html` 与 `sources/*.wav`；`watch.py` 只提示。
10. 改 md 不用手敲构建：`watch.py` / `watch.bat` 1 s 内全量重建（新增会改相邻导航，不做增量）。
11. **CSS/JS URL 必带 `?v=<sha256 前 8 位>`**（`build.asset_url`）。Pages 回 `max-age=600`：改 `assets/`
    不重建 ⇒ 手机最长 10 分钟吃旧文件。**改 assets 后必须重跑构建**；改行尾也会让全站指纹变（按磁盘字节算）。
12. 播放器控件刻意做减法：无 ±5 s；倍速只 0.75/1/1.25；进度条 5 px，命中区靠 `.player-track::before` 撑到 ±9 px。
13. `flex-basis` 不写 px（翻成 column 就是高度）；`.nav-link` 用 `flex: 1 1 0; min-width: 200px`。
14. 图标是静态资产（`favicon.svg` + `-32`/`-180.png`），各页由 `build._render_icons(prefix)` 声明。
15. 行尾：`.gitattributes` = `* text=auto eol=lf` / `*.bat eol=crlf` / 二进制 `binary`；
    `git ls-files --eol` 只应剩 `watch.bat` 是 CRLF。⚠️ **绝不 `git checkout -- <目录>`**（会吞掉别处的
    未暂存改动），要逐文件 `git add` → `rm` → `checkout -- <文件>`。

## Markdown 格式（两种可混用）
- 既有：`# 标题` + `## Article` / `## Words`（3 或 5 列，表头别名含 `IPA`）/ `## Questions`
  （`**题干**` 或 `Question N：` + `A. …`）/ `## Answers` / `## Continue(s)`（忽略）。
- 扩展：front matter（`id`/`title`/`audio`）+ `## Q1` + `题型：单选|填空` + `答案：`/`可接受答案：`/`解释：`。
- 答案四种写法：① 紧凑串 `BAC`；② `Question5: …`；③ 分块；④ 编号列表 `1. **B. …** 解释`
  （序号点常被转义成 `1\.`，正则写 `\\?`，别全局删反斜杠）。
- `extract_choice_key()` 判据严格（`cook` 不是 `C`）；题干 `______` 是内容，不当强调。

## 音频
WAV 由 **EnglishAudio**（Piper+ONNX，离线）生成，**工具在 PATH，不记绝对路径**（写死坏过两次）。
定位：`--audio-tool` > `DAILYLINGO_AUDIO_TOOL` > PATH（`eaudio.cmd`/`EnglishAudio.exe`）> `tools/eaudio.cmd`。
只读 `## Article`；正文含中文被拒（exit 4）；弯引号 `“ ” ’` **不拦**。WAV 均单声道/16 bit/22 050 Hz。
⚠️ **`009.ai_voice/publisher/` 里的 exe 会过期**：runtimeconfig 仍是 `net10.0`，本机只有 7/8/9 时
直接跑只吐 `You must install or update .NET…` 然后 exit 1（在 bash 里是**空输出 + 立即结束**，
别误判成被沙箱杀）。正解 `dotnet build src/EnglishAudio/EnglishAudio.csproj -c Release`，
跑 `src/EnglishAudio/bin/Release/net9.0-windows/EnglishAudio.exe <md> --dist=sources`
（AppPaths 向上找 `tools/piper`，必须在仓库树内）。另：本机 `HTTPS_PROXY`/`https_proxy` 同时存在，
PS 的 `Start-Process` 会抛「关键字重复」，别用它启动。

## 学习进度（纯前端，两处写入）
- 存储 `localStorage["dailylingo_learning_progress_v1"]` = `{schemaVersion:1, completedArticles:["0001"], updatedAt}`；
  ID 用**四位补零字符串**，永不拿标题当身份；坏数据备份 `…__corrupt` 后重置；存储不可用走内存态。
- `progress.js`：首页（勾选/统计/Chapter 汇总/导入导出/设置对话框）+ 对外写接口 `markCompleted(id)` /
  `isCompleted(id)` / `readCompleted()`；纯逻辑挂 `globalThis.DailyLingoProgress`。
  Chapter 汇总分母取 `data-chapter-total`（实际篇数，不假定 25）；每章自己的进度条
  `data-chapter-bar/fill` 按本章比例更新，跨章互不影响。
- `study-completion.js`（文章页）：`dailylingo:listen`(播放器) + `dailylingo:quiz`(main.js) ⇒
  **听够 ≥90% 且全答对** 才 `markCompleted`；**只增不减**（撤销权留首页手动开关）；无音频/无题目时
  `data-study-auto="false"`，页面直说只能手动勾。
- 播放器累计：`timeupdate` 累加**媒体秒**，单步 >1.5 s 视为跳转丢弃（拖到结尾刷不出完成）；
  倍率无关。阈值是单常量 `REQUIRED_RATIO` / `LISTEN_STEP_LIMIT`，validate 断言 0.9。
- ⚠️ jsdom 测真 DOM 必须 `runScripts:"outside-only"`（否则 `window.eval` 静默不执行），并等 `load` 再点。
  jsdom 属开发期依赖，缺了整组 skip；node workspace `npm install jsdom` 可恢复。
- ⚠️ 本机**当前**没有可用浏览器/playwright（`msedge --version` 假成功），像素未验证；音频真实播放未验证。

## 其它模块
- 朗读高亮：正文按句 `<span class="sentence" data-start data-end>`，时间轴由 `scripts/timeline.py` 构建期
  从 WAV 反推（帧峰值 → 静音段 → DP 按音节数挑边界）。四条铁律见文件注释（候选只能是停顿中心、
  代价按每段算、用有声时长、引号+≤6 词叙述语并一句）。
- `apps/`：Windows WinForms+WebView2 / Android 系统 WebView（无 Gradle），均加载线上站点；
  进度镜像成 `dailylingo-progress.json`（Android 写 LF，Windows .NET 9 默认 CRLF）。
  ⚠️ Android：`WindowInsetsController` 要在 `setContentView` 之后取；隐藏 WebView 用 **GONE**。

## 已验证（2026-10-20，29 篇）
`build.py` **29 篇 / 2 Chapter（0001–0025 满章 + 0026–0050 共 4 篇）/ 0 警告**；`validate.py`
**PASS 1366**；`pytest -q` **274 passed**；全量重建冷 0.84 s / 时间轴缓存命中 0.38 s。
文章改名史：0005 撞名、0016 去撇号、0018 笔误、0021 去弯撇号、0029 去文件名空格、
0029/0030 编号写错重排为 0028/0029（H1 均保留排版符号）。**编号即身份**：改编号必须同步
md 文件名 + 相邻 Continues + 重生成同名 WAV + 手工删旧 `src/*.html`（构建不删文件）。
`## Continue(s)` 段由构建忽略，但 md 里仍需自洽：previous/next 按**编号相邻**、缺号不跳空，
目录写 `../index.html`（仓库无 `catalogue.md`）。
