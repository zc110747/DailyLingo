# DailyLingo — 项目长期记忆

> 每次会话开始读这里；细节看 `YYYY-MM-DD.md` 日志。

## 项目定位
纯静态英语学习网站（无后端 / 无数据库 / 无远程 API），部署到 GitHub Pages **项目子路径**
`https://zc110747.github.io/DailyLingo/`。前端只用 HTML/CSS/原生 JS，不引入框架。
构建与验证脚本**只使用 Python 标准库**；`requirements.txt` 里的 pytest 只服务测试。

## 目录与职责边界（不要越界）
| 目录 | 定位 | 可手工改 |
|---|---|---|
| `content/*.md` | 文章唯一维护源 | 是 |
| `src/*.html`、`index.html` | 构建生成 | 否（重新构建即覆盖） |
| `sources/*.wav` | 外部音频工具生成 | 由工具写入 |
| `assets/` | 全站 CSS / JS | 是 |
| `assets/images/` | 站点图标 `favicon.svg` / `-32.png` / `-180.png`（**静态资产，原样提交**） | 是 |
| `scripts/build.py` | 构建 | 是 |
| `scripts/watch.py` | md/wav 变化后自动重建（同步机制） | 是 |
| `scripts/validate.py` | 验证 | 是 |
| `watch.bat` | Windows 双击即监听（纯 ASCII + CRLF，每条退出路径 pause） | 是 |
| `tests/` | pytest（`tests/test_build.py` + `tests/test_frontend.py`） | 是 |
| `tools/` | EnglishAudio 打包产物（约 100 MB）——**已 gitignore，不进仓库** | 由外部维护 |

生成物（`index.html`、`src/*.html`）**必须提交**，Pages 以仓库根为站点根。

## 文档语言约定
**`README.md` 是英文（默认），`README-CH.md` 是简体中文**，两份内容必须**同步维护**、
结构对齐；顶部与底部都有 `[English](README.md) | [简体中文](README-CH.md)` 切换链接。
改任一份都要同步改另一份；改章节标题后记得顺手更新 `.gitignore` 与
`tests/test_frontend.py` 里指向 README 章节的注释。

### README 里「按文件逐条列举」一律省略
文章量目标是**几千篇**，所以 README 中凡是逐篇罗列文件/标题/路径的地方（目录树、
首页目录示例、WAV 参数表、`build.py --verbose` 输出、`http.server` 清单），
**只保留第一条 + `…`**，并在块后加一句 *（abridged / 做了省略）* 说明。
不允许再写成全量清单——文章一多就臃肿得没法读。
判据：只要那段内容会随文章数线性增长，就必须省略。
（历史叙述、单个示例命令、编号规则的通用示例不在此列，可保留。）

## 硬约定
1. 编号是永久 ID：四位补零，超过四位不截断；文件名 = `NNNN.Title_With_Underscores.md`，
   **文件名里不要有空格**（否则 `sources/` 音频名、页面链接、`href` 三处对不上）；
   编号、文件名、front matter `id` 三者必须一致，否则构建报错。
2. **文件名只用 ASCII，不要含撇号 / 引号 / 空格等标点**：文件名同时是 URL 片段与音频文件名，
   U+2019 这类弯引号会多出 percent-encoding、git 引号、HTML 属性转义（`esc()` 把 `'` 变
   `&#x27;`）三层麻烦。先例：`0006.A_Visit_to_the Library.md` → 下划线；
   `0016.Grandma’s_Secret_Recipe.md` → `0016.Grandmas_Secret_Recipe.md`（H1 保留排版撇号）。
   改名后记得：改相邻文章 `## Continue` 交叉引用 → 删旧 WAV → 用新名字重新生成 → **删旧 HTML**。
3. 显示标题统一由 `build.display_title()` 生成：`NNNN. 原始标题`；浏览器标签加 `| DailyLingo`。
   首页 / 文章页 / 标签 / 上下篇导航共用同一函数。
4. Chapter 固定 100 号一段：`start = ((n-1)//100)*100 + 1`；**只输出含真实文章的 Chapter**，
   第一组默认展开（`<details open>`），其余折叠。
5. 文章页固定五个区域，顺序不可变：Article / Words / Questions / Answers / Continue。
   Answers 用 `<details>` 默认折叠；判分答案内嵌在 `#quiz-data`，与 Answers 同源。
6. 全站相对路径，**禁止 `href="/…"` / `src="/…"`**；`validate.py` 会失败。
7. 构建脚本不生成音频、不调 TTS、不转码；单篇缺 WAV 只警告，其他页面照常构建。
8. 构建必须可复现：输入不变时输出字节级一致（validate.py 会重构建到临时目录逐字节比对）。
9. `src/` 中已删除文章的历史 HTML **不会自动清理**（不删文件原则），需人工删；
   `watch.py` 只提示遗留页面，同样不删。
10. **改 md 后不必手动敲构建**：`python scripts/watch.py`（或双击 `watch.bat`）会在 1 s 内
   全量重建。全量而非单页增量 —— 新增/删除文章会改动相邻文章的上下篇导航。
   md 写坏时只报错并继续监听；`--audio` 会顺带补齐缺失 WAV。
11. **改了 `## Article` 正文就必须重新生成同名 WAV**（`sources/` 里那份会过期）；
    `watch.py --audio` 只在**缺文件**时补，不检测内容过期，需人工重跑 EnglishAudio。
12. **改名/删除文章要手删旧产物**：`sources/<旧名>.wav` 与 `src/<旧名>.html`。
   构建脚本与 `watch.py` 都遵守「不删文件」，只会提示。
   改名的配套动作：`git mv content/...` → 改 H1 → 改相邻文章 `## Continues` 里的交叉引用
   → 重新生成 WAV → 删旧产物 → 重新构建。编号**永不**随标题变化。
13. 文章页 Article 区内顺序为 **`<h2>Article</h2>` → 播放器 → `<hr class="player-divider">` → 正文段落**
    （诉求：先点开播放再读文字；分隔线由用户要求，上下各有 16 / 20 px 间距）。
    播放器另加 `.section-article .player { position: sticky; top: 8px }` 在阅读长文时吸顶，
    不想要吸顶删掉这条规则即可。`validate.py` 会断言顺序（有 / 无 WAV 两种情形都测）。
14. 站点图标是**静态资产、随仓库提交**（不是构建产物，删不掉也不用生成）：
    `assets/images/favicon.svg`（设计源，打开的书 + 声波）、`favicon-32.png`、`favicon-180.png`；
    由 `build._render_icons(prefix)` 在每页 head 声明三条 link + `<meta name="theme-color">`
    （首页前缀 `""`、文章页 `"../"`），`build.THEME_COLOR = "#3166a4"`；首页品牌名左侧另有
    `class="brand-icon"`。**PNG 的光栅化脚本是一次性的，已删除**——要改图标需重写一个
    （纯标准库手写 PNG 编码 + 超采样即可，几何与 SVG 保持一致）。
15. 播放器是「紧凑款」且**控件刻意做减法**（都是用户明确要求，别自行加回）：
    - 尺寸：卡片高实测 136 → 85.7 px（padding `12px 14px`，留白是用户后来的要求）；
      进度条视觉高 **5 px**，靠 `.player-track::before`（18 px 高、`top:50%` + `margin-top:-9px`）
      把可点区域撑到 **±9 px**（实测 ±7 px 有效、±11 px 无效）。伪元素不是独立事件目标，
      `event.currentTarget` 仍是 `.player-track`。
    - **无 ±5 秒按钮**（`data-action="back"/"forward"` 已删除，JS 里的绑定也删了）；
      跳转只靠点击 / 拖动进度条与键盘方向键（`←`/`→`）。
    - **倍速只有 0.75x / 1x / 1.25x** 三档（`RATES` 数组与页面按钮同步），1x 默认激活。
    - 控件行布局：`<label 音量>` 在前、`.player-rates` 在后靠 `margin-left: auto` 右对齐。
16. **`flex-basis` 不要写长度值（px）：容器一翻成竖排，它就变成「高度」。**
    `.nav-link/.nav-disabled` 原本是 `flex: 1 1 200px`，移动端 `.continue-nav` 翻成
    `flex-direction: column` 后每个标签被撑到 200px 高（实测 366×200）。
    **2026-10-16 已把共享规则直接改成 `flex: 1 1 0; min-width: 200px`**，媒体查询里那条
    `flex: 0 0 auto` 补丁已删除。横向排与原先逐像素一致（641/700/900px 实测 299.5 / 329 / 405）；
    竖排时靠 flex item 默认的 `min-height: auto` 回到内容高 **52.6px**。
    百分比（`1 1 60%`）与 `auto` 不踩这个坑；`.fill-input`（`1 1 220px`）的父 `.fill-row`
    是 row + wrap 且移动端不翻转，所以没问题。
17. **CSS / JS 的 URL 必须带内容指纹 `?v=<sha256 前 8 位>`**（`build.asset_version()` /
    `build.asset_url()` 生成，只按文件内容算 ⇒ 构建仍字节级可复现）。
    GitHub Pages 给这两个文件回 `Cache-Control: max-age=600`：只改内容不改 URL，手机端最长
    10 分钟还拿旧文件 —— 已把「已修好并部署」误判成「修复没生效」一次。HTML 自身也有
    10 分钟强缓存，所以改完样式手机上仍有 ≤10 分钟延迟，属 Pages 固有行为，不是构建问题。
    断言路径时用 `build.asset_url()`，别再写死 `assets/css/style.css`。
    诊断手法：`curl -D - <线上 css>` 看 `Last-Modified` + 本地/线上字节数比对。

## 本机预览
IDE 内置预览把 **文件所在目录**当站点根：`index.html`（仓库根）预览正常，而 `src/` 下的
文章页会丢样式（`../assets/…` 解析成 `/static-html/assets/…` → 404）。要看带样式的文章页，
用自包含副本 `.workbuddy/preview/`（`cp src/*.html` + `cp -r assets` + `cp sources/xx.wav sources/`，
再把 HTML 里的 `../` 全部去掉），该目录已 gitignore。**注意这是预览副本，不是交付物**。

## 文章 Markdown 格式
兼容两种，可混用：
- 既有格式（原本来自 `D:\user_project\git\DailyWork\english`，该目录**已不存在**，
  内容已并入本仓 `content/`）：`# 标题` + `## Article` / `## Words`
  （3 列或 5 列，表头按别名识别）/ `## Questions`（`**题干**` 或 `Question N：题干` + `A. …`）/
  `## Answers` / `## Continues`（被忽略，别名含单数 `Continue`）。
- 扩展格式：YAML front matter（`id` / `title` / `audio`）+ `## Q1` + `题型：单选|填空` +
  `答案：` / `可接受答案：` / `解释：`。
- **答案四种写法可混用**：① 紧凑字母串（`BAC`，按题目顺序）；② `Question5: …`；
  ③ 分块；④ 编号答案列表 `1. **B. To the library.** 解释文字`（粗体里的选项字母当答案，
  粗体后的文字当解释；填空题同样适用）。
  ④ 的序号点**允许被反斜杠转义**（`1\. **B. …**`）：编辑器为防自动有序列表常这么写，
  CommonMark 里 `\.` 就是字面句点，两种写法等价。题干同理（`1. 题干` / `1\. 题干`）。
  正则里写成 `\\?` 即可，别去全局删反斜杠。
- 选项字母提取走 `build.extract_choice_key()`，判据严格：`cook`/`bamboo` 不会被误判成 `C`/`B`。
- 题干里的 `______` 是内容，`strip_markdown` **不得**处理下划线强调。

## 音频链路
WAV 由 **EnglishAudio**（Piper + ONNX，离线）生成：
`E:\cnb\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd`（源仓库，已单独维护）。
> 2026-10-17：原兜底路径 `D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice\publisher\` 连同
> `D:\user_project` 整个目录已不存在，源仓库搬到了 **E 盘**（watch.py 的候选路径 + 两份 README
> 共 10 处已同步）。**发现「找不到 eaudio.cmd」时先确认这个路径，不要怀疑参数。**
`watch.py --audio` 的定位顺序：`--audio-tool` > `DAILYLINGO_AUDIO_TOOL` >
`<仓库>/tools/eaudio.cmd` > 上面那个 publisher 路径；都找不到只提示不中断。
只朗读 `## Article` 章节，输出与 md 同名的 WAV，正文含非英文会被拒绝（退出码 4），
md 必须是 UTF-8。本仓现有 16 个 WAV 均为单声道 / 16 bit / 22 050 Hz。
> **弯引号不拦**：`0010` 正文含 `“ ”`（U+201C/U+201D）照样合成成功（exit 0）——"含非英文就拒绝"
> 指的是中文字符等，排版标点没问题。**不用为此删引号**。
直接跑 `EnglishAudio.exe <md> --dist=sources`（`MSYS_NO_PATHCONV=1`，从仓库根执行）比走
`.cmd` 包装更省事：stdout 能正常看到它自己的 banner（含字数 / 时长 / 字节数 / RTF）。

## 文章清单（16 篇，全部在 Chapter 0001–0100）
| 编号 | 文件 | 标题 |
|---|---|---|
| 0001 | `0001.A_New_Hobby.md` | A New Hobby |
| 0002 | `0002.A_Busy_Morning.md` | A Busy Morning |
| 0003 | `0003.Helping_a_Neighbor.md` | Helping a Neighbor |
| 0004 | `0004.A_Day_at_the_Beach.md` | A Day at the Beach |
| 0005 | `0005.A_Day_on_the_Farm.md` | A Day on the Farm（原名 A Busy Morning，与 0002 撞名，已改） |
| 0006 | `0006.A_Visit_to_the_Library.md` | A Visit to the Library |
| 0007 | `0007.A_Day_at_the_Market.md` | A Day at the Market |
| 0008 | `0008.The_Blue_Planet.md` | The Blue Planet |
| 0009 | `0009.A_Little_Coffee_Shop.md` | A Little Coffee Shop |
| 0010 | `0010.The_Lost_Puppy.md` | The Lost Puppy |
| 0011 | `0011.The_School_Art_Show.md` | The School Art Show |
| 0012 | `0012.A_Message_from_the_Moon.md` | A Message from the Moon |
| 0013 | `0013.The_Little_Musician.md` | The Little Musician |
| 0014 | `0014.A_Strange_Fish_in_the_Sea.md` | A Strange Fish in the Sea |
| 0015 | `0015.The_Weekend_Football_Game.md` | The Weekend Football Game |
| 0016 | `0016.Grandmas_Secret_Recipe.md` | Grandma’s Secret Recipe（文件名去撇号，见下） |

> 0001–0005 已由用户手工把单词表表头改成 `Word | IPA | Meaning`、题干改成 `Question N：…`、
> Answers 改成**编号答案列表** `1\. **B. … ** 解释文字`（三种写法解析器都支持，只是写法统一了）。

## 首页学习进度（2026-10-17 新增，纯前端）
- 结构由 `build.render_index()` 生成：左上角 `.site-tools`（齿轮 → `<dialog id="settings-dialog">`）、
  `.progress-card`（`data-progress-done/total/percent/fill/bar`，SSR 兜底 0/总数/0%）、
  每篇 `li.article-item[data-article-id="NNNN"]` + `button.article-toggle
  [data-action="toggle-complete"][aria-pressed][aria-label]`、Chapter summary 内
  `[data-chapter-status][data-chapter-total]` + `[data-chapter-count]` + `[data-chapter-state]`。
- **两个图标（空心圆 / 绿勾）同时在 DOM 里**，靠 CSS `[aria-pressed="true"] > .toggle-icon-*` 与
  `.chapter-status.is-complete` 切显隐；JS 只改属性，不重建节点。
- `assets/js/progress.js` 契约：键 `dailylingo_learning_progress_v1`、`schemaVersion: 1`、
  ID 为**四位补零字符串**（`article.number_text`，永不把标题当身份）、`updatedAt` ISO。
  损坏数据先备份到 `…__corrupt` 再重置+提示；存储不可用则内存态继续可用。
  导出 `dailylingo-progress-YYYYMMDD.json` 只含 4 个键（schemaVersion / completedArticles /
  updatedAt / exportedAt）；导入先预览再合并（并集）或覆盖（**二次确认**）。
  纯逻辑挂 `globalThis.DailyLingoProgress`，`typeof document === "undefined"` 早退。
- ⚠️ **jsdom 测真 DOM 必须 `runScripts: "outside-only"`**：不加时 `window.eval` 静默不执行
  （表现为 `exports present: false`，什么都不报）；且构造后 `readyState` 是 `loading`，
  **要等 `load` 再点**（脚本按 defer 在 DOMContentLoaded 前跑）。
  jsdom 装在 `~/.workbuddy/binaries/node/workspace/node_modules`，**不是站点/测试硬依赖**，
  `tests/conftest.py::find_jsdom()` 找不到就整组 skip。
- ⚠️ **本沙箱起不了 Chromium**（`msedge --version` 无输出、`--dump-dom` 空、exit 0 假成功），
  所以**像素级布局没有截图证据**，只有 jsdom 行为证据。改这块 CSS 后要人工在浏览器看一眼。

## 已验证 / 待验证
- 已验证（2026-10-18，16 篇 + 学习进度）：`python scripts/build.py`（16 篇 / 1 个 Chapter / 0 警告）、
  `python scripts/validate.py`（PASS 618 / FAIL 0 / WARN 0）、`pytest -q`（152 passed：
  test_build 105 / test_frontend 4 / test_progress 29 / test_progress_dom 14）、
  本地 `http.server` 40 条路径全 200（16 HTML + 16 WAV + 首页 + CSS/JS（含 progress.js）+ 3 图标，35.6 MiB）、
  进程内全量重建 16 篇约 0.20 s（5 次中位数 200 ms；单次 32 ms 是缓存抖动，别采信单次）；
  `watch.py` 实测 touch 后 1 s 内重建（23 ms）。
- ⚠️ **`validate.py` 的「三档倍速」断言必须分支**（2026-10-17 修）：没生成 WAV 的页面只渲染
  `player-unavailable`、不输出任何控件，无条件断言会得到 `rates=[]` 假 FAIL。
  现在：有 `data-player` → 断言 `0.75/1/1.25` + 无 `back`/`forward`；否则 → 断言不出现
  **播放器专属类名**（`player-rates` / `player-track` / `player-toggle`）。
  ⚠️ 别用 `'data-action=' not in html` 判定「没有控件」——**题目区的 Check/Reset 也带
  `data-action`**，会误伤（这个坑当场踩过一次）。
  两棵树都实测过：删掉 `0009` 的 WAV 的临时副本 → PASS 345 / FAIL 0 / WARN 1（就是缺音频那条）。
- ✅ **`core.autocrlf=true` + 无 `.gitattributes` 的假 FAIL 已修（2026-10-17）**：仓内已加
  `.gitattributes`（`* text=auto eol=lf`、`*.bat text eol=crlf`、`*.wav/*.png/*.ico binary`），
  并把索引里仍是 CRLF 的 7 个 `content/*.md` renormalize 成 LF、把 26 个工作副本仍是 CRLF 的
  文本文件重新签出为 LF。**现在 `git ls-files --eol` 只有 `watch.bat` 是 `w/crlf`（预期）。**
  全新 clone 实测：`src/*.html`、`index.html`、`content/*.md`、`assets/js/*.js` 全部 **LF**；
  `watch.bat` 仍 **CRLF**。复现方式：把 10 个生成页面改成 CRLF 后 `validate.py` 会报 10 个
  FAIL（干净站点），validate 现已把「纯行尾差异」显式点出来。
  ⚠️ **指纹口径**：`build.asset_version()` 算的是**磁盘字节**的哈希，所以工作副本行尾一变，
  全站 `?v=` 都会跟着变（本次见证了 CRLF→LF 导致 9 个页面 + 首页的指纹回退到 LF 口径）。
  ⚠️ 同时注意 README《本地静态服务器》清单里的字节数是 **LF 口径**（= Pages 实际下发），
  不要拿 CRLF 工作副本的 `stat` 结果去填（我曾填错一次，18102/7530/9928/941 是 CRLF 尺寸，
  正确值 17162/7291/9610/919）。
  ⚠️ **归一新增文件行尾时绝不要用 `git checkout -- content/`**：它会把该目录下**所有未暂存改动**
  一起回滚 —— 2026-10-17 就这么把用户手改的 `0010` 的 next chapter 冲掉过一次（事后手工改回）。
  正确做法：`git add <文件>` → `rm <文件>` → `git checkout -- <文件>`，**逐个文件**，不要给目录。
- 顺带发现：`0006`/`0007` 的 HTML 曾是过期产物（`?v=` 指纹落后于当前 assets，上个 commit 改了
  CSS/JS 没重建那两页），2026-10-17 重建时对齐。**改 `assets/` 后务必重跑一次构建**。
- **GitHub Pages 已实际发布并验证**：`https://zc110747.github.io/DailyLingo/` 首页与
  css/js/wav 全部 200；WAV 返回 **206 Partial Content（支持 Range）**，
  所以**线上拖动进度条可跳转**。
- ⚠️ **本地与线上的 Range 行为不同，两张清单不要互相抄结论**：
  `SimpleHTTPRequestHandler`（Python 3.13.14）**完全不支持 Range** —— 带
  `Range: bytes=0-1023` 仍返回 `200` 整份文件、且**没有** `Accept-Ranges` 头。
  （曾在 `15985d3` 的「本地静态服务器」清单里错写一行 `206`，已删除并改成显式说明。）
  要验证拖动跳转，只能对**线上**或支持 Range 的服务器发请求。
- 待人工验证：真实浏览器交互（折叠、拖进度条、倍速、点检查答案）、真机出声、移动端布局。
- 播放器尺寸/命中区已用 headless Chromium 实测（`getBoundingClientRect()` + 真实点按/拖动）：
  卡片 136 → **85.7 px**（早期一版 78.7 px，后因「第一行与外框要留白」加了 padding）、
  滑柄中心偏移 0.00 px、点按 ±7 px 命中而 ±11 px 不命中、拖到 60% 得 22 s。
- 一次性验证脚本（playwright 截图、进程内 `http.server` 探测）放 `.workbuddy/tmp/`，
  **已 gitignore，跑完即删**，不要留在仓库里。
  测法：`NODE_PATH=~/.workbuddy/binaries/node/workspace/node_modules` 跑 playwright，
  直接开 `file:///…/src/xxx.html`（**不用起 http 服务**）；`<audio>` 不在 DOM 里，取状态看
  `aria-valuenow` / `aria-valuemax` / `[data-role=current]` 文本。
- 已无待确认项（`tests/example.md` 用户已自行删除）。
