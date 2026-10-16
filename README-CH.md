# DailyLingo

**[English](README.md) | [简体中文](README-CH.md)**

每日英语学习网站：分级短文阅读 + 真实 WAV 朗读 + 重点单词表 + 阅读理解即时判分，
文章导航全自动生成。

纯静态站点 —— **无登录、无数据库、无后端、无远程 API**，构建产物原样提交，
直接由 GitHub Pages 提供服务。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](#快速开始)
[![运行期依赖: 无](https://img.shields.io/badge/%E8%BF%90%E8%A1%8C%E6%9C%9F%E4%BE%9D%E8%B5%96-none-success.svg)](#快速开始)
[![测试: 109 passed](https://img.shields.io/badge/tests-109%20passed-success.svg)](#验证结果)
[![部署: GitHub Pages](https://img.shields.io/badge/deploy-GitHub%20Pages-222.svg)](#部署到-github-pages)

**线上站点：** <https://zc110747.github.io/DailyLingo/>

> **English documentation:** [README.md](README.md)

| | |
|---|---|
| **前端** | HTML5 + CSS3 + 原生 JavaScript（不引入 React/Vue，前端无构建步骤） |
| **文章源** | Markdown —— 唯一维护入口 |
| **构建 / 验证** | Python 3，**只使用标准库** |
| **测试** | pytest（含在 Node 中真实执行的前端判分逻辑） |
| **音频** | 外部离线 TTS 工具生成 WAV，用 HTML5 Audio API 播放 |
| **部署** | GitHub Pages 项目站点，全站相对路径 |

---

## 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [站点图标](#站点图标)
- [文章编号与命名](#文章编号与命名)
- [Markdown 文章格式](#markdown-文章格式)
- [首页 Chapter 目录](#首页-chapter-目录)
- [文章详情页区域](#文章详情页区域)
- [音频播放器](#音频播放器)
- [用 EnglishAudio 生成音频](#用-englishaudio-生成音频)
- [改完 Markdown 自动重建](#改完-markdown-自动重建)
- [GitHub Pages 路径兼容](#github-pages-路径兼容)
- [本地预览](#本地预览)
- [部署到 GitHub Pages](#部署到-github-pages)
- [新增一篇文章](#新增一篇文章)
- [构建脚本的边界](#构建脚本的边界)
- [验证结果](#验证结果)
- [尚未完成与需人工验证的事项](#尚未完成与需人工验证的事项)

---

## 功能特性

- **Chapter 折叠目录** —— 首页**只显示** `DailyLingo` 品牌名和按固定 100 号区间分组的
  `<details>` 文章目录。没有摘要、难度、音频状态、文章数量统计。
- **每篇文章五个固定区域** —— `Article` / `Words` / `Questions` / `Answers` / `Continue`，
  顺序恒定，所有文章共用同一套模板、样式与脚本。
- **真实音频，不是模拟** —— HTML5 Audio 播放器直连真实 WAV。播放暂停、已播时间、总时长、
  实时进度、点击跳转、拖动定位、`0.75x` / `1x` / `1.25x` 倍速、音量、加载 / 结束 / 失败状态，
  全部由真实播放事件驱动。
- **先播放，再阅读** —— 播放器位于 `Article` 标题之下、**正文之上**，与正文之间有一条细分隔线
  且上下留出距离；阅读长文时吸顶，可以先点开音频，再顺着往下读，不必滚回顶部找控件。
- **自带站点图标** —— 手写的 SVG（打开的书 + 声波）加光栅回退，全站每个页面都声明。
  不依赖 CDN、不用图标字体、没有构建步骤：文件原样提交。
- **无需后端的即时判分** —— 单选与填空在浏览器内判分。忽略大小写、忽略首尾空白、容忍尾部标点；
  空白输入永远不判为正确；支持一题多个可接受答案。
- **答案单一真值源** —— 判分答案内嵌在页面 `#quiz-data`，与 Answers 区域同源生成，
  两者不可能不一致。
- **零人工导航** —— 上一篇 / 下一篇、首页列表、Chapter 分组全部由文章编号推导。
  新增一个 Markdown 文件并重建，所有内容自动更新。
- **优雅降级** —— 缺 WAV 只在播放器区域内提示错误，正文、单词表、题目、答案与导航全部照常可用。
- **可复现构建** —— 输入不变时输出字节级一致，由「重建到临时目录后与磁盘逐字节比对」验证。

---

## 快速开始

```bash
# 1) 安装测试依赖（构建与验证脚本什么都不需要）
python -m pip install -r requirements.txt

# 2) 构建站点 -> index.html + src/*.html
python scripts/build.py
python scripts/build.py --verbose    # 带逐篇明细

# 3) 验证生成结果与数据一致性
python scripts/validate.py

# 4) 跑自动化测试
pytest -q

# 5) 改 Markdown 时自动重建，然后预览
python scripts/watch.py              # Ctrl+C 退出
python -m http.server 8000
```

| | 要求 | 实测版本 |
|---|---|---|
| Python | 3.9+（构建脚本只用标准库） | 3.13.12 |
| pytest | 仅在跑测试时需要 | 9.1.1 |
| Node.js | 仅在跑 `tests/test_frontend.py` 时需要（缺失时自动跳过） | 22.22.2 |

> `scripts/build.py` 与 `scripts/validate.py` **没有引入任何标准库之外的模块**。
> `requirements.txt` 里的 pytest 只为测试服务。

---

## 目录结构

```text
DailyLingo/
├── index.html                  # 首页（生成）：品牌名 + Chapter 折叠目录
├── src/                        # 文章详情页（生成）—— 每篇文章一个 .html
│   ├── 0001.A_New_Hobby.html
│   └── …                       # 0002、0003、… 每篇一个
├── content/                    # 文章唯一维护源（Markdown）
│   ├── 0001.A_New_Hobby.md
│   └── …                       # 0002、0003、… 每篇一个
├── sources/                    # 外部 TTS 工具生成的 WAV（与 md 同名）
│   ├── 0001.A_New_Hobby.wav
│   └── …                       # 0002、0003、… 每篇一个
├── assets/
│   ├── css/style.css           # 全站统一样式（桌面 + 移动）
│   ├── js/audio-player.js      # 音频播放器
│   ├── js/main.js              # 题目判分 / 页面交互
│   └── images/                 # 站点图标（原样提交，非构建产物）
│       ├── favicon.svg         # 设计源文件：打开的书 + 声波
│       ├── favicon-32.png      # 不支持 SVG 图标时的光栅回退
│       └── favicon-180.png     # apple-touch-icon
├── scripts/
│   ├── build.py                # 构建：解析 -> 分组 -> 渲染 -> 关联音频
│   ├── watch.py                # 同步：md/wav 一变就自动重建
│   └── validate.py             # 生成结果与数据校验
├── tests/
│   ├── conftest.py
│   ├── test_build.py           # 解析 / 分组 / 标题 / 导航 / 判分 / 路径
│   └── test_frontend.py        # 在 Node 中真实执行判分逻辑
├── watch.bat                   # Windows 双击即开始监听
├── requirements.txt
├── .gitignore
├── LICENSE
├── README.md                   # 英文文档（默认）
└── README-CH.md                # 本文件（简体中文）
```

> `tools/`（EnglishAudio 的 ~100 MB 打包产物）**不在仓库内**：体积大且已在其它仓库维护，
> 这里只按需调用。`.gitignore` 已忽略该目录，放进去也不会污染 `git status`。
> 见 [用 EnglishAudio 生成音频](#用-englishaudio-生成音频)。

目录职责边界：

| 路径 | 定位 | 可否手工编辑 |
|---|---|---|
| `content/` | 文章唯一维护源 | **是**，人工维护 |
| `src/`、`index.html` | 构建生成的 HTML | 否，重新构建即覆盖 |
| `sources/` | 外部工具生成的 WAV | 由音频工具写入 |
| `assets/` | 全站公共 CSS / JS | 是 |

> **生成物（`index.html`、`src/*.html`）是刻意提交的。** GitHub Pages 以仓库根目录作为站点根
> （*Deploy from a branch*），不提交它们发布会得到一个空站点。

---

## 站点图标

图标是手写的 SVG（919 B）：圆角蓝底上排三条声波、下方一本打开的书 —— *听 + 读*，
正好对应本站的两件事。光栅回退由同一套几何渲染而来，三个文件视觉一致。

| 文件 | 声明方式 | 大小 |
|---|---|---|
| `assets/images/favicon.svg` | `rel="icon" type="image/svg+xml"` | 919 B（矢量） |
| `assets/images/favicon-32.png` | `rel="icon" type="image/png" sizes="32x32"` | 942 B |
| `assets/images/favicon-180.png` | `rel="apple-touch-icon" sizes="180x180"` | 4 682 B |

- 每个页面都声明这三个文件，相对路径规则与全站一致（首页 `assets/images/…`，
  文章页 `../assets/images/…`），并附带与图标底色一致的 `<meta name="theme-color">`。
- 首页还会在品牌名左侧显示图标（`class="brand-icon"`），属于品牌标识的一部分，
  不属于「品牌名 + Chapter 目录」之外的信息。
- 需要换图标时，替换这三个文件后重新构建即可。`validate.py` 会检查文件存在、
  PNG 头有效，以及每个页面都以正确前缀声明了它们。
- 图标是**静态资产而非构建产物**：原样提交，即使从不运行构建脚本站点也照常工作。

---

## 文章编号与命名

### 编号

- 编号是**永久 ID**，不随标题、正文或排序变化。
- 按数值升序排列；重复编号直接报错。
- 默认显示四位，不足补零：`0001`、`0002`、`0010`、`0100`、`0101`。
- 超过四位的编号**保留完整数字，不截断**：`10000`、`123456`。
- 文件名、front matter 的 `id` 与编号三者必须一致，否则构建失败。

### 文件命名

```text
content/0001.A_New_Hobby.md
src/0001.A_New_Hobby.html       # 构建生成
sources/0001.A_New_Hobby.wav    # 音频工具生成
```

> **文件名里不要有空格。** `0006.A_Visit_to_the Library.md` 会让 `sources/` 的音频名与页面链接、
> `href` 属性三处对不上。请改用下划线。

### 标题生成

原始标题**不含编号**，编号由唯一一个公共函数（`build.display_title` / `build.page_title`）添加，
全站共用：

| 位置 | 输出 |
|---|---|
| 首页列表 | `0001. A New Hobby` |
| 文章页 `<h1>` | `A New Hobby`（上方单独显示编号） |
| 浏览器标签 | `0001. A New Hobby \| DailyLingo` |
| 上一篇 / 下一篇导航 | `上一篇：0001. A New Hobby` |

任何模板里都不存在手工硬编码的标题。

---

## Markdown 文章格式

### 兼容格式（当前 `content/` 采用）

```markdown
# A New Hobby

## Article

My name is David. I am thirty years old. I work in a small company.

Every day, I am busy with my work. Sometimes, I feel tired after work.

## Words

| Word | Pronunciation | 中文释义 |
| --- | --- | --- |
| **meal** | /miːl/ | 餐、一顿饭 |
| **tired** | /ˈtaɪəd/ | 累的、疲惫的 |

## Questions

**Where does David work?**

A. In a school.

B. In a small company.

C. In a supermarket.

## Answers

BAC

## Continues

- [cataloge](./catalogue.md)
```

要点：

- 一级标题 `# ...` 是**原始标题**（不含编号）。
- 章节名大小写不敏感，`# Article` 与 `## Article` 两种层级都接受；
  `## Questions` 内部的 `## Q1` **不会**被当成新章节。
- `## Words` 表头列名按别名识别，3 列和 5 列都支持：
  `Word/单词`、`Pronunciation/音标`、`词性/pos`、`中文释义/meaning`、`例句/example`。
  单元格里的 `**粗体**` 会被剥离。
- `## Answers` 支持四种写法（可混用）：
  1. **紧凑字母串** —— 按题目顺序逐题赋值：`BAC`、`ACBBA`、`CABABB`；
  2. **单题行** —— `Question5: He feels happy because he has helped someone.`；
  3. **分块** —— `## Q1` + `答案：B` + `解释：…` + `可接受答案：cook, to cook`；
  4. **编号答案列表** —— `1. **B. To the library.** 解释文字`：粗体里的选项字母作为答案，
     粗体后的文字作为解释（粗体后没写解释时，用粗体原文当解释）。填空题同样适用
     （`1. cook` / `1. **cook**`）。
     字母判据刻意从严，`cook`、`bamboo` 这类单词不会被误判成选项 `C` / `B`
     （见 `build.extract_choice_key` 与 `tests/test_build.py::test_extract_choice_key`）。
     序号后的点**允许被反斜杠转义** —— `1\. **B. …**`，这是编辑器为了不让该行变成有序列表而
     自动写的形态；CommonMark 里 `\.` 就是字面句点，所以两种写法等价，输出完全一致。
- 题干支持 `Question 1：…`（半角/全角冒号均可）、`**题干**`、`## Q1`、`1. 题干`
  （序号点写成 `1\.` 同样可以）等写法。
- `## Continues`（或 `## Continue`）会被构建忽略 —— 上一篇 / 下一篇与目录始终自动生成，
  不需要人工维护。

### 题型

| 题型 | 判定方式 | 判分 |
|---|---|---|
| 单选 | 题干下跟随 `A. / B. / C. …` 选项，或显式写 `题型：单选` | 选项字母比对，忽略大小写 |
| 填空 | 题干下没有选项，或显式写 `题型：填空` | 与「答案 / 可接受答案」比对：**忽略大小写、忽略首尾空白、忽略尾部标点；空白输入永远不判为正确** |

题干中的 `______`（连续下划线）会被**完整保留**，不会被误当成 Markdown 强调语法。

### 可选：YAML Front Matter

```markdown
---
id: "0101"
title: "Some Title"
audio: "0101.Some_Title.wav"
---
```

三项都可省略：`id` 默认取文件名前缀（写了则必须与文件名一致），
`title` 默认取 `# 一级标题`，`audio` 默认取 `<编号>.<文件名标题>.wav`。

---

## 首页 Chapter 目录

首页**只显示**两样东西：`DailyLingo` 品牌名，以及按 Chapter 分组的可折叠文章目录。
不显示摘要、难度、音频状态、文章数量或任何其他信息。

```text
DailyLingo

▼ Chapter 0001–0100
    0001. A New Hobby
    …
```

*（目录按编号升序列出该 Chapter 的全部文章，这里只展示第一条。真实首页不做任何省略。）*

### 分组算法（`build.chapter_bounds` / `build.group_chapters`）

每 100 个编号划分为一个**固定**区间。分组依据是编号的**数值**，与文章数量、数组下标、
排序位置无关：

```python
start = ((number - 1) // 100) * 100 + 1
end   = start + 99
```

| 编号 | 所属 Chapter |
|---|---|
| `0001` | Chapter 0001–0100 |
| `0100` | Chapter 0001–0100 |
| `0101` | Chapter 0101–0200 |
| `0200` | Chapter 0101–0200 |
| `0201` | Chapter 0201–0300 |

**只输出包含真实文章的 Chapter。** 中间缺号不会移动区间边界，也不会提前创建空分组。
新增文章后重建，新分组自动出现；删除某组最后一篇文章后重建，该组不再显示。

分组计算与 HTML 渲染是分离的（`group_chapters` → `render_index`），规则不会散落到模板里，
可以直接被单元测试调用。

### 折叠行为

- 使用语义化的原生 `<details>` / `<summary>`；鼠标与键盘均可操作，焦点状态可见。
- `Chapter 0001–0100`（第一组）**默认展开**；其他实际存在的 Chapter **默认折叠**。
- 每个 Chapter 独立控制，展开一个不会强制关闭其他。
- 收起 / 展开状态由箭头方向体现（`▸` / `▾`）。

---

## 文章详情页区域

按固定顺序渲染，所有文章共用同一套模板、CSS 与 JavaScript：

| # | 区域 | 内容 |
|---|---|---|
| 1 | **Article** | 编号、标题、**WAV 播放器**、英文正文。播放器渲染在**区域标题之下、第一段正文之上**，所以自然顺序是：先开音频，再读文字 |
| 2 | **Words** | 单词表（单词 / 音标 / 词性 / 中文释义 / 例句）。窄屏下表格在自身容器内横向滚动，**整页不会横向滚动** |
| 3 | **Questions** | 单选 + 填空，原生 JavaScript 判分，无需后端 |
| 4 | **Answers** | **默认折叠**；展开后显示正确答案、可接受答案与解释 |
| 5 | **Continue** | 返回目录、上一篇、下一篇（显示目标文章的真实编号与标题） |

- 题目 ID 在页面内唯一（`Q1`、`Q2`…），答案通过 ID 与题目关联。
- 判分答案内嵌在页面 `#quiz-data`，与 Answers 区域**同源生成**，修改答案后重建即自动同步。
- 播放器放在**正文之上**，并在文章滚动时 `position: sticky` 吸顶，进度条与倍速控件在阅读过程中
  始终够得着；不想要吸顶效果，删掉 `assets/css/style.css` 里的 `.section-article .player`
  规则即可，不影响其他布局。
- 首篇不生成上一篇链接、末篇不生成下一篇链接 —— 显示「上一篇：无」而不是死链。
- 上一篇 / 下一篇按**编号数值升序**计算，与首页 Chapter 分组完全独立。

---

## 音频播放器

基于真实 WAV 文件与 HTML5 Audio API。**所有显示状态都与真实播放状态同步**，
不存在模拟进度条或伪造播放状态。支持：

- 播放 / 暂停
- 已播时间、总时长、实时进度
- 点击进度条跳转；按住拖动定位（Pointer Events，触屏可用）
- 进度条键盘操作：`←` / `→` 5 秒（`Shift` 10 秒）、`Home` / `End`、
  `Space` / `Enter` 切换播放
- `0.75x` / `1x` / `1.25x` 倍速
- 音量调节
- 状态提示：正在加载 / 缓冲中 / 已就绪 / 正在播放 / 已暂停 / 播放结束
- 音频缺失或加载失败时的明确错误提示

时长尚未获取时显示 `--:--`，页面其他部分不受影响。

**某篇文章缺 WAV 时**，播放器区域显示缺失提示，而正文、单词表、题目、答案、导航
**全部照常可用**。构建只输出警告，不阻断其他页面。

### 用 EnglishAudio 生成音频

音频由外部工具生成 —— 构建脚本**不做** TTS、**不做**转码。本项目使用
**EnglishAudio**（Piper + ONNX，完全离线：不联网、不上传文本）。它可存在于两处：

- `D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd` —— 源仓库，已单独维护；
- `<本仓库>/tools\eaudio.cmd` —— 可选：把整包复制进来即可。`tools/` 已被 `.gitignore` 忽略，
  因为整包约 100 MB（含 63 MB 语音模型），不再在仓库里存第二份。

`scripts/watch.py --audio` 按下面的顺序定位它；都找不到时只重建网页并给出提示：

```text
--audio-tool <路径>  >  环境变量 DAILYLINGO_AUDIO_TOOL  >  <仓库>/tools/eaudio.cmd
                     >  009.ai_voice\publisher\eaudio.cmd
```

```bat
:: 单篇：读取 ## Article 章节 -> 生成同名 WAV
"D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd"^
  "content\0006.A_Visit_to_the_Library.md" --dist="sources"

:: 批量：把 content/ 下所有 md 一次转完
for %f in (content\*.md) do ^
  "D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd" "%f" --dist="sources"

:: 也可以交给同步脚本：自动补齐缺失 WAV 并重建网页
python scripts/watch.py --audio
```

该工具只朗读 `## Article` 章节 —— `## Words` / `## Questions` / `## Answers` / `## Continues`
不会被读出来。正文含非英文字符会被直接拒绝（退出码 4），Markdown 必须是 UTF-8。

> **改了正文就必须重新生成 WAV。** 同步脚本只在文件**缺失**时补齐，不检测内容过期，
> 所以改过正文的文章会一直保留过期录音，直到你重跑一次工具。

本仓库所有 WAV 均由该工具生成，参数**完全一致**（单声道 / 16 bit / 22 050 Hz，每篇文章一个），
用 Python `wave` 模块读出核对：

| 文件 | 声道 / 位深 / 采样率 | 时长 | 大小 |
|---|---|---|---|
| `0001.A_New_Hobby.wav` | 单声道 / 16 bit / 22 050 Hz | 37.22 s | 1 641 488 B |
| …（每篇文章一行） | 单声道 / 16 bit / 22 050 Hz | 各不相同 | 各不相同 |

### 改完 Markdown 自动重建

手工维护时不必反复敲构建命令：`watch.py` 轮询 `content/*.md` 与 `sources/*.wav`，
发现新增 / 修改 / 删除后自动重建 `index.html` 与 `src/*.html`。

| 命令 | 作用 |
|---|---|
| `python scripts/watch.py` | 监听并自动重建（默认 1 s 轮询） |
| `python scripts/watch.py --audio` | 顺带用 EnglishAudio 补齐缺失的 WAV |
| `python scripts/watch.py --once` | 只重建一次后退出（适合放进脚本 / Git hook） |
| `python scripts/watch.py --interval 0.5` | 调整轮询间隔 |
| `watch.bat`（双击） | Windows 上一键启动，等价于 `--audio` |

行为约定：

- **全量重建**（8 篇 < 0.2 s）：新增或删除一篇文章会改变相邻文章的上一篇 / 下一篇，
  只重写「变化的那一页」会留下不一致的假象。
- Markdown 写坏时**只打印错误并继续监听**，不会退出；修好再保存即可重建成功。
- 被删除文章遗留的 `src/*.html` 只提示、**不自动删除**（构建脚本同样不删文件）。

---

## GitHub Pages 路径兼容

站点部署在**项目子路径**下，例如 `https://zc110747.github.io/DailyLingo/`。

- 全部链接与资源引用都是**相对路径**，没有任何以 `/` 开头的站点根路径：
  - 首页 → 文章：`src/0001.A_New_Hobby.html`
  - 文章 → 首页：`../index.html`
  - 文章 → 资源：`../assets/css/style.css?v=<指纹>`、`../assets/js/*.js?v=<指纹>`
  - 文章 → 音频：`../sources/0001.A_New_Hobby.wav`
  - 上一篇 / 下一篇：同目录文件名
- **CSS / JS 的 URL 带内容指纹**：`?v=` + 文件 SHA-256 的前 8 位十六进制。GitHub Pages 对这些
  文件回 `Cache-Control: max-age=600`，只改内容不改 URL 的话，手机上最长 10 分钟还拿旧文件
  —— 表现就是「明明改了样式，手机上却没变」。内容一变 URL 就变，浏览器必然重新拉取。
  指纹由 `build.asset_version()` 只按文件内容算出，因此构建仍字节级可复现。
- `scripts/validate.py` 会断言生成结果中不存在 `href="/..."` / `src="/..."`。
- 不依赖后端路由、服务器重写或动态 API，本地静态服务器与 GitHub Pages 行为一致。

---

## 本地预览

```bash
python scripts/build.py
python -m http.server 8000
```

浏览器打开：

- 首页 —— <http://localhost:8000/>
- 示例文章 —— <http://localhost:8000/src/0001.A_New_Hobby.html>

> `python -m http.server` **不支持** HTTP Range 请求（线上 GitHub Pages 支持）。
> 浏览器会把整个 WAV 下载完再播放，因此本地预览时拖动跳转的体验与线上略有差异，
> 功能本身不受影响。

---

## 部署到 GitHub Pages

1. 确认 `python scripts/build.py && python scripts/validate.py && pytest -q` 全部通过。
2. 提交并推送 —— **构建产物 `index.html` 与 `src/*.html` 必须一起提交**。
3. 打开仓库 **Settings → Pages**。
4. **Source** 选择 *Deploy from a branch*。
5. **Branch** 选择 `main`，目录选择 `/ (root)`。
6. 保存并等待发布完成。
7. 打开实际发布地址（<https://zc110747.github.io/DailyLingo/>），逐项检查：
   首页 → Chapter 折叠展开 → 文章正文 → 音频播放与倍速 → 单词表 → 练习题判分 →
   展开 Answers → 上/下一篇导航。

若仓库使用其他分支或部署方式，按实际配置调整。

---

## 新增一篇文章

1. 在 `content/` 新建 Markdown，文件名用**未占用的编号**：

   ```text
   content/0009.My_Weekend.md
   ```

2. 写原始标题与正文：`# My Weekend`，然后 `## Article`。
3. 填 `## Words`（3 列或 5 列均可）、`## Questions`、`## Answers`。
4. 用 EnglishAudio 生成同编号 WAV 并放进 `sources/`（见
   [用 EnglishAudio 生成音频](#用-englishaudio-生成音频)）：

   ```bat
   "D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd"^
     "content\0009.My_Weekend.md" --dist="sources"
   ```

5. 重建与自检 —— 或者更省事：先开着 `python scripts/watch.py --audio`，
   保存 md 后第 4、5 步都会自动完成：

   ```bash
   python scripts/build.py --verbose
   python scripts/validate.py
   pytest -q
   ```

6. 浏览器里检查页面与音频，然后提交推送。

新增后**自动完成**：首页文章列表、Chapter 分组（必要时新增分组）、文章主标题、
浏览器标签标题、上一篇 / 下一篇导航、WAV 关联。
**不需要**手工修改 `index.html`、Chapter 分组或其他文章的导航。

**改名或删除文章** —— 构建从不删文件，所以要自行清理遗留的 `sources/<旧名>.wav` 与
`src/<旧名>.html`。改名的完整动作是：`git mv` 源文件 → 更新其 `# ...` 标题 →
更新相邻文章 `## Continues` 里的交叉引用 → 重新生成 WAV → 删除旧产物 → 重新构建。
编号本身永不改变。

---

## 构建脚本的边界

`scripts/build.py` **会做**：

扫描 `content/` → 解析 Markdown 与元数据 → 校验编号 / 标题 / 结构 / 重复编号 / 文件名一致性 →
按编号升序 → 计算 Chapter 分组 → 只输出非空分组 → 第一组默认展开 → 渲染 `index.html` →
渲染全部文章页 → 统一生成主标题与浏览器标签 → 渲染单词表 / 练习题 / 答案 → 关联 WAV →
生成上一篇与下一篇 → 检查导航目标与资源路径 → 缺失音频输出警告 → 非法数据明确报错 →
输出构建摘要。

`scripts/build.py` **不会做**：

生成语音、调用 TTS、把 WAV 转成 MP3、生成没有真实文章的 Chapter、生成虚构文章或占位链接、
在首页显示摘要 / 难度 / 音频状态、在各模板里重复硬编码标题、
因单篇缺音频而阻止其他页面构建。

构建是**可复现**的：输入不变时多次构建输出字节级一致。`validate.py` 会把站点重建到临时目录，
再与磁盘上的产物逐字节比对来证明这一点。

---

## 验证结果

以下数据均在本机实测：Windows 10 19045 / Python 3.13.12 / Node 22.22.2。

### 构建

```text
$ python scripts/build.py --verbose
  文章 0001  A New Hobby  |  3 词  3 题  |  音频 有
  …                                   # 每篇文章一行
DailyLingo 构建完成
  文章总数：8
  Chapter 分组：1
    Chapter 0001–0100（默认展开）：8 篇
  警告：0 条
```

*（为可读性做了省略：真实输出每篇文章打印一行 `文章 NNNN …`，并在 Chapter 下逐条列出标题。）*

### 验证脚本

```text
$ python scripts/validate.py
结果：PASS 310 / FAIL 0 / WARN 0
```

覆盖：文章数据；编号唯一性与升序；Chapter 区间边界与「只输出有真实文章的 Chapter」；
首页只含品牌名与折叠目录（并做摘要 / 难度 / 音频状态的**反向**检查）；第一个 Chapter 默认展开；
五个区域顺序；**播放器位于 `Article` 区内、标题之下、第一段正文之上**；**播放器与正文之间有分隔线**；
**播放器控件为音量 + 恰好三档倍速（`0.75x` / `1x` / `1.25x`，无 ±5 秒）**；
**图标文件存在、PNG/SVG 有效、每个页面都以正确相对前缀声明**；浏览器标签与主标题一致性；
单词表行数；题目数量；判分数据与 Answers 同源；Answers 默认折叠；上一篇 / 下一篇链接与标题；
首末篇边界；无绝对根路径；静态资源存在性；重复构建字节级一致。

### 自动化测试

```text
$ pytest -q
109 passed in 2.31s
```

| 文件 | 用例数 | 覆盖内容 |
|---|---|---|
| `tests/test_build.py` | 105 | 文章解析（缺编号 / 缺标题 / 编号非法 / 重复编号 / 编号与文件名不一致 / 中文与特殊字符）、编号显示规则（含超过四位）、Chapter 边界（`0001`/`0100`/`0101`/`0200`/`0201`/`0300`/`301`/`9999`/`10001`）、缺号仍正确分组、空 Chapter 不显示、组内升序、第一组默认展开、新增文章产生新分组、删除最后一篇后分组消失、首页链接可解析、标题全站一致、浏览器标签含编号、上一篇 / 下一篇与首末边界、导航与分组无关、单词表 3 列与 5 列、题型推断、紧凑答案串、**编号答案列表（`1. **B. …** 解释`，含被转义的 `1\.` 写法，题干与答案都测）、`extract_choice_key` 的 11 组边界（`cook` 不被当成 `C`）**、`题型：填空` + 多可接受答案、`______` 保留、非法答案配置可被识别、缺答案报错、Answers 默认折叠、判分数据与答案一致、`normalize_answer` 边界、**播放器位于正文之前（有 / 无 WAV 两种情形）**、**播放器与正文之间有分隔线**、**无 ±5 秒按钮且恰好三档倍速**、**图标声明前缀正确、首页品牌图标、图标资产的 PNG/SVG 有效性与尺寸**、缺音频只警告不影响其他区域、CSS/JS/音频相对路径、**CSS/JS 的 URL 带内容指纹（`?v=` + 8 位十六进制）**、GitHub Pages 子路径、构建可重复 |
| `tests/test_frontend.py` | 4 | 在 Node 中真实执行 `assets/js/main.js`：单选正确 / 错误 / 空选、大小写不敏感、首尾空格、尾部标点、多个可接受答案、空白输入不判正确；并与 `build.normalize_answer` 做逐样本一致性比对 |

测试全部使用临时目录，不会污染或覆盖真实的 `content/` 与 `sources/`。

### 本地静态服务器

```text
$ python -m http.server 8123
200 2297   text/html              <- /
200 9650   text/html              <- /src/0001.A_New_Hobby.html
200 …                               <- /src/0002 … 0008（每篇文章一个页面）
200 17162  text/css               <- /assets/css/style.css
200 7291   application/javascript <- /assets/js/main.js
200 9610   application/javascript <- /assets/js/audio-player.js
200 919    image/svg+xml          <- /assets/images/favicon.svg
200 942    image/png              <- /assets/images/favicon-32.png
200 4682   image/png              <- /assets/images/favicon-180.png
200 1641488 audio/wav             <- /sources/0001.A_New_Hobby.wav
200 …                               <- /sources/0002 … 0008（每篇文章一个 WAV）
```

*（做了省略：全部 23 条路径——8 个文章页、8 个 WAV、首页与共享静态资源——都真实请求过且全部
`200`；按文章逐条的那部分只留一个示例加 `…`，文章变多以后这份清单仍然可读。）*

> **`python -m http.server` 不支持 `Range`。** 带 `Range: bytes=0-1023` 的请求仍返回 `200`
> 整份文件，也没有 `Accept-Ranges` 头，所以「拖动进度条跳转」无法对着本地服务器验证。
> GitHub Pages 支持（见下）。

### 线上发布

```text
$ curl -I https://zc110747.github.io/DailyLingo/
200                                  <- /
200  text/css                       <- /assets/css/style.css
200  application/javascript         <- /assets/js/main.js
200  application/javascript         <- /assets/js/audio-player.js
200  audio/wav                      <- /sources/0001.A_New_Hobby.wav
200  audio/wav                      <- /sources/0002 …（每篇文章一个 WAV）
206  Partial Content (Range)        <- /sources/0001.A_New_Hobby.wav
```

GitHub Pages 上返回的首页列出的正是仓库里的全部文章，归属于 `Chapter 0001–0100`。
WAV 响应支持 HTTP Range 请求（`206 Partial Content`，已实测），因此线上拖动进度条可正常跳转。

### 开发过程中发现并修复的真实缺陷

- **`______` 被 Markdown 强调规则吃掉**：`strip_markdown` 原本处理 `_斜体_`，
  把填空题干的连续下划线替换掉了，`very ______.` 变成 `very __.`。
  已移除下划线强调规则（`**粗体**` / `*斜体*` 保留），并加了回归测试。
- **`## Q1` 子标题把题目区提前截断**：章节切分原先只认二级标题，
  遇到无法识别的 `## Q1` 就结束当前章节，导致扩展格式的文章「没有解析到任何题目」。
  现在无法识别为章节的标题行会保留在当前章节内。
- **编号答案列表解析不到答案**：新增的 `0006` 用 `1. **B. To the library.** 解释文字`
  写答案，解析器只认紧凑字母串 / `QuestionN:` / 分块三种写法，直接报
  `Q1/Q2/Q3 缺少答案` 构建失败。`apply_answers` 已支持这种写法
  （并新增 `extract_choice_key`，用严格判据避免把 `cook`、`bamboo` 误判成 `C`、`B`），
  附 5 个回归测试 + 11 组参数化边界用例。
- **转义过的列表序号让答案解析不到**：新增的 `0007` 把答案写成 `1\. **B. Her mother.** …`，
  序号后的点被反斜杠转义（编辑器为了不让该行被自动编号成有序列表就常这么写，CommonMark 里
  `\.` 就是字面句点）。编号列表的正则只认裸 `.`，于是一个答案都没绑定上，构建直接以
  `Q1…Q5 缺少答案` 中止。现在 `_ANS_NUMBERED_RE`、`_Q_NUMBERED_RE`、`_ANS_CHOICE_KEY_RE`
  都允许分隔符前多一个反斜杠，题干与答案的 `1.` / `1\.` 完全等价；补了 2 条回归测试，
  其中一条专门断言这个反斜杠不会漏进渲染后的页面。
- **文件名里出现空格**：`0006.A_Visit_to_the Library.md` 会让 `sources/` 的音频名与页面链接
  对不上（生成的 `href` 里也带空格）。已统一为下划线命名
  （`0006.A_Visit_to_the_Library.md` / `.wav`），旧文件已删除。
- **文章标题与正文不符**：`0005` 标题是 *A Busy Morning*（与 `0002` 重复），
  正文写的却是周六在农场的一天。已改名为 *A Day on the Farm* —— 编号、源文件名、H1、
  音频与相邻文章的 `## Continues` 交叉引用同步更新。
- **改正文后音频过期**：`0005` 的 WAV 生成于正文修改之前，录音与文字已不一致。
  同步脚本只在文件**缺失**时补齐，不检测内容过期，必须显式重新生成。现已写入文档。
- **已经 push 的样式修复，手机上看不到**：移动端 Continue 卡片被撑到 200 px 的问题修好并
  部署后，手机仍旧是那个高度。查下来线上样式其实是**对的** —— GitHub Pages 给 CSS 回
  `Cache-Control: max-age=600`，而手机在部署前几分钟已经拉过上一版，于是继续用缓存那份。
  由此做了两件事：① CSS / JS 的 URL 挂内容指纹 `?v=<哈希>`（见《GitHub Pages 子路径兼容》）；
  ② 把布局修法从媒体查询里挪出来 —— 共享规则上的 `flex: 1 1 200px` 一旦容器翻成
  `flex-direction: column`，200px 就变成**高度**；现在改成 `flex: 1 1 0` + `min-width: 200px`，
  横向排逐像素不变、纵向排天然安全。

---

## 尚未完成与需人工验证的事项

自动化测试能证明的部分已在上文列出。以下项目**未**在本机执行，因此不做「已验证」的声明：

1. **真实浏览器交互未做端到端自动化**：本环境没有可用的浏览器自动化通道，
   因此「点击 Chapter 展开收起、拖动进度条跳转、切换倍速、输入答案点检查答案」这些交互
   没有跑过自动化用例。已做的是：判分规则在 Node 中逐条真实执行（见上文），
   生成 HTML 的结构与语义（`<details>` / `<summary>` / `role="slider"` / `aria-live` /
   `aria-controls`）由 `validate.py` 静态断言。请按[本地预览](#本地预览)在浏览器里手工过一遍。
2. **实际听感未验证**：WAV 参数已用 Python `wave` 模块读出核对，
   但「播放是否真的出声」需要有声卡的浏览器会话，未由本工具执行。
3. **移动端真机布局未验证**：响应式断点（640 px）已实现，未在真机或设备模拟器中逐档核对。
   单词表放在 `.table-wrap`（`overflow-x: auto`）内，整页不会横向滚动。
4. **键盘无障碍仅做了代码层面的保障**：语义化标签、可见焦点、文本化反馈、
   进度条可聚焦可操作。未使用读屏软件实测。
5. **`src/` 中已删除文章的历史 HTML 不会被自动清理**：构建不删除文件，
   避免误删非构建产物。若某篇文章被移除，请手工删除对应的
   `src/xxxx.*.html` 与 `sources/xxxx.*.wav`。
6. **图标外观与吸顶播放器未在浏览器中目视确认**：图标资产做了结构校验（尺寸、PNG 签名、
   每个页面的声明）并已按渲染结果目视检查过，但 16 px 标签栏里的实际观感、以及手机上滚动时
   播放器的吸顶表现，需要真实浏览器会话。若不需要吸顶效果，删掉 `assets/css/style.css` 中的
   `.section-article .player` 规则即可。

---

**[English](README.md) | [简体中文](README-CH.md)**
