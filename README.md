# DailyLingo

每日英语学习网站：英文阅读 + WAV 朗读 + 重点单词 + 阅读理解练习 + 文章导航。

纯静态站点 —— **无登录、无数据库、无后端、无远程 API**，构建产物直接部署到 GitHub Pages。

- 前端：HTML5 + CSS3 + 原生 JavaScript（不引入 React / Vue 等框架）
- 文章源：Markdown（唯一维护入口）
- 构建 / 验证：Python 3（**只使用标准库**）
- 自动化测试：pytest（含在 Node 中执行的前端判分逻辑测试）
- 音频：外部工具生成的 WAV，用 HTML5 Audio API 播放
- 部署：GitHub Pages（项目站点，全站相对路径）

---

## 一、目录结构

```text
DailyLingo/
├── index.html                  # 首页（由构建脚本生成）：品牌名 + Chapter 折叠目录
├── src/                        # 文章详情页（由构建脚本生成）
│   ├── 0001.A_New_Hobby.html
│   ├── 0002.A_Busy_Morning.html
│   ├── 0003.Helping_a_Neighbor.html
│   └── 0004.A_Day_at_the_Beach.html
├── content/                    # 文章唯一维护源（Markdown）
│   ├── 0001.A_New_Hobby.md
│   ├── 0002.A_Busy_Morning.md
│   ├── 0003.Helping_a_Neighbor.md
│   └── 0004.A_Day_at_the_Beach.md
├── sources/                    # 外部工具生成的 WAV（与 Markdown 同名）
│   ├── 0001.A_New_Hobby.wav
│   ├── 0002.A_Busy_Morning.wav
│   ├── 0003.Helping_a_Neighbor.wav
│   └── 0004.A_Day_at_the_Beach.wav
├── assets/
│   ├── css/style.css           # 全站统一样式（桌面 + 移动）
│   ├── js/audio-player.js      # 音频播放器
│   ├── js/main.js              # 题目判分 / 页面交互
│   └── images/
├── scripts/
│   ├── build.py                # 构建脚本（解析 → 分组 → 生成页面 → 关联音频）
│   └── validate.py             # 项目验证脚本
├── tests/
│   ├── conftest.py
│   ├── test_build.py           # 构建 / 数据 / 分组 / 标题导航 / 题目答案 / 路径
│   └── test_frontend.py        # 前端判分逻辑（在 Node 中执行 assets/js/main.js）
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

目录职责边界：

| 目录 | 定位 | 可否手工编辑 |
|---|---|---|
| `content/` | 文章唯一维护源 | **是**，人工维护 |
| `src/` | 构建生成的文章 HTML | 否，重新构建即覆盖 |
| `index.html` | 构建生成 | 否，重新构建即覆盖 |
| `sources/` | 外部工具生成的 WAV | 由音频工具写入 |
| `assets/` | 全站公共 CSS / JS | 是 |

---

## 二、环境要求与安装

| 项目 | 要求 | 实测版本 |
|---|---|---|
| Python | 3.9+（构建脚本只依赖标准库） | 3.13.12 |
| pytest | 仅在跑测试时需要 | 9.1.1 |
| Node.js | 仅在跑 `tests/test_frontend.py` 时需要（缺失时自动跳过） | 22.22.2 |

```bash
python -m pip install -r requirements.txt
```

> 构建和验证脚本自身**不需要**任何第三方包；`requirements.txt` 里的 pytest 只为测试服务。

---

## 三、常用命令

```bash
# 1) 构建站点（生成 index.html 与 src/*.html）
python scripts/build.py

# 带逐篇明细
python scripts/build.py --verbose

# 2) 验证生成结果与数据一致性
python scripts/validate.py

# 3) 自动化测试
pytest -q

# 4) 本地预览（详见第六节）
python -m http.server 8000
```

---

## 四、文章编号与命名规则

### 4.1 编号

- 编号是**永久 ID**，不随标题、正文或排序变化；按数值升序排列；不允许重复。
- 默认显示为四位，不足补零：`0001`、`0002`、`0010`、`0100`、`0101`。
- 超过四位的编号**保留完整数字，不截断**：`10000`、`123456`。
- 文件名、元数据（front matter 的 `id`）与编号必须一致，否则构建直接报错。

### 4.2 文件命名

```text
content/0001.A_New_Hobby.md
src/0001.A_New_Hobby.html      （构建生成）
sources/0001.A_New_Hobby.wav   （音频工具生成）
```

### 4.3 标题生成

原始标题**不含编号**，编号由统一逻辑添加，全站共用同一套实现
（`build.display_title` / `build.page_title`）：

| 位置 | 内容 |
|---|---|
| 首页列表 | `0001. A New Hobby` |
| 文章页 `<h1>` | `A New Hobby`（配上方独立的编号显示） |
| 浏览器标签 | `0001. A New Hobby \| DailyLingo` |
| 上一篇 / 下一篇导航 | `上一篇：0001. A New Hobby` |

首页、文章页、浏览器标签、前后篇导航都调用同一函数，不存在手工硬编码的标题。

---

## 五、Markdown 文章格式

### 5.1 兼容格式（当前 `content/` 采用）

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
- 章节名大小写不敏感，也支持 `# Article`（一级）与 `## Article`（二级）两种层级；
  `## Questions` 内部的 `## Q1` 属于题目区，**不会被当成新章节**。
- `## Words` 表头列名按别名识别，3 列和 5 列都支持：
  `Word/单词`、`Pronunciation/音标`、`词性/pos`、`中文释义/meaning`、`例句/example`。
  单元格里的 `**粗体**` 会被剥离。
- `## Answers` 支持三种写法（可混用）：
  1. 紧凑字母串 —— 按题目顺序逐题赋答案：`BAC`、`ACBBA`、`CABABB`；
  2. 单题行 —— `Question5: He feels happy because he has helped someone.`；
  3. 分块 —— `## Q1` + `答案：B` + `解释：…` + `可接受答案：cook, to cook`。
- `## Continues` 会被构建忽略（上一篇 / 下一篇与目录全部自动生成，不需要人工维护）。

### 5.2 题型

| 题型 | 判定方式 | 判分 |
|---|---|---|
| 单选 | 题干下有 `A. / B. / C. …` 选项，或显式写 `题型：单选` | 选项字母比对（忽略大小写） |
| 填空 | 题干下没有选项，或显式写 `题型：填空` | 与「答案 / 可接受答案」比对，**忽略大小写、忽略首尾空白、忽略尾部标点；空白输入永远不判为正确** |

题干中的 `______`（连续下划线）会被**完整保留**，不会被误当成 Markdown 强调语法。

### 5.3 可选：YAML Front Matter

```markdown
---
id: "0005"
title: "Some Title"
audio: "0005.Some_Title.wav"
---
```

三项都可省略：`id` 默认取文件名前缀（写了则必须与文件名一致），
`title` 默认取 `# 一级标题`，`audio` 默认取 `<编号>.<文件名标题>.wav`。

---

## 六、首页：Chapter 折叠目录

首页**只显示**两样东西：`DailyLingo` 品牌名，以及按 Chapter 分组的可折叠文章目录。
不显示摘要、难度、音频状态、文章数量统计或任何其他信息。

```text
DailyLingo

▼ Chapter 0001–0100
    0001. A New Hobby
    0002. A Busy Morning
    0003. Helping a Neighbor
    0004. A Day at the Beach
```

### 6.1 分组算法（`build.chapter_bounds` / `build.group_chapters`）

每 100 个编号划分为一个**固定**区间，分组依据是编号的**数值**，不是文章数量、
数组下标或排序位置：

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

**只输出包含真实文章的 Chapter** —— 中间缺号不改变区间边界，也不会提前创建空分组。
新增文章后重新构建会自动出现新分组；删除某组最后一篇文章后重新构建，该组不再显示。

当前仓库只有 `0001`–`0004`，因此首页**只显示 `Chapter 0001–0100`**。

分组计算与 HTML 渲染分离（`group_chapters` → `render_index`），规则不散落在模板里，
可以直接被单元测试调用。

### 6.2 折叠行为

- 使用语义化的原生 `<details>` / `<summary>`，鼠标与键盘均可操作，焦点状态可见。
- `Chapter 0001–0100`（第一组）**默认展开**，其他实际存在的 Chapter **默认折叠**。
- 每个 Chapter 独立控制，展开一个不会强制关闭其他。
- 收起 / 展开状态由箭头方向体现（`▸` / `▾`）。

---

## 七、文章详情页：固定五个区域

按固定顺序渲染，所有文章共用同一套模板与 CSS / JS：

| # | 区域 | 内容 |
|---|---|---|
| 1 | **Article** | 编号、标题、英文正文、WAV 播放器 |
| 2 | **Words** | 单词表（单词 / 音标 / 词性 / 中文释义 / 例句），窄屏下表格自身横向滚动，**不会导致整页横向滚动** |
| 3 | **Questions** | 单选 + 填空，原生 JavaScript 判分，无需后端 |
| 4 | **Answers** | 默认**折叠**，用户主动展开后显示答案、可接受答案与解释 |
| 5 | **Continue** | 返回目录、上一篇、下一篇（显示目标文章的真实编号与标题） |

- 题目 ID 全局唯一（`Q1`、`Q2`…），答案通过 ID 与题目关联。
- 自动判分用的正确答案内嵌在页面 `#quiz-data` 中，**与 Answers 区域同源**，
  因此修改文章答案后重新构建，两者自动同步。
- 首篇文章不生成上一篇链接，末篇文章不生成下一篇链接（显示「上一篇：无」等文字，而不是死链）。
- 上一篇 / 下一篇按**编号数值升序**计算，与首页 Chapter 分组完全独立。

---

## 八、音频播放器

使用真实 WAV 文件与 HTML5 Audio API，**所有显示状态都与真实播放状态同步**，
不存在模拟进度条或伪造播放状态。支持：

- 播放 / 暂停
- 当前播放时间、音频总时长、实时播放进度
- 点击进度条跳转、按住拖动进度条调整播放位置（Pointer Events，触屏可用）
- 进度条支持键盘操作：`←` / `→` 5 秒（`Shift` 10 秒）、`Home` / `End`、`Space` / `Enter` 播放暂停
- 后退 5 秒 / 前进 5 秒
- `0.75x` / `1x` / `1.25x` / `1.5x` / `2x` 倍速
- 音量调节
- 状态提示：正在加载 / 缓冲中 / 已就绪 / 正在播放 / 已暂停 / 播放结束
- 音频缺失或加载失败时的明确错误提示

音频时长尚未加载或不可获取时，时长显示为 `--:--`，页面其余部分不受影响。

**某篇文章缺少 WAV 时**：播放器位置显示缺失提示，而 Article 正文、Words、Questions、
Answers、Continue **全部照常可用**，构建只输出警告、不中断其他页面。

### 8.1 用 009.ai_voice 生成 WAV

音频由外部工具生成，构建脚本**不做** TTS、**不做**音频转码。本项目使用
`D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice`（Piper + ONNX 本地离线女声）：

```bash
# 单篇：读取 Markdown 的 ## Article 章节 → 生成与 md 同名的 WAV
"D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd" \
  "D:\user_project\git\DailyLingo\content\0001.A_New_Hobby.md" \
  --dist="D:\user_project\git\DailyLingo\sources"

# 批量：把 content/ 下所有 md 一次转完
cd /d D:\user_project\git\DailyLingo\content
for %f in (*.md) do "D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd" "%f" --dist="..\sources"
```

该工具只朗读 `## Article` 章节，`## Words` / `## Questions` / `## Answers` / `## Continues`
不会被读出来；正文含非英文字符会被直接拒绝（退出码 4），Markdown 必须是 UTF-8。

本仓库 4 个 WAV 均由该工具生成，实测参数：

| 文件 | 声道 / 位深 / 采样率 | 时长 | 大小 |
|---|---|---|---|
| `0001.A_New_Hobby.wav` | 单声道 / 16 bit / 22 050 Hz | 37.22 s | 1 641 488 B |
| `0002.A_Busy_Morning.wav` | 单声道 / 16 bit / 22 050 Hz | 46.37 s | 2 044 944 B |
| `0003.Helping_a_Neighbor.wav` | 单声道 / 16 bit / 22 050 Hz | 50.43 s | 2 224 164 B |
| `0004.A_Day_at_the_Beach.wav` | 单声道 / 16 bit / 22 050 Hz | 56.23 s | 2 479 932 B |

---

## 九、GitHub Pages 路径兼容

站点部署在**项目子路径**下，例如 `https://zc110747.github.io/DailyLingo/`。

- 全部链接与资源引用都是**相对路径**，没有任何以 `/` 开头的站点根路径：
  - 首页 → 文章：`src/0001.A_New_Hobby.html`
  - 文章 → 首页：`../index.html`
  - 文章 → 资源：`../assets/css/style.css`、`../assets/js/*.js`
  - 文章 → 音频：`../sources/0001.A_New_Hobby.wav`
  - 上一篇 / 下一篇：同目录文件名
- `scripts/validate.py` 会检查生成结果中不存在 `href="/..."` / `src="/..."`。
- 不依赖后端路由、服务器重写或动态 API，本地静态服务器与 GitHub Pages 行为一致。

---

## 十、本地运行

```bash
python scripts/build.py
python -m http.server 8000
```

浏览器打开：

- 首页：<http://localhost:8000/>
- 示例文章：<http://localhost:8000/src/0001.A_New_Hobby.html>

> `python -m http.server` 不支持 HTTP Range 请求（实际部署的 GitHub Pages 支持）。
> 浏览器会把整个 WAV 下载完再播放，因此本地预览时的拖动跳转体验与线上略有差异，
> 功能本身不受影响。

---

## 十一、GitHub Pages 部署

1. `python scripts/build.py && python scripts/validate.py && pytest -q` 全部通过。
2. 提交并推送（**构建产物 `index.html` 与 `src/*.html` 必须一起提交**）。
3. 打开仓库 **Settings → Pages**。
4. **Source** 选择 *Deploy from a branch*。
5. **Branch** 选择 `main`，目录选择 `/ (root)`。
6. 保存，等待发布完成。
7. 打开实际发布地址（例如 `https://zc110747.github.io/DailyLingo/`），逐项检查：
   首页 → Chapter 折叠展开 → 文章正文 → 音频播放与倍速 → 单词表 → 练习题判分 →
   展开 Answers → 上/下一篇导航。

若仓库使用其他分支或部署方式，按实际配置调整。

---

## 十二、新增一篇文章

1. 在 `content/` 新建 Markdown，文件名用**未占用的编号**：

   ```text
   content/0005.My_Weekend.md
   ```

2. 写原始标题与正文：`# My Weekend`、`## Article`。
3. 填 `## Words`（3 列或 5 列均可）、`## Questions`、`## Answers`。
4. 用外部工具生成同编号 WAV 并放进 `sources/`（见 8.1）。
5. 重建与自检：

   ```bash
   python scripts/build.py --verbose
   python scripts/validate.py
   pytest -q
   ```

6. 浏览器里检查页面与音频，然后提交推送。

新增后**自动完成**：首页文章列表、Chapter 分组（必要时新增分组）、文章主标题、
浏览器标签标题、上一篇 / 下一篇导航、WAV 关联。
**不需要**手工修改 `index.html`、Chapter 分组或其他文章的导航。

---

## 十三、构建脚本的边界

`scripts/build.py` 会做：

扫描 `content/` → 解析 Markdown 与元数据 → 校验编号 / 标题 / 结构 / 重复编号 /
文件名一致性 → 按编号升序 → 计算 Chapter 分组 → 只输出有真实文章的分组 →
第一组默认展开 → 生成 `index.html` → 生成全部文章 HTML → 统一生成主标题与浏览器标签 →
生成单词表 / 练习题 / 答案 → 关联 WAV → 生成上一篇与下一篇 → 检查导航目标与资源路径 →
缺失音频输出警告 → 非法数据输出明确错误 → 输出构建摘要。

`scripts/build.py` **不会**做：生成语音、调用 TTS、把 WAV 转成 MP3、
生成没有真实文章的 Chapter、生成虚构文章或占位链接、在首页显示摘要 / 难度 / 音频状态、
在各页面重复硬编码标题、因单篇缺音频而阻止其他页面构建。

构建是**可重复**的：输入不变时多次构建的输出字节级一致（`validate.py` 会把站点
重新构建到临时目录并与磁盘上的产物逐字节比对）。

---

## 十四、实际执行结果

以下均为本机实测（Windows 10 19045 / Python 3.13.12 / Node 22.22.2）。

### 14.1 构建

```text
$ python scripts/build.py --verbose
  文章 0001  A New Hobby          |  3 词  3 题  |  音频 有
  文章 0002  A Busy Morning       |  4 词  5 题  |  音频 有
  文章 0003  Helping a Neighbor   |  4 词  5 题  |  音频 有
  文章 0004  A Day at the Beach   |  7 词  6 题  |  音频 有
DailyLingo 构建完成
  文章总数：4
  Chapter 分组：1
    Chapter 0001–0100（默认展开）：4 篇
  警告：0 条
```

### 14.2 验证脚本

```text
$ python scripts/validate.py
结果：PASS 146 / FAIL 0 / WARN 0
```

覆盖：文章数据、编号唯一性与升序、Chapter 区间边界与「只输出有真实文章的 Chapter」、
首页只含品牌名与折叠目录（并检查不含摘要 / 难度 / 音频状态等）、
第一个 Chapter 默认展开、五个区域顺序、浏览器标签与主标题一致性、
单词表行数、题目数量、判分数据与 Answers 同源、Answers 默认折叠、
上一篇 / 下一篇链接与标题、首末篇边界、无绝对根路径、静态资源存在性、重复构建字节级一致。

### 14.3 自动化测试

```text
$ pytest -q
84 passed in 3.69s
```

| 文件 | 用例数 | 覆盖内容 |
|---|---|---|
| `tests/test_build.py` | 80 | 文章解析（含缺编号 / 缺标题 / 编号非法 / 重复编号 / 编号与文件名不一致 / 中文与特殊字符）、编号显示规则（含超过四位）、Chapter 边界（0001/0100/0101/0200/0201/0300/301/9999/10001）、缺号仍正确分组、不存在的 Chapter 不显示、组内升序、第一组默认展开、新增文章产生新分组、删除最后一篇后分组消失、首页链接可解析、标题全站一致、浏览器标签含编号、上一篇 / 下一篇与首末边界、导航与分组无关、单词表 3 列与 5 列、题型推断、紧凑答案串、`题型：填空` + 多可接受答案、`______` 保留、非法答案可被识别、缺答案报错、Answers 默认折叠、判分数据与答案一致、`normalize_answer` 边界、缺音频只警告不影响其他区域、CSS/JS/音频相对路径、GitHub Pages 子路径、构建可重复 |
| `tests/test_frontend.py` | 4 | 在 Node 中真实执行 `assets/js/main.js`：单选正确 / 错误 / 空选、大小写不敏感、首尾空格、尾部标点、多个可接受答案、空白输入不判正确；并与 `build.normalize_answer` 做逐样本一致性比对 |

测试全部使用临时目录，不会污染或覆盖真实的 `content/` 与 `sources/`。

### 14.4 本地静态服务器

```text
$ python -m http.server 8123
200 1371   text/html            <- /
200 9683   text/html            <- /src/0001.A_New_Hobby.html
200 12912  text/html            <- /src/0002.A_Busy_Morning.html
200 12626  text/html            <- /src/0003.Helping_a_Neighbor.html
200 14727  text/html            <- /src/0004.A_Day_at_the_Beach.html
200 15703  text/css             <- /assets/css/style.css
200 7291   application/javascript <- /assets/js/main.js
200 9894   application/javascript <- /assets/js/audio-player.js
200 1641488 audio/wav           <- /sources/0001.A_New_Hobby.wav
```

### 14.5 开发过程中发现并修复的真实缺陷

- **`______` 被 Markdown 强调规则吃掉**：`strip_markdown` 原本处理 `_斜体_`，
  把填空题干的连续下划线替换掉了，题目文本变成 `very __.`。
  已移除下划线强调规则（`**粗体**` / `*斜体*` 保留），并加了回归测试。
- **`## Q1` 子标题把题目区提前截断**：章节切分原先只认二级标题，
  遇到无法识别的 `## Q1` 就结束当前章节，导致扩展格式的文章「没有解析到任何题目」。
  已改为「无法识别为章节的标题行保留在当前章节内」。

---

## 十五、尚未完成或需要人工验证的事项

自动化测试能证明的部分已在第十四节列出；以下项目**未**在本机执行，不做「已通过」的声明：

1. **真实浏览器交互未做端到端自动化**：本环境没有可用的浏览器自动化通道，
   因此「点击 Chapter 展开收起、拖动进度条跳转、切换倍速、输入答案点检查答案」这些
   交互没有跑过自动化用例。已做的是：判分规则在 Node 中逐条真实执行（14.3），
   生成 HTML 的结构与语义（`<details>` / `<summary>` / `role="slider"` /
   `aria-live` / `aria-controls`）由 `validate.py` 静态校验。
   请按第十节的步骤在浏览器里手工过一遍。
2. **实际听感未验证**：WAV 文件参数已用 Python `wave` 模块读出来核对（14.1 / 8.1），
   但「播放是否真的出声」需要有声卡的浏览器会话，未由本工具执行。
3. **移动端真机布局未验证**：响应式断点（640px）已实现，未在真机或设备模拟器中逐档核对；
   单词表已放在 `.table-wrap`（`overflow-x: auto`）内以避免整页横向滚动。
4. **GitHub Pages 实际发布未执行**：`git push` 由用户本人完成，因此
   `https://zc110747.github.io/DailyLingo/` 尚未由本工具访问验证；
   子路径兼容性由「无绝对根路径」检查 + 临时目录内的子路径模拟部署测试覆盖。
5. **键盘无障碍仅做了代码层面的保障**（语义化标签、可见焦点、文本化反馈、
   进度条可聚焦可操作），未使用读屏软件实测。
6. **`src/` 中已删除文章的历史 HTML 不会被自动清理**：构建不删除文件，
   避免误删非构建产物。若某篇文章被移除，请手工删除对应的
   `src/xxxx.*.html` 与 `sources/xxxx.*.wav`。
