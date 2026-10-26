# DailyLingo

**[English](README.md) | [简体中文](README-CH.md)**

每日英语学习网站：分级短文阅读 + 真实 WAV 朗读 + 重点单词表 + 阅读理解即时判分，
文章导航全自动生成，学习进度只存在你自己的浏览器里。

纯静态站点 —— **无登录、无数据库、无后端、无远程 API**，构建产物原样提交，
直接由 GitHub Pages 提供服务。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](#快速开始)
[![运行期依赖: 无](https://img.shields.io/badge/%E8%BF%90%E8%A1%8C%E6%9C%9F%E4%BE%9D%E8%B5%96-none-success.svg)](#快速开始)
[![测试: 517 passed](https://img.shields.io/badge/tests-517%20passed-success.svg)](#验证结果)
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
- [学习进度](#学习进度)
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

- **Chapter 折叠目录** —— 首页显示 `DailyLingo` 品牌名、一张紧凑的学习进度卡，以及按固定
  **25 篇一章**分组的 `<details>` 文章目录，每章带自己的计数与进度条。没有摘要、没有难度、
  没有音频状态。
- **学习进度只存在你自己的浏览器里** —— 每篇一个完成开关、Chapter 全部学完才变绿的汇总、
  实时更新的 `已完成 / 总数 · 百分比` 进度条，以及藏在左上角设置里的 JSON 导出 / 导入
  （合并或覆盖）与 Android 安装包下载。无账号、无后端、不上传任何数据 —— 详见[学习进度](#学习进度)。
- **文章页自动打勾** —— 听完音频（真的听够 ≥ 90%，中途拖动不算）**且**全部题目答对，这篇文章
  会自己写进首页读的那份进度；标题下方一行状态实时显示「听力 x% · 答对 n/m」，首页的开关仍然
  保留用于手动改 —— 详见[文章页自动打勾](#文章页自动打勾)。
- **每篇文章五个固定区域** —— `Article` / `Words` / `Questions` / `Answers` / `Continue`，
  顺序恒定，所有文章共用同一套模板、样式与脚本。
- **左上角返回目录** —— 每篇文章的左上角（编号与标题之上）都有一枚 `返回目录` 胶囊按钮，
  不必滚到底部的导航才能离开；它是真正的 `<a href="../index.html">`，带 `aria-label`、
  可键盘聚焦，并**刻意不吸顶** —— 顶部位置留给已经吸顶的播放器。
- **真实音频，不是模拟** —— HTML5 Audio 播放器直连真实 WAV。播放暂停、已播时间、总时长、
  实时进度、点击跳转、拖动定位、`0.75x` / `1x` / `1.25x` 倍速、音量、加载 / 结束 / 失败状态，
  全部由真实播放事件驱动。
- **先播放，再阅读** —— 播放器位于 `Article` 标题之下、**正文之上**，与正文之间有一条细分隔线
  且上下留出距离；阅读长文时吸顶，可以先点开音频，再顺着往下读，不必滚回顶部找控件。
- **朗读高亮** —— 读到哪句就把哪句加粗染色，拖动进度条、改倍速、往回拖都会跟着走；
  点任意一句即从该句开始播放。时间轴在构建时从 WAV 反推（TTS 工具不提供时间戳），
  所以不需要后端、也不需要运行时对齐 —— 详见[朗读高亮](#朗读高亮)。
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
├── content/                    # 文章唯一维护源（Markdown），按 Chapter 区间分子目录
│   ├── 0001-0025/
│   │   ├── 0001.A_New_Hobby.md
│   │   └── …                   # 每篇一个 .md
│   ├── 0026-0050/
│   │   └── …                   # **递归**扫描，子目录可有可无
│   └── 0051-0075/
│       └── …                   # 每 25 篇一个目录
├── sources/                    # 外部 TTS 工具生成的 WAV（与 md 同名）
│   ├── 0001.A_New_Hobby.wav
│   └── …                       # 0002、0003、… 每篇一个
├── assets/
│   ├── css/style.css           # 全站统一样式（桌面 + 移动）
│   ├── js/audio-player.js      # 音频播放器
│   ├── js/main.js              # 题目判分 / 页面交互
│   ├── js/progress.js          # 学习进度存储：localStorage + JSON 导出 / 导入（两处共用）
│   ├── js/study-completion.js  # 文章页：听完 ≥90% + 全部答对 ⇒ 自动标记完成
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
│   ├── test_frontend.py        # 在 Node 中真实执行判分逻辑
│   ├── test_progress.py        # 进度结构 + 纯逻辑（在 Node 中执行）
│   ├── test_progress_dom.py    # 用 jsdom 驱动进度交互（可选）
│   ├── test_auto_complete.py   # 自动打勾逻辑 + 生成结构
│   ├── test_auto_complete_dom.py  # 用 jsdom 驱动自动打勾（可选）
│   └── js/                     # 上面几个测试用到的 jsdom / Node 驱动脚本
├── watch.bat                   # Windows 双击即开始监听
├── apps/
│   ├── windows/                # 桌面端（WinForms + WebView2）+ publisher/ 发布产物
│   └── android/                # Android 端（系统 WebView）+ publisher/ 发布产物
├── requirements.txt
├── .gitignore
├── .gitattributes              # 仓库内 LF、*.bat 为 CRLF（见下方说明）
├── LICENSE
├── README.md                   # 英文文档（默认）
└── README-CH.md                # 本文件（简体中文）
```

> **行尾约定。** 仓库内一律存 LF，`*.bat` 签出为 CRLF（cmd.exe 只对 CRLF 可靠）。这不只是整洁
> 问题：`scripts/build.py` 永远写 LF，所以在 `core.autocrlf=true` 的机器上，全新 clone 会把
> **CRLF** 的 `src/*.html` 交给 `validate.py`，其字节级重建比对就会无端报 `FAIL` —— 这个假失败
> 已实际复现并加了防护。配置正确时 `git ls-files --eol src/0001.A_New_Hobby.html index.html`
> 应显示 `i/lf w/lf`；《本地静态服务器》一节里的字节数都是 **LF 计数**，与 GitHub Pages 实际
> 下发的字节一致。

> `tools/`（EnglishAudio 的 ~100 MB 打包产物）**不在仓库内**：体积大且已在其它仓库维护，
> 这里只按需调用。`.gitignore` 已忽略该目录，放进去也不会污染 `git status`。
> 见 [用 EnglishAudio 生成音频](#用-englishaudio-生成音频)。

目录职责边界：

| 路径 | 定位 | 可否手工编辑 |
|---|---|---|
| `content/` | 文章唯一维护源；**递归**扫描，可以按 `0001-0025/` 这类目录分组 | **是**，人工维护 |
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
content/0001-0025/0001.A_New_Hobby.md   # 目录只负责整理，不参与编号
src/0001.A_New_Hobby.html               # 构建生成，始终是平的
sources/0001.A_New_Hobby.wav            # 音频工具生成，始终是平的
```

> **目录只是整理用。** Chapter 分组仍然只看编号（`((n-1)//25)*25+1`），把同一篇放进
> `content/0002-0026/` 也还是落在同一个 Chapter。输出保持扁平（`src/*.html`、`sources/*.wav`），
> 这样源文件怎么归档都不会动到已经发出去的 URL。

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

- [catalogue](../index.html)
- [next chapter](./0002.A_Busy_Morning.md)
```

要点：

- 一级标题 `# ...` 是**原始标题**（不含编号）。
- 章节名大小写不敏感，`# Article` 与 `## Article` 两种层级都接受；
  `## Questions` 内部的 `## Q1` **不会**被当成新章节。
- `## Words` 表头列名按别名识别，3 列和 5 列都支持：
  `Word/单词`、`Pronunciation/IPA/音标/发音`、`词性/pos`、`中文释义/meaning/释义`、`例句/example`。
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
- `## Continues`（或 `## Continue`）会被构建忽略 —— 上一篇 / 下一篇与目录始终由构建生成，
  不需要人工维护。段内的链接只服务于**直接阅读 Markdown 的人**：目录指向 `../index.html`
  （站点首页就是目录，仓库里没有 `catalogue.md`），相邻文章指向 `./<编号>.<文件名>.md`。

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

▼ Chapter 0001–0025
    0001. A New Hobby
    …
```

*（目录按编号升序列出该 Chapter 的全部文章，这里只展示第一条。真实首页不做任何省略。）*

### 分组算法（`build.chapter_bounds` / `build.group_chapters`）

每 **25** 个编号划分为一个**固定**区间（`build.CHUNK`）。分组依据是编号的**数值**，与文章数量、
数组下标、排序位置无关：

```python
CHUNK = 25
start = ((number - 1) // CHUNK) * CHUNK + 1
end   = start + CHUNK - 1
```

| 编号 | 所属 Chapter |
|---|---|
| `0001` | Chapter 0001–0025 |
| `0025` | Chapter 0001–0025 |
| `0026` | Chapter 0026–0050 |
| `0050` | Chapter 0026–0050 |
| `0051` | Chapter 0051–0075 |

**只输出包含真实文章的 Chapter。** 中间缺号不会移动区间边界，也不会提前创建空分组。
新增文章后重建，新分组自动出现；删除某组最后一篇文章后重建，该组不再显示。

分组计算与 HTML 渲染是分离的（`group_chapters` → `render_index`），规则不会散落到模板里，
可以直接被单元测试调用。

### 折叠行为

- 使用语义化的原生 `<details>` / `<summary>`；鼠标与键盘均可操作，焦点状态可见。
- `Chapter 0001–0025`（第一组）**默认展开**；其他实际存在的 Chapter **默认折叠**。
- 每个 Chapter 独立控制，展开一个不会强制关闭其他。
- 收起 / 展开状态由箭头方向体现（`▸` / `▾`）。

---

## 学习进度

首页会记录每篇文章是否学完。所有数据都只存在浏览器里 —— 没有账号、没有后端、没有同步服务。
写入有两条路径：首页的勾选开关，以及**文章页在「听完音频 + 全部答对」后的自动标记**。

### 每篇标记与 Chapter 汇总

- 目录每一行在标题**右侧**有一个圆形开关：未完成是灰色空心圆，完成是绿色勾。标题链接行为不变；
  开关是独立的 `<button>`，带 `aria-pressed`、随状态变化的 `aria-label`，点击区 36 px
  （手机上 34 px）。
- 点开关既不跳转文章，也不展开 / 折叠 Chapter：处理函数里 `preventDefault()` +
  `stopPropagation()`，而且按钮本来就在 `<summary>` 之外。
- Chapter 标题右侧有自己的汇总：`已完成/总篇数`、**一条本章专属的进度条**，加同一对图标；
  只有**该 Chapter 里实际存在的每一篇**都完成后才变绿。进度条只按本章自己的文章算，
  在某一章勾选不会带动其他章；分母取自生成时的标记（`data-chapter-total`），**不假定 25 篇**；
  状态每次渲染都实时算，不存在「Chapter 完成标记」这种会发霉的字段。
- 新增文章自动以未完成状态出现，不需要任何配置：存储里只有「已完成编号的集合」，不是每篇一条记录。

### 文章页自动打勾

学完一篇不必再回首页：

- **两个条件同时成立**才算：音频听到 **≥ 90%**，**并且**全部题目判分为正确。只满足一个，
  除了页面上的状态行之外什么都不会变。
- **怎样算「听完」**：`audio-player.js` 按 `timeupdate` 累计**媒体秒数**，通过
  `dailylingo:listen` 事件上报比例。单步增量超过 1.5 s 的一律丢弃 —— `timeupdate` 大约 4 Hz，
  不丢的话拖一次进度条就会把跳过的整段算成听过，「拖到结尾」就能刷出完成。累计的是媒体时间
  而不是墙上时间，所以 0.75x / 1.25x 播放与 1x 的判定完全一致。
- **怎样算「全部答对」**：`main.js` 从判分状态（每个 `.question` 上的 `is-correct`）推导，
  每次检查 / 重做 / 改选项后都会广播一份 `dailylingo:quiz` 快照。改选项会清掉判分标记，
  因此改动过的题目在重新检查前不再计入「答对」。
- **只增不减**：已经完成的文章，之后改答案或重播都不会被取消 —— 撤销是明确动作，留给首页。
  写入是与现有集合求并集，不会覆盖你在别处做出的勾选。
- **看得见的反馈**：文章页头部有一行状态：初始是构建期的说明，之后随进度显示
  `听力 45% · 答对 3/5`，打勾成功变绿显示 `✅ 本篇已标记为完成`；`localStorage` 不可用时
  明确提示（带 `⚠️`）标记没能保存。
- **没有音频或没有题目 ⇒ 不会自动打勾**：两者都是前提，所以构建时会写
  `data-study-auto="false"`，页面一进来就说清楚，而不是给一个永远不成立的约定；
  这类文章仍可在首页手动勾选。

写入走的是与首页同一个 `markCompleted()`，所以自动标记和手动标记的存储结构完全一致 ——
下次打开首页就能看到那个绿勾。

### 首页统计

目录上方一张紧凑的卡片显示 `已完成 / 总数 · 百分比` 和一条 6 px 进度条
（`role="progressbar"`，`aria-valuenow` / `aria-valuetext` 同步，数字变化会被读屏温和播报）。
只统计真实文章 —— Chapter 标题、导航链接、品牌名都不算。文章数为 0 时显示 `0 / 0` 与 `0%`，
不会除零。数字是从目录同一份 DOM 算出来的，所以新增文章只要重新构建就自动计入总数，
已有记录不受影响。

### 设置对话框（左上角）

首页标题区左上角有一个齿轮按钮，打开原生模态 `<dialog>`（`showModal()`；`Esc`、点遮罩、
点关闭按钮都能关）。导出 / 导入就藏在里面，不占阅读视线。

- **导出**通过 `Blob` + `<a download>` 下载 `dailylingo-progress-YYYYMMDD.json`，内容只有
  结构版本号、已完成编号和时间戳 —— 不含正文、不含音频、不含任何个人信息。
- **导入**先读你选的文件、校验，然后给出**预览**再动手：文件里有效编号多少条、你当前多少条、
  两种模式各自的结果是什么。
- **合并**（默认）取并集，不会取消你已有的记录。**覆盖**以文件为准替换，**可能取消**记录，
  所以必须再确认一次才执行。
- JSON 非法、`schemaVersion` 不支持、结构不对、或者文件里的编号在本项目一个都不存在 —— 这些
  情况下现有进度一律不动，并给出明确提示。
- 编号是四位补零的字符串（`"0001"`）。不存在的编号会被忽略**并报数量**，格式非法的条目被跳过
  并计数，重复编号自动去重。
- **手机应用**：面板最下方是 Android 安装包直链（`apps/android/publisher/DailyLingo.apk?v=<指纹>`，
  带 `download` 属性），手机上点一下就把 APK 存到本地，再点开即可安装。安装包不在仓库里时整块
  **省略**，不在首页留一个点了 404 的死链。

### 存储结构

`localStorage["dailylingo_learning_progress_v1"]`：

```json
{
  "schemaVersion": 1,
  "completedArticles": ["0001", "0002", "0003"],
  "updatedAt": "2026-10-16T08:00:00.000Z"
}
```

- 用文章**编号**做身份，绝不用标题 —— 改标题不影响记录，改编号就不再对应。
- 保留前导零；超过四位的编号保留完整数字。
- 本地数据损坏时，原始内容先复制到 `dailylingo_learning_progress_v1__corrupt`，再重置为空白，
  并在页面上提示 —— 坏数据不会把首页带崩。
- 本地存储不可用（隐私模式 / 被禁用 / 配额满）时页面会明确提示，当前会话仍可正常勾选，
  只是刷新后会丢。

### 浏览器范围与迁移

`localStorage` 属于**某一个浏览器配置文件里的某一个来源**。两个浏览器、两部手机、Android
WebView、台式机加笔记本之间都不会同步，也不会上传到任何地方。JSON 导出 / 导入是唯一的迁移
途径。重新部署网站**不会**重置你浏览器里已有的记录 —— 浏览器是按来源存，不是按版本存。

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

### 朗读高亮

播放时**当前句会加粗并带淡蓝底色**，随播放往下走。快进方式不变 —— 拖动进度条、`←` / `→`、
`Home` / `End`、或直接点某一句 —— 高亮都会**立刻**跟着走，不会出现「快进后高亮还停在旧句子」。

**点句子即从该句开始播放**（原本暂停的话会自动开始）。鼠标选中文字再松开**不会**触发跳转，
否则想复制一个单词就会把音频拨回去。

时间从哪来 —— TTS 工具**不提供任何时间戳**，因此由 `scripts/timeline.py` 在构建时从 WAV 反推：

1. 用 10 ms **帧峰值**包络区分有声 / 静音（用峰值而不用 RMS：停顿里的 -60 dB 残余噪声会把
   RMS 拉高）；
2. 时长 ≥ 100 ms 的静音段成为**候选边界**。停顿是原子单位 —— 一次停顿最多承载一个边界，
   否则一次长段落停顿会把整句话吞掉；
3. 用动态规划为 N 句话恰好挑出 N-1 个边界，判据是每句话的**有声时长**（扣掉停顿）应与音节数成正比。

三个实际踩过的点：

- **用有声时长、不用墙钟时长**：逗号后的停顿会拉长墙钟时长，用它做先验会系统性把边界推长句一侧；
- **代价按每一段算，不用累计漂移**：累计口径允许某句被压扁、由邻句的漂移抵消 ——
  实测出现过「13 个音节挤进 0.87 秒」；逐段口径没有这个漏洞；
- **引号句 + 其后的短叙述语算一句**：`“Oh no! Where is my ticket?” she says.` 中间**没有停顿**，
  边界在音频里不可观测；硬切成两句会让优化器把边界丢到别处，后面所有句子跟着错位。

运行时不做任何计算 —— 时间轴以 `data-start` / `data-end` 属性随页面下发。音频缺失或无法分析
（比如不是 16 bit PCM）时，正文退回纯段落，只是没有高亮；播放器与其他功能照常。

### 用 EnglishAudio 生成音频

音频由外部工具生成 —— 构建脚本**不做** TTS、**不做**转码。本项目使用
**EnglishAudio**（Piper + ONNX，完全离线：不联网、不上传文本）。它可存在于两处：

- **系统 `PATH` 里** —— EnglishAudio 已加入系统环境，`EnglishAudio.exe` / `eaudio.cmd` 都能按名字
  直接调用。**本仓库不记录任何绝对路径**：各台电脑安装位置不同，写死一条只会在换机后失效；
- `<本仓库>/tools\eaudio.cmd` —— 可选兜底：把整包复制进来即可。`tools/` 已被 `.gitignore`
  忽略，因为整包约 100 MB（含 63 MB 语音模型）。

`scripts/watch.py --audio` 按下面的顺序定位它；都找不到时只重建网页并给出提示：

```text
--audio-tool <路径>  >  环境变量 DAILYLINGO_AUDIO_TOOL  >  <仓库>/tools/eaudio.cmd
                     >  PATH 里的 eaudio.cmd / EnglishAudio.exe / EnglishAudio
                     >  <仓库>/tools/eaudio.cmd
```

```bat
:: 单篇：读取 ## Article 章节 -> 生成同名 WAV
EnglishAudio.exe "content\0006.A_Visit_to_the_Library.md" --dist="sources"

:: 批量：把 content/ 下所有 md 一次转完
for %f in (content\*.md) do EnglishAudio.exe "%f" --dist="sources"

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

手工维护时不必反复敲构建命令：`watch.py` 轮询 `content/**/*.md` 与 `sources/*.wav`，
发现新增 / 修改 / 删除后自动重建 `index.html` 与 `src/*.html`。

| 命令 | 作用 |
|---|---|
| `python scripts/watch.py` | 监听并自动重建（默认 1 s 轮询） |
| `python scripts/watch.py --audio` | 顺带用 EnglishAudio 补齐缺失的 WAV |
| `python scripts/watch.py --once` | 只重建一次后退出（适合放进脚本 / Git hook） |
| `python scripts/watch.py --interval 0.5` | 调整轮询间隔 |
| `watch.bat`（双击） | Windows 上一键启动，等价于 `--audio` |

行为约定：

- **全量重建**（70 篇，时间轴缓存命中时进程内约 0.42 s；首次因为要分析音频里的句子时间轴约 4.85 s，
  之后按 WAV 的大小 / mtime 缓存，只有音频本身变了才重新分析）：新增或删除一篇文章会改变
  相邻文章的上一篇 / 下一篇，只重写「变化的那一页」会留下不一致的假象。
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

## 桌面端（Windows）

`apps/windows/` 是一个 WinForms 外壳：嵌 WebView2 直接打开线上站点，不复制任何内容。
启动先显示 `Lingo` 启动页，联网成功才切到主页；断网或连接超时则显示「请连接网络，当前无资源」。
学习进度会镜像到程序同目录的 `dailylingo-progress.json`，**格式与网页端导出完全一致**，
两边可以互相导入。

```bash
# 直接运行（需 .NET 8 桌面运行时 + WebView2 运行时）
apps\windows\publisher\DailyLingo.Desktop.exe

# 重新发布
cd apps/windows && dotnet publish -c Release -r win-x64 --self-contained false -o publisher
```

启动流程、进度同步机制、调试开关与已知边界见 [`apps/windows/README.md`](apps/windows/README.md)。

---

## Android 端

`apps/android/` 是一个系统 WebView 外壳：同样直接加载线上站点，启动流程与桌面端一致
（`Lingo` 启动页 → 联网成功才显示网页；断网 / 超时进「请连接网络，当前无资源」）。
学习进度镜像到应用私有目录的 `dailylingo-progress.json`，**与网页端导出逐字同构**（LF）。

```bash
cd apps/android
python tools/build_apk.py                        # 构建 publisher/DailyLingo.apk
adb install -r publisher/DailyLingo.apk          # 装到手机
adb shell am start -n com.dailylingo.app/.MainActivity
```

不依赖 Gradle：构建脚本直接调用 SDK 的 `aapt2 / javac / d8 / zipalign / apksigner`，
只用 Python 标准库。SDK 位置走 `ANDROID_SDK_ROOT`（或 `--sdk`），JDK 走 `JAVA_HOME`
（或 Android Studio 自带的 `jbr`）。

进度文件位置、双向同步细节、调试开关（`--ez force_offline true`）与已知边界见
[`apps/android/README.md`](apps/android/README.md)。

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
   content/0026-0050/0021.My_Weekend.md
   ```

   放进编号所属 Chapter 的目录即可（新区间就新建目录）；构建是递归扫描的，
   直接平铺成 `content/0021.My_Weekend.md` 也照样能用。文件名先随手给个占位也没关系 ——
   `python scripts/fix_content.py --apply` 会按 `# 标题` 改名，并顺带重写相邻文章的
   `previous` / `next`（`--check` 只报告不改）：

   ```bash
   python scripts/fix_content.py --check   # 只报要改什么，有需修项退出码 1
   python scripts/fix_content.py --apply   # 改名 + 重写链接，幂等
   ```

2. 写原始标题与正文：`# My Weekend`，然后 `## Article`。
3. 填 `## Words`（3 列或 5 列均可）、`## Questions`、`## Answers`。
4. 用 EnglishAudio 生成同编号 WAV 并放进 `sources/`（见
   [用 EnglishAudio 生成音频](#用-englishaudio-生成音频)）：

   ```bat
   EnglishAudio.exe "content\0021.My_Weekend.md" --dist="sources"
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

递归扫描 `content/` → 解析 Markdown 与元数据 → 校验编号 / 标题 / 结构 / 重复编号 / 文件名一致性 →
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
  文章总数：70
  Chapter 分组：3
    Chapter 0001–0025（默认展开）：25 篇
    Chapter 0026–0050（默认折叠）：25 篇
    Chapter 0051–0075（默认折叠）：20 篇
  警告：0 条
```

*（为可读性做了省略：真实输出每篇文章打印一行 `文章 NNNN …`，并在 Chapter 下逐条列出标题。）*

### 验证脚本

```text
$ python scripts/validate.py
结果：PASS 3142 / FAIL 0 / WARN 0
```

覆盖：文章数据；编号唯一性与升序；Chapter 区间边界与「只输出有真实文章的 Chapter」；
首页含品牌名、进度卡与折叠目录（并做摘要 / 难度 / 音频状态的**反向**检查）；第一个 Chapter 默认展开；
五个区域顺序；**每篇左上角都有 `返回目录` 链接且排在 `<h1>` 之前**；**播放器位于 `Article` 区内、标题之下、第一段正文之上**；**播放器与正文之间有分隔线**；
**播放器控件为音量 + 恰好三档倍速（`0.75x` / `1x` / `1.25x`，无 ±5 秒）**（仅对**已有 WAV** 的页面
断言 —— 尚未生成音频的页面反过来必须**不输出任何播放器控件**，只留 `player-unavailable` 提示）；
**正文逐句带时间轴：严格递增、首尾相接、从 0 开始且结束时间正好等于 WAV 时长，且句子拼回去
与原文逐字一致**；
**图标文件存在、PNG/SVG 有效、每个页面都以正确相对前缀声明**；浏览器标签与主标题一致性；
单词表行数；题目数量；判分数据与 Answers 同源；Answers 默认折叠；上一篇 / 下一篇链接与标题；
首末篇边界；无绝对根路径；静态资源存在性；重复构建字节级一致（若差异**纯粹来自行尾**，会直接
点明是行尾问题，而不是报一个语焉不详的字节不一致）；**进度卡、每篇恰好一个完成按钮
（全部初始未完成）、统计总数与进度条上限等于真实文章数、各 Chapter 汇总篇数等于该章真实
篇数、设置对话框及其导出 / 导入控件、`progress.js` 带存储键与 schema 版本且不含任何
网络请求**；**每个文章页都声明 `data-article-id` 与学习状态行、`data-study-auto` 与该篇是否
真的有音频与题目一致、两个新脚本都带内容指纹、收听 / 判分事件名在收发两侧完全一致、
自动完成脚本不发网络请求**。

### 自动化测试

```text
$ pytest -q
517 passed in 37.2s
```

| 文件 | 用例数 | 覆盖内容 |
|---|---|---|
| `tests/test_build.py` | 110 | 文章解析（缺编号 / 缺标题 / 编号非法 / 重复编号 / 编号与文件名不一致 / 中文与特殊字符）、编号显示规则（含超过四位）、Chapter 边界（`0001`/`0025`/`0026`/`0050`/`0051`/`0075`/`9999`/`10001`，即每章 25 篇）、缺号仍正确分组、空 Chapter 不显示、组内升序、第一组默认展开、新增文章产生新分组、删除最后一篇后分组消失、首页链接可解析、标题全站一致、浏览器标签含编号、上一篇 / 下一篇与首末边界、导航与分组无关、单词表 3 列与 5 列、题型推断、紧凑答案串、**编号答案列表（`1. **B. …** 解释`，含被转义的 `1\.` 写法，题干与答案都测）、`extract_choice_key` 的 11 组边界（`cook` 不被当成 `C`）**、`题型：填空` + 多可接受答案、`______` 保留、非法答案配置可被识别、缺答案报错、Answers 默认折叠、判分数据与答案一致、`normalize_answer` 边界、**播放器位于正文之前（有 / 无 WAV 两种情形）**、**播放器与正文之间有分隔线**、**无 ±5 秒按钮且恰好三档倍速**、**图标声明前缀正确、首页品牌图标、图标资产的 PNG/SVG 有效性与尺寸**、缺音频只警告不影响其他区域、CSS/JS/音频相对路径、**CSS/JS 的 URL 带内容指纹（`?v=` + 8 位十六进制）**、GitHub Pages 子路径、构建可重复、**在 `content/<chapter>/` 子目录下递归发现文章（只有子目录、平铺与子目录混放、隐藏目录被忽略、两个目录里出现同一编号仍然报错）** |
| `tests/test_frontend.py` | 7 | 在 Node 中真实执行 `assets/js/main.js`：单选正确 / 错误 / 空选、大小写不敏感、首尾空格、尾部标点、多个可接受答案、空白输入不判正确；并与 `build.normalize_answer` 做逐样本一致性比对 |
| `tests/test_progress.py` | 32 | 学习进度的首页结构（每篇一个完成按钮且初始未完成、统计总数 / `aria-valuemax` / Chapter 汇总等于真实篇数、设置对话框与导出导入控件、Android 安装包直链带 `download` 与内容指纹且 APK 缺失时整块省略、空站点渲染 `0 / 0`）**外加在 Node 中真实执行的纯逻辑**：编号补零、文件校验（JSON 语法 / `schemaVersion` / 结构）、去重与非法条目计数、忽略不存在编号、合并取并集、统计不除零、按真实篇数判定 Chapter 完成、导出载荷结构与文件名、导出内容可被导入解析器读回 |
| `tests/test_progress_dom.py` | 18 | 在 **jsdom** 中用真实 click 事件与真实 `localStorage` 驱动生成的首页：首次访问为空、勾选同步统计与存储、取消回退、Chapter 全完成才变绿、**每章的进度条与计数各自独立（用合成的「两章」站点验证：勾第一章不动第二章）**、刷新恢复、损坏数据隔离、存储禁用降级、导入预览、合并、覆盖需二次确认、取消覆盖、非法 JSON / 不支持版本不改动进度、未知编号忽略并计数、导出载荷与对话框开关。未安装 jsdom 时自动跳过 |
| `tests/test_timeline.py` | 163 | `scripts/timeline.py`：切句（`Mrs.` 缩写、引号内的句末标点、引号后的叙述语并回、引号后真正的新句子不并）、**对每篇文章的每一段**验证切分不丢字、音节估算、合成 WAV 上的静音检测、DP 选中「最接近音节比例」的停顿、完全没有停顿时退回网格、时间轴覆盖整段音频、逐句首尾相接、8 bit / 缺失音频时优雅返回空、真实文章 × 真实音频的一致性、以及构建是否真的输出 `data-start` / `data-end`（缺音频时退回纯段落） |
| `tests/test_content_links.py` | 142 | Markdown 源里每个 `## Continue` 段：每条相对链接都能在磁盘上解析、previous / next 等于**编号相邻**的上一篇 / 下一篇（跨 Chapter 目录也算）、首篇 previous 与末篇 next 都指回首页、并单独校验 `0025` ↔ `0026` 这条跨目录（`0001-0025/` → `0026-0050/`）的边界 |
| `tests/test_fix_content.py` | 15 | `scripts/fix_content.py`：slug 规则（撇号丢弃、标点去掉、空格转下划线）、**仓库里每篇的文件名都等于 `slugify(标题)`**、占位文件名会被改名、跨 Chapter 目录的链接会重算、再跑一次不产生任何变化、`--check` 只报不改、重复编号与缺 `# 标题` 会被拒绝 |
| `tests/test_player_dom.py` | 9 | 在 **jsdom** 中用替身 `Audio` 驱动生成的文章页：播放前不高亮、高亮跟随 `currentTime`（0 / 2 / 4 秒 → 第 0 / 1 / 2 句）、点句子跳到句首并开始播放、选中文字时点击不跳转、快退后高亮回退、始终只有一句处于高亮。未安装 jsdom 时自动跳过 |
| `tests/test_auto_complete.py` | 8 | 在 Node 里**不带 DOM**执行 `audio-player.js` 与 `study-completion.js`：收听累计（第一拍只记基准、正常 0.25 s 累加、恰好 1.5 s 仍算、向前 / 向后跳转丢弃、时间不动不加）与完成判定边界（0.89 不算、0.90 算、错一题不算、无题目不算、无快照不算）；外加生成结构 —— 每页的 `data-article-id`、`data-study-auto` 是否与「真的有音频且真的有题目」一致、两个脚本都带指纹、首页手动开关仍在 |
| `tests/test_auto_complete_dom.py` | 13 | 在 jsdom 里用真实的 `main.js` / `progress.js` / `study-completion.js` 驱动**生成的文章页**：首次进入不动、只答题不完成、只听不完成、听一半不完成、听完且全对即标记并落库、反过来先听完再答题也打勾、重开显示已完成、完成后改答案不撤销、写入与已有记录取并集、坏数据先留档再标记、存储不可用明确报错。文章编号与题目数从构建结果读取，不写死；没装 jsdom 时整组 skip |

测试全部使用临时目录，不会污染或覆盖真实的 `content/` 与 `sources/`。
`test_progress_dom.py` 额外需要本机装有 `jsdom`；它只是开发期辅助工具（不是站点依赖），
找不到时整个文件自动 skip。

### 本地静态服务器

```text
$ python -m http.server 8123
200 25185  text/html              <- /
200 9916   text/html              <- /src/0001.A_New_Hobby.html
200 …                               <- /src/0002 … 0020（每篇文章一个页面）
200 25081  text/css               <- /assets/css/style.css
200 7291   application/javascript <- /assets/js/main.js
200 9610   application/javascript <- /assets/js/audio-player.js
200 26252  application/javascript <- /assets/js/progress.js
200 919    image/svg+xml          <- /assets/images/favicon.svg
200 942    image/png              <- /assets/images/favicon-32.png
200 4682   image/png              <- /assets/images/favicon-180.png
200 1641488 audio/wav             <- /sources/0001.A_New_Hobby.wav
200 …                               <- /sources/0002 … 0020（每篇文章一个 WAV）
```

*（做了省略：全部 150 条路径——首页 + 70 个文章页、70 个 WAV、共享静态资源与 Android 安装包——都真实请求过且全部
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

GitHub Pages 上返回的首页列出的正是仓库里的全部文章，归属于 `Chapter 0001–0025`。
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
- **验证脚本在「无音频页」上误报失败**：`validate.py` 对**每个**页面都断言「音量 + 三档倍速」，
  但尚未生成音频的页面只渲染 `player-unavailable` 提示、根本不输出控件，于是 `rates=[]` 被判
  `FAIL`（新增 `0009` 后、生音频之前暴露出来）。现在按分支断言：有播放器就查三档倍速且无 ±5 s
  按钮，没有播放器就查页面里不出现任何播放器控件。
- **音频工具被写成了绝对路径**：`watch.py` 的兜底路径写死了 EnglishAudio 在某块盘上的位置，
  工具一挪或换台电脑就失效 —— 实际已经因此坏过两次。现在工具本身已加入系统 `PATH`，
  `resolve_audio_tool()` 改为**按名字查找**（`eaudio.cmd` / `EnglishAudio.exe` / `EnglishAudio`），
  **仓库里不再记录任何绝对路径**。实测：本机能解析到，`watch.py --once` 重建 70 篇耗时 5770 ms。
- **冲着「构建字节级可复现」来的行尾陷阱**：本机开着 `core.autocrlf=true` 而仓库没有
  `.gitattributes`，全新 clone 会把 `src/*.html` 签出成 **CRLF**，而 `build.py` 永远写 LF。
  在临时目录里把那 10 个生成页面改成 CRLF 复现：`validate.py` 对一个完全正常的站点报了 10 个
  `FAIL`。已通过提交 `.gitattributes`（`* text=auto eol=lf`、`*.bat text eol=crlf`、二进制资产
  标 `binary`）修复，并把索引里仍是 CRLF 的 7 个 `content/*.md` renormalize 成 LF；同时让
  `validate.py` 把「只有行尾不同」的情况**显式点出来**，而不是闷着报字节不一致。

---

## 尚未完成与需人工验证的事项

自动化测试能证明的部分已在上文列出。以下项目**未**在本机执行，因此不做「已验证」的声明：

1. **真实浏览器交互未做端到端自动化**：`pytest` 里没有浏览器用例（本次的朗读高亮例外，
   见第 8 条 —— 它是用本机无头 Chromium 手工驱动验证的，但没有进测试套件），
   因此「点击 Chapter 展开收起、拖动进度条跳转、切换倍速、输入答案点检查答案」这些交互
   没有跑过自动化用例。已做的是：判分规则在 Node 中逐条真实执行（见上文），
   生成 HTML 的结构与语义（`<details>` / `<summary>` / `role="slider"` / `aria-live` /
   `aria-controls`）由 `validate.py` 静态断言。请按[本地预览](#本地预览)在浏览器里手工过一遍。（后来加的学习进度交互已由 jsdom 真实驱动，
   见第 7 条。）
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
7. **学习进度界面只在 DOM 层面验证过，没有在真实浏览器里看过像素**：行为有真覆盖 ——
   `tests/test_progress_dom.py` 用真实 click 事件和真实 `localStorage` 驱动生成的首页；
   但本环境无法启动浏览器，所以齿轮位置、6 px 进度条、两种图标状态、以及 390 px 宽下的
   对话框，仍值得按[本地预览](#本地预览)亲手看一眼。

8. **朗读高亮「准不准」最终要靠人耳**：时间轴不是 TTS 给的，而是从 WAV 的静音结构 + 音节比例
   反推出来的 —— 边界落在停顿上，量级误差约 0.1–0.3 s，极短的句子（如 `Who knows?`）可能一闪而过。
   本机已用无头 Chromium 实测：高亮随播放前进、拖到 80% 后立即跳到对应句、点句子从该句播放、
   1.25 倍速、键盘快退、长文自动滚动、390 px 移动端截图；**但「读的与高亮的是不是同一句」仍需
   按[本地预览](#本地预览)亲耳听一遍**，尤其是音频与正文已经不同步的文章（见上文「改了正文必须
   重新生成 WAV」）。

9. **自动打勾的「听了多少」是靠算术与事件接线验证的，没有真的放音**：累计函数有独立单测
   （`addListenStep`），整条流程也在 jsdom 里用合成的 `dailylingo:listen` / `dailylingo:quiz`
   事件驱动过，但本次环境没有浏览器与声卡，所以 0.75x / 1.25x 下真实的 `timeupdate` 节奏、
   以及 `ended` 是否恰好在预期时刻触发，都没有实测。两个阈值都是单个具名常量 ——
   `assets/js/study-completion.js` 的 `REQUIRED_RATIO` 与 `assets/js/audio-player.js` 的
   `LISTEN_STEP_LIMIT` —— 想调只需改一行，`validate.py` 会断言比例仍是 0.9。

---

**[English](README.md) | [简体中文](README-CH.md)**
