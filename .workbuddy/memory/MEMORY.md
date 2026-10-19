# DailyLingo — 项目长期记忆

> 每次会话先读这里；细节看 `YYYY-MM-DD.md` 日志。

## 项目定位
纯静态英语学习站（无后端 / DB / 远程 API），部署在 GitHub Pages **项目子路径**
`https://zc110747.github.io/DailyLingo/`。只用 HTML/CSS/原生 JS 不引框架；构建与验证
**只用 Python 标准库**（pytest 仅服务测试）。经验已沉淀 4 个全局 skill：`web-static-site-pipeline` /
`web-local-progress-store` / `app-webview-shell` / `android-apk-no-gradle`。

## 目录职责
`content/*.md` 是唯一维护源；`index.html` + `src/*.html` 由构建生成、**必须提交**（Pages 以仓库根为
站点根）；`sources/*.wav` 由外部 TTS 写；`assets/`、`scripts/{build,validate,watch,timeline}.py`、
`tests/`、`watch.bat`（纯 ASCII + CRLF，每条退出路径 pause）可手改；`tools/`（EnglishAudio）gitignore。

## 文档约定
`README.md` 英文（默认）+ `README-CH.md` 中文，**两份同步、结构对齐**（H2 数一致），顶/底互链；
改标题顺带看 `.gitignore` 与 `tests/` 里指向 README 的注释。
**凡随文章数线性增长的列举一律省略**：只留第一条 + `…`（判据：会不会随篇数变长）。

## 硬约定
1. 编号 = 永久 ID：四位补零、超四位不截断；`NNNN.Title_With_Underscores.md`；编号 / 文件名 /
   front matter `id` 三者必须一致，否则构建报错。
2. **文件名只用 ASCII，无空格无标点**（同时是 URL 片段与音频名）：撇号会引出 percent-encoding、
   git 引号、HTML 转义三层麻烦。改名配套：`git mv` → 改 H1 → 改相邻 `## Continue` →
   重生成 WAV → 删旧 WAV/HTML → 重建。
3. 标题统一 `build.display_title()`（`NNNN. 原标题`）；标签页加 `| DailyLingo`。
4. Chapter 每 100 号一组（`((n-1)//100)*100+1`）；只输出有文章的组，首组 `<details open>`。
5. 文章页五区固定顺序：Article / Words / Questions / Answers / Continue；Answers 默认折叠，
   判分数据内嵌 `#quiz-data`（与 Answers 同源）。
6. 全站相对路径，**禁止 `href="/…"`**；validate 会失败。
7. 构建不生成音频、不调 TTS、不转码；缺 WAV 只警告。
8. 构建可复现：输入不变 ⇒ 字节级一致（validate 重建到临时目录比对）。
9. 已删文章的旧 `src/*.html` **不自动清理**（不删文件原则），人工删；watch 只提示。
10. 改 md 不用手敲构建：`watch.py` / `watch.bat` 1 s 内**全量**重建（新增/删除会改相邻导航，
    不做单页增量）；md 写坏只报错不退出；`--audio` 顺带补缺。
11. **改了 `## Article` 就必须重生成同名 WAV**；`--audio` 只补**缺失**，不检测内容过期。
12. 删除 / 改名要手删旧 WAV 与 `src/*.html`；编号**永不**随标题变化。
13. Article 区内顺序：`<h2>` → 播放器 → `<hr class="player-divider">` → 正文；播放器 `sticky; top: 8px`
    吸顶（不想要就删）。validate 断言该顺序（有/无 WAV）。
14. 图标是**静态资产随仓库提交**：`assets/images/favicon.svg`（设计源）+ `-32` / `-180.png`；
    `build._render_icons(prefix)` 输出三条 link + `theme-color`（首页前缀 `""`、文章页 `"../"`）。
    改图标要重写光栅化脚本（标准库手写 PNG + 超采样）。
15. 播放器是紧凑款，**控件刻意做减法（别加回）**：无 ±5 s；倍速只 0.75 / 1 / 1.25；进度条 5 px，
    靠 `.player-track::before`（18 px）把命中区撑到 ±9 px（实测 ±7 有效、±11 无效）；
    控件行「音量在左、倍速 `margin-left:auto`」。
16. **`flex-basis` 不写 px**：容器翻成 `column` 后它就是「高度」。`.nav-link` 已改 `flex: 1 1 0;
    min-width: 200px`（竖排靠默认 `min-height: auto`）。`%` 与 `auto` 无此问题。
17. **CSS / JS 的 URL 必带 `?v=<sha256 前 8 位>`**（`build.asset_url`）。Pages 回 `max-age=600`，
    只改内容不改 URL ⇒ 手机最长 10 分钟吃旧文件（已误判「修复没生效」一次）；HTML 自身也有该缓存。
    断言用 `build.asset_url()`，别写死路径；诊断 `curl -D -` 看 `Last-Modified` 与字节数。

## Markdown 格式（两种可混用）
- 既有：`# 标题` + `## Article` / `## Words`（3 或 5 列，表头按别名识别）/ `## Questions`
  （`**题干**` 或 `Question N：题干` + `A. …`）/ `## Answers` / `## Continue(s)`（忽略）。
- 扩展：front matter（`id`/`title`/`audio`）+ `## Q1` + `题型：单选|填空` + `答案：` / `可接受答案：` / `解释：`。
- **答案四种写法可混用**：① 紧凑串 `BAC`；② `Question5: …`；③ 分块；④ 编号列表 `1. **B. …** 解释`。
  ④ 的序号点常被转义成 `1\.`（CommonMark 里等价），正则写 `\\?`，**别全局删反斜杠**；题干同理。
- `extract_choice_key()` 判据严格（`cook` 不会读成 `C`）；题干 `______` 是内容，不得当强调处理。

## 音频链路
WAV 由 **EnglishAudio**（Piper + ONNX，离线）生成。**工具在 PATH，不记绝对路径**（写死换机即失效，
坏过两次）。定位顺序：`--audio-tool` > `DAILYLINGO_AUDIO_TOOL` > PATH 按名字（`eaudio.cmd` /
`EnglishAudio.exe`）> `tools/eaudio.cmd`；报「找不到」先 `command -v`。只读 `## Article`，输出同名
WAV；正文含非英文被拒（退出码 4）；md 必须 UTF-8。WAV 均单声道 / 16 bit / 22 050 Hz。

## 文章清单
**0001–0022 共 22 篇**，全在 Chapter 0001–0100，不逐篇罗列。
改名史：`0005` 撞名、`0016` 去撇号、`0018` 笔误 `fro`→`from`、`0021` 去弯撇号（`Bee’s`→`Bees`，
H1 保留弯引号）。

## 首页学习进度（纯前端）
- `build.render_index()` 输出 `.site-tools`（齿轮 → `#settings-dialog`）、`.progress-card`（`data-progress-*`）、
  `li.article-item[data-article-id]` + `[aria-pressed]`、`[data-chapter-*]`；空心圆 / 绿勾**同时在 DOM 里**，
  靠属性切显隐（JS 只改属性，不重建节点）。
- `progress.js`：键 `dailylingo_learning_progress_v1`、`schemaVersion: 1`、ID 用**四位补零字符串**
  （永不拿标题当身份）；坏数据备份 `…__corrupt` 后重置；存储不可用走内存态；导出 / 导入 JSON（4 键，
  导入先预览再并集或覆盖，**覆盖二次确认**）；纯逻辑挂 `globalThis.DailyLingoProgress`，无 document 早退。
- ⚠️ jsdom 测真 DOM 必须 `runScripts:"outside-only"`（否则 `window.eval` 静默不执行），等 `load` 再点
  （defer 脚本在 DOMContentLoaded 前跑）。**jsdom 会被环境清掉**：曾整组 skip 仍"全绿"；node workspace
  `npm install jsdom` 即恢复，跑完应 **225 passed**。
- ✅ headless Chromium 可用（playwright + 本机 chromium，`file://` 直开量尺寸/截图/发 pointer）：
  `NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules`。⚠️ 别用 `msedge --dump-dom` 判可用（假成功）。

## 桌面端 / Android 端（apps/）
两端都加载线上站点：启动页 → 探网 → **导航成功才**显示网页，离线/超时进错误菜单；进度镜像成
`dailylingo-progress.json`（与网页导出同构；**Android 写 LF，Windows 因 .NET 9 默认写 CRLF**）。
`windows/` = WinForms + WebView2；`android/` = 系统 WebView，**无 Gradle / AndroidX / Material**，
构建 `python tools/build_apk.py`（aapt2 + javac + d8 + zipalign + apksigner，只用标准库；SDK 读
`ANDROID_SDK_ROOT`、JDK 读 `JAVA_HOME` 或 Studio 的 `jbr`）。细节见各自 README。
⚠️ Android 三坑：`WindowInsetsController` 要在 `setContentView` **之后**取（否则 NPE）；隐藏 WebView 用
**GONE**（`INVISIBLE` 仍合成、盖住启动页）；图标用 favicon 整图，别拆 adaptive icon／垫白底。
`adb install` 被拒先看是否息屏。

设置面板末尾「手机应用」= 安装包直链（`build.render_app_download()`）：`apps/android/publisher/
DailyLingo.apk?v=<sha8>` + `download`；**APK 缺失整块省略**。

## 朗读高亮（音频 ↔ 网页联动）
正文按句包 `<span class="sentence" data-start data-end>`（无时间轴退回纯 `<p>`），当前句 `is-active`
（加粗 + 淡蓝底）。时间轴由 **`scripts/timeline.py`** 在**构建期**从 WAV 反推（TTS 无时间戳）：
帧峰值包络 → ≥100 ms 静音段 → DP 按「每句**有声时长** ∝ 音节数」挑 N-1 个边界。
四条铁律（实测踩出来的，改算法前先读文件注释）：**候选只能是停顿中心**（网格点会让一次长停顿
吞出空句）；**代价按每段算**（累计偏差允许某句被压扁）；**用有声时长不用墙钟**；**引号 + ≤6 词
叙述语并成一句**（中间无停顿，硬切会整体错位）。
前端：`renderProgress()` 里统一 `tracker.sync(audio.currentTime)` —— 播放/拖动/←→/点句子共用一条路径；
播放前不高亮（`armed` 标志）。缓存键 (size, mtime_ns, hash(句子))，热构建 0.09 s。

## 已验证 / 踩坑
- 2026-10-19 全绿：22 篇 / validate 949 / pytest 229 / Android 真机三态 / 朗读高亮 `a63c2f3`。
- **validate 三档倍速断言必须分支**：无 WAV 的页只有 `player-unavailable`，无条件查得 `rates=[]` 假
  FAIL。有 `data-player` 才查 `0.75/1/1.25` 且无 `back/forward`。⚠️ 别用 `'data-action=' not in html`
  判「无控件」——题目区 Check/Reset 也带它。
- **行尾**：`.gitattributes` 设 `* text=auto eol=lf` / `*.bat eol=crlf` / 二进制 `binary`；
  `git ls-files --eol` 只应剩 `watch.bat` 是 CRLF。⚠️ `asset_version()` 算磁盘字节，行尾一变全站
  `?v=` 全变。⚠️ **绝不 `git checkout -- content/`**，要逐个 `git add` → `rm` → checkout。
- **本地 `http.server` 不支持 Range**（仍 200）；线上 Pages 是 **206**，拖动跳转只能对线上验证。
  改 `assets/` 后**必须重跑构建**（否则 `?v=` 落后）；一次性脚本放 `.workbuddy/tmp/`（gitignore）。
