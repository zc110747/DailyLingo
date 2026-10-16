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
| `scripts/build.py` | 构建 | 是 |
| `scripts/validate.py` | 验证 | 是 |
| `tests/` | pytest（`tests/test_build.py` + `tests/test_frontend.py`） | 是 |

生成物（`index.html`、`src/*.html`）**必须提交**，Pages 以仓库根为站点根。

## 硬约定
1. 编号是永久 ID：四位补零，超过四位不截断；文件名 = `NNNN.Title_With_Underscores.md`，
   编号、文件名、front matter `id` 三者必须一致，否则构建报错。
2. 显示标题统一由 `build.display_title()` 生成：`NNNN. 原始标题`；浏览器标签加 `| DailyLingo`。
   首页 / 文章页 / 标签 / 上下篇导航共用同一函数。
3. Chapter 固定 100 号一段：`start = ((n-1)//100)*100 + 1`；**只输出含真实文章的 Chapter**，
   第一组默认展开（`<details open>`），其余折叠。
4. 文章页固定五个区域，顺序不可变：Article / Words / Questions / Answers / Continue。
   Answers 用 `<details>` 默认折叠；判分答案内嵌在 `#quiz-data`，与 Answers 同源。
5. 全站相对路径，**禁止 `href="/…"` / `src="/…"`**；`validate.py` 会失败。
6. 构建脚本不生成音频、不调 TTS、不转码；单篇缺 WAV 只警告，其他页面照常构建。
7. 构建必须可复现：输入不变时输出字节级一致（validate.py 会重构建到临时目录逐字节比对）。
8. `src/` 中已删除文章的历史 HTML **不会自动清理**（不删文件原则），需人工删。

## 文章 Markdown 格式
兼容两种，可混用：
- 既有格式（`D:\user_project\git\DailyWork\english`）：`# 标题` + `## Article` / `## Words`
  （3 列或 5 列，表头按别名识别）/ `## Questions`（`**题干**` 或 `Question N: 题干` + `A. …`）/
  `## Answers` / `## Continues`（被忽略）。
- 扩展格式：YAML front matter（`id` / `title` / `audio`）+ `## Q1` + `题型：单选|填空` +
  `答案：` / `可接受答案：` / `解释：`。
- 答案三种写法可混用：紧凑字母串（`BAC`，按题目顺序）、`Question5: …`、分块。
- 题干里的 `______` 是内容，`strip_markdown` **不得**处理下划线强调。

## 音频链路
WAV 由 `D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd` 生成：
只朗读 `## Article` 章节，输出与 md 同名的 WAV，正文含非英文会被拒绝（退出码 4），
md 必须是 UTF-8。本仓 4 个 WAV 均为单声道 / 16 bit / 22 050 Hz。

## 已验证 / 待验证
- 已验证：`python scripts/build.py`（0 警告）、`python scripts/validate.py`（PASS 146/FAIL 0）、
  `pytest -q`（84 passed）、本地 `http.server` 全部资源 200。
- 待人工验证：真实浏览器交互（折叠、拖进度条、倍速、点检查答案）、真机出声、移动端布局、
  GitHub Pages 实际发布后的访问（`git push` 由用户自己做）。
