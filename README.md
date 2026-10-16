# DailyLingo

**[English](README.md) | [简体中文](README-CH.md)**

A daily English-learning site: short graded readings with real WAV narration, a key-word table,
reading-comprehension practice with instant grading, and fully automatic article navigation.

Pure static site — **no login, no database, no backend, no remote API**. The build output is
committed as-is and served straight from GitHub Pages.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](#quick-start)
[![Runtime dependencies: none](https://img.shields.io/badge/runtime%20dependencies-none-success.svg)](#quick-start)
[![Tests: 99 passed](https://img.shields.io/badge/tests-99%20passed-success.svg)](#verification-results)
[![Deploy: GitHub Pages](https://img.shields.io/badge/deploy-GitHub%20Pages-222.svg)](#deployment-to-github-pages)

**Live site:** <https://zc110747.github.io/DailyLingo/>

> **Chinese documentation:** [README-CH.md](README-CH.md)

| | |
|---|---|
| **Frontend** | HTML5 + CSS3 + vanilla JavaScript (no React/Vue, no front-end build step) |
| **Content source** | Markdown — the single source of truth |
| **Build / validation** | Python 3, **standard library only** |
| **Tests** | pytest, including the front-end grading logic executed in Node |
| **Audio** | WAV files produced by an external offline TTS tool, played via the HTML5 Audio API |
| **Deployment** | GitHub Pages project site, entirely relative paths |

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Article Numbering and Naming](#article-numbering-and-naming)
- [Markdown Article Format](#markdown-article-format)
- [Homepage Chapter Directory](#homepage-chapter-directory)
- [Article Page Sections](#article-page-sections)
- [Audio Player](#audio-player)
- [Generating Audio with EnglishAudio](#generating-audio-with-englishaudio)
- [Auto-Rebuild on Markdown Changes](#auto-rebuild-on-markdown-changes)
- [GitHub Pages Path Compatibility](#github-pages-path-compatibility)
- [Local Preview](#local-preview)
- [Deployment to GitHub Pages](#deployment-to-github-pages)
- [Adding a New Article](#adding-a-new-article)
- [Build Script Boundaries](#build-script-boundaries)
- [Verification Results](#verification-results)
- [Known Limitations and Manual Verification](#known-limitations-and-manual-verification)

---

## Features

- **Collapsible Chapter directory** — the homepage shows *only* the `DailyLingo` brand and a
  `<details>` tree of articles grouped into fixed 100-number Chapters. No summaries, no difficulty
  labels, no audio status, no counters.
- **Five fixed sections per article** — `Article` / `Words` / `Questions` / `Answers` / `Continue`,
  always in that order, sharing one template, one stylesheet and one script.
- **Real audio, not a mock** — an HTML5 Audio player wired to the actual WAV file. Play/pause,
  elapsed time, duration, live progress, click-to-seek, drag-to-seek, ±5 s, `0.75x`–`2x` speed,
  volume, loading/finished/error states — every indicator is driven by real playback events.
- **Instant grading with no backend** — single-choice and fill-in-the-blank questions graded in the
  browser. Case-insensitive, whitespace-trimmed, trailing-punctuation-tolerant; a blank answer is
  never accepted. Multiple acceptable answers per question are supported.
- **Single source of truth for answers** — the grading key is embedded in the page's `#quiz-data`
  and generated from the same data as the Answers section, so the two can never drift apart.
- **Zero manual navigation** — previous/next links, the homepage list and Chapter grouping are all
  derived from the article number. Add a Markdown file, rebuild, and everything updates.
- **Graceful degradation** — a missing WAV only renders an error message inside the player. The
  article text, word table, questions, answers and navigation all keep working.
- **Reproducible builds** — identical input produces byte-identical output, verified by rebuilding
  the whole site into a temporary directory and diffing it against the files on disk.

---

## Quick Start

```bash
# 1. Install test dependencies (build/validation need nothing at all)
python -m pip install -r requirements.txt

# 2. Build the site -> index.html + src/*.html
python scripts/build.py
python scripts/build.py --verbose    # with a per-article report

# 3. Validate the generated output and data consistency
python scripts/validate.py

# 4. Run the automated tests
pytest -q

# 5. Auto-rebuild whenever a Markdown file changes, then preview
python scripts/watch.py              # Ctrl+C to stop
python -m http.server 8000
```

| | Requirement | Tested version |
|---|---|---|
| Python | 3.9+ (build script uses the standard library only) | 3.13.12 |
| pytest | Only needed to run the tests | 9.1.1 |
| Node.js | Only needed for `tests/test_frontend.py` (skipped if absent) | 22.22.2 |

> `scripts/build.py` and `scripts/validate.py` import **nothing outside the Python standard library**.
> pytest in `requirements.txt` exists solely for the test suite.

---

## Project Structure

```text
DailyLingo/
├── index.html                  # Homepage (generated): brand + collapsible Chapter directory
├── src/                        # Article pages (generated)
│   ├── 0001.A_New_Hobby.html
│   ├── 0002.A_Busy_Morning.html
│   ├── 0003.Helping_a_Neighbor.html
│   ├── 0004.A_Day_at_the_Beach.html
│   ├── 0005.A_Day_on_the_Farm.html
│   └── 0006.A_Visit_to_the_Library.html
├── content/                    # Article source of truth (Markdown)
│   ├── 0001.A_New_Hobby.md
│   ├── …
│   └── 0006.A_Visit_to_the_Library.md
├── sources/                    # WAV files from the external TTS tool (same basename as the .md)
│   ├── 0001.A_New_Hobby.wav
│   ├── …
│   └── 0006.A_Visit_to_the_Library.wav
├── assets/
│   ├── css/style.css           # Site-wide styles (desktop + mobile)
│   ├── js/audio-player.js      # Audio player
│   ├── js/main.js              # Question grading / page interactions
│   └── images/
├── scripts/
│   ├── build.py                # Build: parse -> group -> render -> link audio
│   ├── watch.py                # Sync: rebuild automatically when md/wav changes
│   └── validate.py             # Output and data validation
├── tests/
│   ├── conftest.py
│   ├── test_build.py           # Parsing / grouping / titles / navigation / grading / paths
│   └── test_frontend.py        # Grading logic executed for real in Node
├── watch.bat                   # Double-click to start watching on Windows
├── requirements.txt
├── .gitignore
├── LICENSE
├── README.md                   # This file (English, default)
└── README-CH.md                # 简体中文文档
```

> `tools/` (the ~100 MB packaged EnglishAudio TTS build) is **not** in this repository: it is large
> and already maintained elsewhere, so it is only invoked on demand. `.gitignore` already ignores
> the directory, so dropping a copy there will not dirty `git status`.
> See [Generating Audio with EnglishAudio](#generating-audio-with-englishaudio).

Directory responsibilities:

| Path | Role | Hand-editable |
|---|---|---|
| `content/` | Article source of truth | **Yes**, maintained by hand |
| `src/`, `index.html` | Generated HTML | No — rebuilding overwrites it |
| `sources/` | WAV files produced by the external tool | Written by the audio tool |
| `assets/` | Site-wide CSS / JS | Yes |

> **The generated files (`index.html`, `src/*.html`) are committed on purpose.** GitHub Pages serves
> the repository root as the site root with *Deploy from a branch*, so omitting them would publish
> an empty site.

---

## Article Numbering and Naming

### Numbering

- The number is a **permanent ID**. It never changes when the title, body or sort order changes.
- Articles are sorted ascending by numeric value; duplicate numbers are rejected.
- Displayed as four digits, zero-padded: `0001`, `0002`, `0010`, `0100`, `0101`.
- Numbers longer than four digits **keep every digit, never truncated**: `10000`, `123456`.
- The filename, the `id` front-matter field and the number must all agree, or the build fails.

### File naming

```text
content/0001.A_New_Hobby.md
src/0001.A_New_Hobby.html       # generated
sources/0001.A_New_Hobby.wav    # generated by the audio tool
```

> **Never put spaces in a filename.** `0006.A_Visit_to_the Library.md` would desynchronise the audio
> filename from the page link and the `href` attribute. Use underscores instead.

### Title generation

The raw title **never contains the number**; the number is prepended by a single shared helper
(`build.display_title` / `build.page_title`) used by every page:

| Location | Output |
|---|---|
| Homepage list | `0001. A New Hobby` |
| Article `<h1>` | `A New Hobby` (with the number shown separately above it) |
| Browser tab | `0001. A New Hobby \| DailyLingo` |
| Previous / next navigation | `Previous: 0001. A New Hobby` |

No title is ever hard-coded in a template.

---

## Markdown Article Format

### Compatible format (currently used by `content/`)

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

Notes:

- The `# ...` heading is the **raw title** (no number).
- Section names are case-insensitive, and both `# Article` and `## Article` levels are accepted.
  A `## Q1` inside `## Questions` is **not** treated as a new section.
- `## Words` table headers are matched by alias, and both 3-column and 5-column layouts work:
  `Word/单词`, `Pronunciation/音标`, `词性/pos`, `中文释义/meaning`, `例句/example`.
  `**bold**` inside a cell is stripped.
- `## Answers` accepts four notations (freely mixable):
  1. **Compact key string** — assigned in question order: `BAC`, `ACBBA`, `CABABB`;
  2. **Per-question line** — `Question5: He feels happy because he has helped someone.`;
  3. **Blocks** — `## Q1` + `答案：B` + `解释：…` + `可接受答案：cook, to cook`;
  4. **Numbered answer list** — `1. **B. To the library.** explanation text`: the option letter
     inside the bold run becomes the answer and the text after it becomes the explanation
     (if no trailing text is present, the bold text itself is used). Fill-in-the-blank answers use
     the same form (`1. cook` / `1. **cook**`).
     The letter detector is deliberately strict, so words such as `cook` or `bamboo` are never
     misread as option `C` or `B` (see `build.extract_choice_key` and
     `tests/test_build.py::test_extract_choice_key`).
- Question stems may be written as `Question 1：…` (half- or full-width colon), `**stem**`,
  `## Q1`, or `1. stem`.
- `## Continues` (or `## Continue`) is ignored by the build — previous/next links and the table of
  contents are always generated, never maintained by hand.

### Question types

| Type | Detected when | Grading |
|---|---|---|
| Single choice | Options `A. / B. / C. …` follow the stem, or `题型：单选` is written explicitly | Option letter comparison, case-insensitive |
| Fill in the blank | No options follow the stem, or `题型：填空` is written explicitly | Compared against the answer / acceptable answers: **case-insensitive, leading and trailing whitespace ignored, trailing punctuation ignored; a blank answer is never correct** |

A `______` run inside a stem is preserved verbatim and is never mistaken for Markdown emphasis.

### Optional: YAML front matter

```markdown
---
id: "0101"
title: "Some Title"
audio: "0101.Some_Title.wav"
---
```

All three keys are optional: `id` defaults to the filename prefix (if present it must match),
`title` defaults to the `# ...` heading, and `audio` defaults to `<number>.<filename title>.wav`.

---

## Homepage Chapter Directory

The homepage shows **exactly two things**: the `DailyLingo` brand name and a collapsible directory
of articles grouped by Chapter. No summaries, difficulty, audio status, article counts or anything
else.

```text
DailyLingo

▼ Chapter 0001–0100
    0001. A New Hobby
    0002. A Busy Morning
    0003. Helping a Neighbor
    0004. A Day at the Beach
    0005. A Day on the Farm
    0006. A Visit to the Library
```

### Grouping algorithm (`build.chapter_bounds` / `build.group_chapters`)

Every 100 numbers form a **fixed** range. Grouping depends on the **numeric** value of the article
number — never on article count, array index or sort position:

```python
start = ((number - 1) // 100) * 100 + 1
end   = start + 99
```

| Number | Chapter |
|---|---|
| `0001` | Chapter 0001–0100 |
| `0100` | Chapter 0001–0100 |
| `0101` | Chapter 0101–0200 |
| `0200` | Chapter 0101–0200 |
| `0201` | Chapter 0201–0300 |

**Only Chapters that contain a real article are emitted.** Gaps in the numbering never shift the
range boundaries, and empty groups are never created ahead of time. Adding an article and rebuilding
makes a new group appear automatically; removing the last article of a group makes it disappear.

Group computation and HTML rendering are separate (`group_chapters` → `render_index`), so the rules
never leak into the template and can be unit-tested directly.

### Collapse behaviour

- Uses semantic native `<details>` / `<summary>`; operable by mouse and keyboard, with a visible
  focus ring.
- `Chapter 0001–0100` (the first group) is **expanded by default**; every other existing Chapter is
  **collapsed by default**.
- Each Chapter is independent — expanding one never force-closes another.
- State is conveyed by the arrow direction (`▸` / `▾`).

---

## Article Page Sections

Rendered in a fixed order, all articles sharing the same template, CSS and JavaScript:

| # | Section | Contents |
|---|---|---|
| 1 | **Article** | Number, title, English body, WAV player |
| 2 | **Words** | Word table (word / IPA / part of speech / Chinese gloss / example). On narrow screens the table scrolls inside its own container, so the **page itself never scrolls horizontally** |
| 3 | **Questions** | Single-choice and fill-in questions, graded by vanilla JavaScript with no backend |
| 4 | **Answers** | **Collapsed by default**; expanding reveals correct answers, acceptable answers and explanations |
| 5 | **Continue** | Back to the index, previous article, next article (showing the real number and title of the target) |

- Question IDs are unique per page (`Q1`, `Q2`, …) and answers are bound to questions through them.
- The grading key is embedded in the page's `#quiz-data` and is generated **from the same data** as
  the Answers section, so editing an answer and rebuilding keeps both in sync automatically.
- The first article renders no previous link and the last renders no next link — the text
  "Previous: none" is shown instead of a dead link.
- Previous/next are computed by **ascending numeric order** and are completely independent of the
  homepage Chapter grouping.

---

## Audio Player

Built on the real WAV file and the HTML5 Audio API. **Every displayed state is synchronised with
actual playback** — there is no simulated progress bar and no faked play state. Supported:

- Play / pause
- Elapsed time, total duration, live progress
- Click the progress bar to seek; press and drag to scrub (Pointer Events, so touch works)
- Keyboard control of the progress bar: `←` / `→` 5 s (`Shift` 10 s), `Home` / `End`,
  `Space` / `Enter` to toggle playback
- Back 5 s / forward 5 s
- `0.75x` / `1x` / `1.25x` / `1.5x` / `2x` playback rate
- Volume control
- Status messages: loading / buffering / ready / playing / paused / finished
- An explicit error message when the audio file is missing or fails to load

When the duration is not yet available, it is shown as `--:--` and nothing else on the page breaks.

**If an article's WAV is missing**, the player area shows a notice while the article body, word
table, questions, answers and navigation **all keep working**. The build emits a warning instead of
aborting the other pages.

### Generating Audio with EnglishAudio

Audio is produced by an external tool — the build script **never** synthesises speech and **never**
transcodes. This project uses **EnglishAudio** (Piper + ONNX, fully offline: no network access and
no text ever leaves the machine). It can live in either place:

- `D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd` — the source
  repository, maintained separately;
- `<this repo>/tools\eaudio.cmd` — optional: copy the whole package in. `tools/` is `.gitignore`d
  because the package is ~100 MB (including a 63 MB voice model), so it is not stored twice.

`scripts/watch.py --audio` locates it in the following order, and if nothing is found it simply
rebuilds the pages and prints a notice:

```text
--audio-tool <path>  >  env var DAILYLINGO_AUDIO_TOOL  >  <repo>/tools/eaudio.cmd
                     >  009.ai_voice\publisher\eaudio.cmd
```

```bat
:: Single file: reads the ## Article section -> writes a same-named WAV
"D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd"^
  "content\0006.A_Visit_to_the_Library.md" --dist="sources"

:: Batch: convert every .md under content/
for %f in (content\*.md) do ^
  "D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd" "%f" --dist="sources"

:: Or let the watcher fill in missing WAVs and rebuild for you
python scripts/watch.py --audio
```

The tool only reads the `## Article` section — `## Words`, `## Questions`, `## Answers` and
`## Continues` are never spoken. A body containing non-English characters is rejected outright
(exit code 4), and the Markdown must be UTF-8.

> **Re-generate the WAV after editing the body.** The watcher only fills in *missing* files; it does
> not detect that the text changed, so an edited article keeps a stale recording until you re-run
> the tool.

All six WAV files in this repository were produced by that tool. Measured parameters (read back with
Python's `wave` module):

| File | Channels / bit depth / sample rate | Duration | Size |
|---|---|---|---|
| `0001.A_New_Hobby.wav` | mono / 16 bit / 22 050 Hz | 37.22 s | 1 641 488 B |
| `0002.A_Busy_Morning.wav` | mono / 16 bit / 22 050 Hz | 46.37 s | 2 044 944 B |
| `0003.Helping_a_Neighbor.wav` | mono / 16 bit / 22 050 Hz | 50.43 s | 2 224 164 B |
| `0004.A_Day_at_the_Beach.wav` | mono / 16 bit / 22 050 Hz | 56.23 s | 2 479 932 B |
| `0005.A_Day_on_the_Farm.wav` | mono / 16 bit / 22 050 Hz | 81.22 s | 3 581 660 B |
| `0006.A_Visit_to_the_Library.wav` | mono / 16 bit / 22 050 Hz | 44.32 s | 1 954 552 B |

### Auto-Rebuild on Markdown Changes

No need to re-run the build by hand while writing: `watch.py` polls `content/*.md` and
`sources/*.wav` and rebuilds `index.html` and `src/*.html` whenever something is added, changed or
removed.

| Command | Effect |
|---|---|
| `python scripts/watch.py` | Watch and rebuild (1 s polling by default) |
| `python scripts/watch.py --audio` | Also fill in missing WAVs with EnglishAudio |
| `python scripts/watch.py --once` | Rebuild once and exit (handy in scripts / Git hooks) |
| `python scripts/watch.py --interval 0.5` | Change the polling interval |
| `watch.bat` (double-click) | One-click start on Windows, equivalent to `--audio` |

Behaviour:

- **Full rebuild** (six articles in under 0.2 s): adding or removing an article changes the
  previous/next links of its neighbours, so rewriting only the changed page would leave the site
  subtly inconsistent.
- A malformed Markdown file **prints an error and keeps watching** — fix it and save again.
- `src/*.html` left behind by a deleted article is reported but **never deleted** (the build script
  does not delete files either).

---

## GitHub Pages Path Compatibility

The site is deployed under a **project subpath**, for example `https://zc110747.github.io/DailyLingo/`.

- Every link and asset reference is **relative**; there is not a single root-absolute path:
  - homepage → article: `src/0001.A_New_Hobby.html`
  - article → homepage: `../index.html`
  - article → assets: `../assets/css/style.css`, `../assets/js/*.js`
  - article → audio: `../sources/0001.A_New_Hobby.wav`
  - previous / next: plain filenames in the same directory
- `scripts/validate.py` asserts that no `href="/..."` or `src="/..."` appears in the generated HTML.
- No backend routing, server rewrite or dynamic API is involved, so a local static server and GitHub
  Pages behave identically.

---

## Local Preview

```bash
python scripts/build.py
python -m http.server 8000
```

Then open:

- Homepage — <http://localhost:8000/>
- Example article — <http://localhost:8000/src/0001.A_New_Hobby.html>

> `python -m http.server` does **not** support HTTP Range requests (the deployed GitHub Pages does).
> The browser therefore downloads the whole WAV before playing, so scrubbing feels slightly
> different locally. Functionality itself is unaffected.

---

## Deployment to GitHub Pages

1. Make sure `python scripts/build.py && python scripts/validate.py && pytest -q` all pass.
2. Commit and push — **the generated `index.html` and `src/*.html` must be committed too**.
3. Open the repository's **Settings → Pages**.
4. Set **Source** to *Deploy from a branch*.
5. Set **Branch** to `main` and the folder to `/ (root)`.
6. Save and wait for the deployment to finish.
7. Open the published URL (<https://zc110747.github.io/DailyLingo/>) and check each item in turn:
   homepage → expand/collapse a Chapter → article body → audio playback and speed → word table →
   question grading → expand Answers → previous/next navigation.

Adjust the branch or folder if this repository is configured differently.

---

## Adding a New Article

1. Create a Markdown file in `content/` using an **unused number**:

   ```text
   content/0007.My_Weekend.md
   ```

2. Write the raw title and body: `# My Weekend`, then `## Article`.
3. Fill in `## Words` (3 or 5 columns), `## Questions` and `## Answers`.
4. Generate the same-named WAV with EnglishAudio and place it in `sources/` (see
   [Generating Audio with EnglishAudio](#generating-audio-with-englishaudio)):

   ```bat
   "D:\user_project\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd"^
     "content\0007.My_Weekend.md" --dist="sources"
   ```

5. Rebuild and self-check — or, better, leave `python scripts/watch.py --audio` running, in which
   case saving the Markdown performs steps 4 and 5 for you:

   ```bash
   python scripts/build.py --verbose
   python scripts/validate.py
   pytest -q
   ```

6. Check the page and the audio in a browser, then commit and push.

Adding an article **automatically** updates the homepage list, the Chapter grouping (creating a new
group when needed), the page heading, the browser tab title, the previous/next navigation and the
WAV association. You **never** edit `index.html`, the Chapter groups or another article's navigation
by hand.

**Renaming or removing an article** — the build never deletes files, so also remove the orphaned
`sources/<old name>.wav` and `src/<old name>.html` yourself. A rename means: `git mv` the source,
update its `# ...` heading, update the cross-references in the neighbouring articles'
`## Continues`, regenerate the WAV, delete the old artefacts and rebuild. The number itself never
changes.

---

## Build Script Boundaries

`scripts/build.py` **does**:

scan `content/` → parse Markdown and metadata → validate numbering / title / structure / duplicate
numbers / filename consistency → sort ascending → compute Chapter groups → emit only non-empty
groups → mark the first group as expanded → render `index.html` → render every article page →
generate consistent headings and browser titles → render the word table, questions and answers →
link the WAV → generate previous/next links → check navigation targets and asset paths → warn on
missing audio → fail loudly on invalid data → print a build summary.

`scripts/build.py` **never**:

synthesises speech, calls a TTS engine, converts WAV to MP3, emits a Chapter with no real article,
creates placeholder articles or links, shows summaries / difficulty / audio status on the homepage,
duplicates titles across templates, or blocks the other pages when one article is missing audio.

Builds are **reproducible**: identical input yields byte-identical output. `validate.py` proves this
by rebuilding the whole site into a temporary directory and comparing it byte for byte with the
files on disk.

---

## Verification Results

All figures below were measured on this machine: Windows 10 19045 / Python 3.13.12 / Node 22.22.2.

### Build

```text
$ python scripts/build.py --verbose
  文章 0001  A New Hobby  |  3 词  3 题  |  音频 有
  文章 0002  A Busy Morning  |  4 词  5 题  |  音频 有
  文章 0003  Helping a Neighbor  |  4 词  5 题  |  音频 有
  文章 0004  A Day at the Beach  |  7 词  6 题  |  音频 有
  文章 0005  A Day on the Farm  |  11 词  7 题  |  音频 有
  文章 0006  A Visit to the Library  |  9 词  3 题  |  音频 有
DailyLingo 构建完成
  文章总数：6
  Chapter 分组：1
    Chapter 0001–0100（默认展开）：6 篇
  警告：0 条
```

*(The CLI output is currently in Chinese; the format is stable.)*

### Validation

```text
$ python scripts/validate.py
结果：PASS 207 / FAIL 0 / WARN 0
```

Covers: article data; number uniqueness and ascending order; Chapter range boundaries and the
"only non-empty Chapters" rule; the homepage containing nothing but the brand and the directory
(including negative checks for summaries / difficulty / audio status); the first Chapter being
expanded; the order of the five sections; browser title and heading consistency; word-table row
counts; question counts; the grading key matching the Answers section; Answers being collapsed by
default; previous/next links and titles; first/last article boundaries; absence of root-absolute
paths; existence of static assets; byte-identical rebuilds.

### Automated tests

```text
$ pytest -q
99 passed in 14.52s
```

| File | Cases | Coverage |
|---|---|---|
| `tests/test_build.py` | 95 | Article parsing (missing number / missing title / invalid number / duplicate number / filename-number mismatch / Chinese and special characters), number display rules (including beyond four digits), Chapter boundaries (`0001`/`0100`/`0101`/`0200`/`0201`/`0300`/`301`/`9999`/`10001`), correct grouping across gaps, empty Chapters not rendered, ascending order within a group, first group expanded, a new article creating a new group, a group disappearing after its last article is deleted, homepage links resolvable, titles consistent site-wide, browser tab containing the number, previous/next links and first/last boundaries, navigation independent of grouping, 3- and 5-column word tables, question-type inference, compact answer strings, **numbered answer lists (`1. **B. …** explanation`), 11 boundary cases for `extract_choice_key` (`cook` is not read as `C`)**, `题型：填空` with multiple acceptable answers, `______` preserved, invalid answer configurations detected, missing answers reported, Answers collapsed by default, grading data matching the answers, `normalize_answer` edge cases, a missing WAV warning without affecting other sections, CSS/JS/audio relative paths, GitHub Pages subpath, reproducible builds |
| `tests/test_frontend.py` | 4 | Executes `assets/js/main.js` for real in Node: correct / incorrect / empty single-choice selections, case insensitivity, leading and trailing whitespace, trailing punctuation, multiple acceptable answers, blank input never correct; plus a sample-by-sample consistency check against `build.normalize_answer` |

Every test uses temporary directories and never touches the real `content/` or `sources/`.

### Local static server

```text
$ python -m http.server 8123
200 1601   text/html              <- /
200 9683   text/html              <- /src/0001.A_New_Hobby.html
200 12912  text/html              <- /src/0002.A_Busy_Morning.html
200 12626  text/html              <- /src/0003.Helping_a_Neighbor.html
200 14772  text/html              <- /src/0004.A_Day_at_the_Beach.html
200 17257  text/html              <- /src/0005.A_Day_on_the_Farm.html
200 11134  text/html              <- /src/0006.A_Visit_to_the_Library.html
200 15783  text/css               <- /assets/css/style.css
200 7291   application/javascript <- /assets/js/main.js
200 9894   application/javascript <- /assets/js/audio-player.js
200 1641488 audio/wav             <- /sources/0001.A_New_Hobby.wav
200 3581660 audio/wav             <- /sources/0005.A_Day_on_the_Farm.wav
200 1954552 audio/wav             <- /sources/0006.A_Visit_to_the_Library.wav
```

### Published site

```text
$ curl -I https://zc110747.github.io/DailyLingo/
200                                  <- /
200  text/css                       <- /assets/css/style.css
200  application/javascript         <- /assets/js/main.js
200  application/javascript         <- /assets/js/audio-player.js
200  audio/wav                      <- /sources/0001.A_New_Hobby.wav
200  audio/wav                      <- /sources/0005.A_Day_on_the_Farm.wav
206  Partial Content (Range)        <- /sources/0001.A_New_Hobby.wav
```

The homepage served from GitHub Pages lists all six articles under `Chapter 0001–0100`. WAV
responses support HTTP Range requests (`206 Partial Content`), so seeking works on the live site.

### Real defects found and fixed during development

- **`______` swallowed by the Markdown emphasis rule.** `strip_markdown` handled `_italics_` and
  therefore stripped the underscore run in fill-in-the-blank stems, turning `very ______.` into
  `very __.`. The underscore emphasis rule was removed (`**bold**` and `*italic*` are still
  handled), and a regression test was added.
- **A `## Q1` sub-heading truncated the question section.** Section splitting originally recognised
  only level-2 headings, so an unrecognised `## Q1` ended the current section and articles using the
  extended format reported "no questions parsed". Now, a heading that is not a known section is kept
  inside the current section.
- **Numbered answer lists were unparsable.** The new `0006` wrote its answers as
  `1. **B. To the library.** explanation`, while the parser only understood the compact key string,
  `QuestionN:` and block forms, so the build failed with `Q1/Q2/Q3 missing answer`. `apply_answers`
  now supports this form (plus `extract_choice_key`, whose strict matching stops `cook` and `bamboo`
  from being read as `C` and `B`), backed by 5 regression tests and 11 parameterised boundary cases.
- **Spaces in filenames.** `0006.A_Visit_to_the Library.md` desynchronised the `sources/` audio
  filename from the page links (the generated `href` contained a space too). The file was renamed to
  underscore form (`0006.A_Visit_to_the_Library.md` / `.wav`) and the old files were removed.
- **Article title not matching its body.** `0005` was titled *A Busy Morning* (duplicating `0002`)
  while its body describes a Saturday on a farm. It was renamed to *A Day on the Farm* — number,
  source filename, H1, audio and the neighbouring `## Continues` cross-references all updated.
- **Stale audio after editing a body.** The `0005` WAV had been generated before the body was
  edited, so the recording no longer matched the text. The watcher only fills in *missing* files, so
  the audio had to be regenerated explicitly. This is now documented as a required step.

---

## Known Limitations and Manual Verification

Everything the automated tests can prove is listed above. The following items were **not** executed
on this machine, so no "verified" claim is made for them:

1. **No end-to-end browser-interaction automation.** This environment has no usable browser
   automation channel, so "click a Chapter to expand, drag the progress bar to seek, switch playback
   speed, type an answer and press Check" are not covered by automated cases. What *is* covered:
   the grading rules are executed for real in Node (see above), and the structure and semantics of
   the generated HTML (`<details>` / `<summary>` / `role="slider"` / `aria-live` / `aria-controls`)
   are statically asserted by `validate.py`. Please walk through [Local Preview](#local-preview) by
   hand in a browser.
2. **Actual sound output not verified.** WAV parameters were read back and checked with Python's
   `wave` module, but "does it really play through a speaker" needs a browser session with an audio
   device, which this tool did not have.
3. **Mobile layout not verified on a real device.** The responsive breakpoint (640 px) is in place
   but has not been stepped through on hardware or in a device emulator. The word table sits inside
   `.table-wrap` (`overflow-x: auto`) so the page never scrolls horizontally.
4. **Keyboard accessibility is only guaranteed at the code level** — semantic elements, a visible
   focus ring, textual feedback, a focusable and operable progress bar. No screen reader was used
   for testing.
5. **Orphaned HTML is not cleaned up automatically.** The build never deletes files, to avoid
   touching anything that is not a build artefact. If an article is removed, delete the matching
   `src/xxxx.*.html` and `sources/xxxx.*.wav` by hand.

---

**[English](README.md) | [简体中文](README-CH.md)**
