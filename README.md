# DailyLingo

**[English](README.md) | [简体中文](README-CH.md)**

A daily English-learning site: short graded readings with real WAV narration, a key-word table,
reading-comprehension practice with instant grading, fully automatic article navigation, and a
local per-browser learning-progress tracker.

Pure static site — **no login, no database, no backend, no remote API**. The build output is
committed as-is and served straight from GitHub Pages.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](#quick-start)
[![Runtime dependencies: none](https://img.shields.io/badge/runtime%20dependencies-none-success.svg)](#quick-start)
[![Tests: 457 passed](https://img.shields.io/badge/tests-457%20passed-success.svg)](#verification-results)
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
- [Site Icon](#site-icon)
- [Article Numbering and Naming](#article-numbering-and-naming)
- [Markdown Article Format](#markdown-article-format)
- [Homepage Chapter Directory](#homepage-chapter-directory)
- [Learning Progress](#learning-progress)
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

- **Collapsible Chapter directory** — the homepage shows the `DailyLingo` brand, a compact
  progress card and a `<details>` tree of articles grouped into fixed **25-article Chapters**, each
  with its own counter and progress bar. No summaries, no difficulty labels, no audio status.
- **Learning progress, stored in your own browser** — a per-article completed toggle, a Chapter
  roll-up that turns green only when every article in that Chapter is done, a live
  `completed / total · percent` bar, and JSON export/import (merge or overwrite) plus an Android
  package download behind a settings dialog in the top-left corner. No account, no backend, nothing
  uploaded — see [Learning Progress](#learning-progress).
- **Auto-complete on the article page** — finish the audio (≥ 90 % actually listened, seeks inside
  it do not count) **and** get every question right, and the article marks itself done in the same
  store the homepage reads. A status line under the title shows how far you are; the homepage
  toggle stays for manual overrides — see
  [Auto-complete from the article page](#auto-complete-from-the-article-page).
- **Five fixed sections per article** — `Article` / `Words` / `Questions` / `Answers` / `Continue`,
  always in that order, sharing one template, one stylesheet and one script.
- **Back to the catalogue from the top-left** — every article page starts with a `返回目录` pill in
  the top-left corner (above the number and title), so leaving a page never requires scrolling to
  the bottom navigation. It is a real `<a href="../index.html">` with an `aria-label`, keyboard
  focusable, and it is deliberately not sticky: the player already pins itself to the top edge.
- **Real audio, not a mock** — an HTML5 Audio player wired to the actual WAV file. Play/pause,
  elapsed time, duration, live progress, click-to-seek, drag-to-seek, `0.75x` / `1x` / `1.25x`
  speed, volume, loading/finished/error states — every indicator is driven by real playback events.
- **Play first, then read** — the player sits directly under the `Article` heading and **above the
  body text**, separated from it by a thin divider with breathing room on both sides, and sticks
  to the top of the viewport while you scroll, so you can start the audio and then read along
  without ever scrolling back to the controls.
- **Read-along highlight** — the sentence being spoken is bolded and tinted, following playback
  through seeks, speed changes and rewinds; clicking any sentence plays from that sentence. The
  timings are inferred from the WAV at build time (the TTS tool emits none), so this needs no
  backend and no runtime alignment — see [Read-Along Highlight](#read-along-highlight).
- **A real site icon** — a hand-authored SVG (open book + sound bars) with raster fallbacks, wired
  into every page. No CDN, no icon font, no build step: the files are committed as-is.
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
├── src/                        # Article pages (generated) — one .html per article
│   ├── 0001.A_New_Hobby.html
│   └── …                       # 0002, 0003, … one per article
├── content/                    # Article source of truth (Markdown), split by Chapter range
│   ├── 0001-0025/
│   │   ├── 0001.A_New_Hobby.md
│   │   └── …                   # one .md per article
│   └── 0026-0050/
│       └── …                   # scanned recursively — sub-folders are optional
├── sources/                    # WAV files from the external TTS tool (same basename as the .md)
│   ├── 0001.A_New_Hobby.wav
│   └── …                       # 0002, 0003, … one per article
├── assets/
│   ├── css/style.css           # Site-wide styles (desktop + mobile)
│   ├── js/audio-player.js      # Audio player
│   ├── js/main.js              # Question grading / page interactions
│   ├── js/progress.js          # Progress store: localStorage + JSON export/import (both pages)
│   ├── js/study-completion.js  # Article page: listened ≥90% + all answers right ⇒ mark done
│   └── images/                 # Site icon (committed as-is, not generated)
│       ├── favicon.svg         # Source design: open book + sound bars
│       ├── favicon-32.png      # Raster fallback for browsers without SVG icons
│       └── favicon-180.png     # apple-touch-icon
├── scripts/
│   ├── build.py                # Build: parse -> group -> render -> link audio
│   ├── watch.py                # Sync: rebuild automatically when md/wav changes
│   └── validate.py             # Output and data validation
├── tests/
│   ├── conftest.py
│   ├── test_build.py           # Parsing / grouping / titles / navigation / grading / paths
│   ├── test_frontend.py        # Grading logic executed for real in Node
│   ├── test_progress.py        # Progress markup + pure logic (executed in Node)
│   ├── test_progress_dom.py    # Progress interactions driven in jsdom (optional)
│   ├── test_auto_complete.py   # Auto-mark logic + generated markup
│   ├── test_auto_complete_dom.py  # Auto-mark driven in jsdom (optional)
│   └── js/                     # jsdom / Node drivers used by the tests above
├── watch.bat                   # Double-click to start watching on Windows
├── apps/
│   ├── windows/                # Desktop app (WinForms + WebView2) + publisher/ output
│   └── android/                # Android app (system WebView) + publisher/ output
├── requirements.txt
├── .gitignore
├── .gitattributes              # LF in the repo, CRLF for *.bat (see the note below)
├── LICENSE
├── README.md                   # This file (English, default)
└── README-CH.md                # 简体中文文档
```

> **Line endings.** The repository stores LF, and `*.bat` is checked out as CRLF (cmd.exe is only
> reliable with CRLF). This is more than tidiness: `scripts/build.py` always writes LF, so on a
> machine with `core.autocrlf=true` a fresh clone would hand a **CRLF** `src/*.html` to
> `validate.py`, whose byte-level rebuild comparison would then fail (`FAIL`) for no real reason —
> that exact false alarm was reproduced and is now guarded against. When the setup is right,
> `git ls-files --eol src/0001.A_New_Hobby.html index.html` reports `i/lf w/lf`, and the byte counts
> quoted under *Local static server* are LF counts — the same bytes GitHub Pages serves.

> `tools/` (the ~100 MB packaged EnglishAudio TTS build) is **not** in this repository: it is large
> and already maintained elsewhere, so it is only invoked on demand. `.gitignore` already ignores
> the directory, so dropping a copy there will not dirty `git status`.
> See [Generating Audio with EnglishAudio](#generating-audio-with-englishaudio).

Directory responsibilities:

| Path | Role | Hand-editable |
|---|---|---|
| `content/` | Article source of truth; scanned **recursively**, so articles can be grouped into `0001-0025/` style folders | **Yes**, maintained by hand |
| `src/`, `index.html` | Generated HTML | No — rebuilding overwrites it |
| `sources/` | WAV files produced by the external tool | Written by the audio tool |
| `assets/` | Site-wide CSS / JS | Yes |

> **The generated files (`index.html`, `src/*.html`) are committed on purpose.** GitHub Pages serves
> the repository root as the site root with *Deploy from a branch*, so omitting them would publish
> an empty site.

---

## Site Icon

The icon is hand-authored SVG (919 B): a rounded blue square holding three sound bars and an open
book — *listen + read*, which is what the site does. The raster fallbacks are rendered from the
same geometry, so all three files look identical.

| File | Declared as | Size |
|---|---|---|
| `assets/images/favicon.svg` | `rel="icon" type="image/svg+xml"` | 919 B (vector) |
| `assets/images/favicon-32.png` | `rel="icon" type="image/png" sizes="32x32"` | 942 B |
| `assets/images/favicon-180.png` | `rel="apple-touch-icon" sizes="180x180"` | 4 682 B |

- Every page declares all three, using the same relative-path rule as the rest of the site
  (`assets/images/…` on the homepage, `../assets/images/…` on article pages) plus a
  `<meta name="theme-color">` matching the icon background.
- The homepage also shows the icon next to the brand name (`class="brand-icon"`), as part of the
  brand — it is not extra information beyond "brand name + Chapter directory".
- To rebrand, drop in three replacement files and rebuild. `validate.py` checks that they exist,
  that the PNG headers are valid and that all pages declare them with the right prefix.
- Icons are **static assets, not build output**: they are committed as-is so the site keeps working
  even if the build script is never run.

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
content/0001-0025/0001.A_New_Hobby.md   # folder = organisation only, not the ID
src/0001.A_New_Hobby.html               # generated, always flat
sources/0001.A_New_Hobby.wav            # generated by the audio tool, always flat
```

> **The folder is cosmetic.** Chapter grouping is still derived from the article number alone
> (`((n-1)//25)*25+1`), so `content/0002-0026/0001.A_New_Hobby.md` would land in exactly the same
> Chapter. Output stays flat (`src/*.html`, `sources/*.wav`), which keeps every published URL stable
> no matter how the sources are filed.

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

- [catalogue](../index.html)
- [next chapter](./0002.A_Busy_Morning.md)
```

Notes:

- The `# ...` heading is the **raw title** (no number).
- Section names are case-insensitive, and both `# Article` and `## Article` levels are accepted.
  A `## Q1` inside `## Questions` is **not** treated as a new section.
- `## Words` table headers are matched by alias, and both 3-column and 5-column layouts work:
  `Word/单词`, `Pronunciation/IPA/音标/发音`, `词性/pos`, `中文释义/meaning/释义`, `例句/example`.
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
     The period after the number may be **escaped** — `1\. **B. …**`, which is what editors emit to
     stop the line from turning into an ordered list. In CommonMark `\.` is just a literal period,
     so both spellings are accepted and produce identical output.
- Question stems may be written as `Question 1：…` (half- or full-width colon), `**stem**`,
  `## Q1`, or `1. stem` (again with either `1.` or `1\.`).
- `## Continues` (or `## Continue`) is ignored by the build — previous/next links and the table of
  contents are always generated, never maintained by hand. The links inside it exist only for people
  reading the Markdown directly: point the catalogue entry at `../index.html` (the site index **is**
  the catalogue, there is no `catalogue.md`) and the neighbours at `./<NNNN>.<Slug>.md`.

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

▼ Chapter 0001–0025
    0001. A New Hobby
    …
```

*(The directory lists every article in the Chapter in ascending order; only the first entry is shown
here. The real homepage is never abbreviated.)*

### Grouping algorithm (`build.chapter_bounds` / `build.group_chapters`)

Every **25** numbers form a **fixed** range (`build.CHUNK`). Grouping depends on the **numeric**
value of the article number — never on article count, array index or sort position:

```python
CHUNK = 25
start = ((number - 1) // CHUNK) * CHUNK + 1
end   = start + CHUNK - 1
```

| Number | Chapter |
|---|---|
| `0001` | Chapter 0001–0025 |
| `0025` | Chapter 0001–0025 |
| `0026` | Chapter 0026–0050 |
| `0050` | Chapter 0026–0050 |
| `0051` | Chapter 0051–0075 |

**Only Chapters that contain a real article are emitted.** Gaps in the numbering never shift the
range boundaries, and empty groups are never created ahead of time. Adding an article and rebuilding
makes a new group appear automatically; removing the last article of a group makes it disappear.

Group computation and HTML rendering are separate (`group_chapters` → `render_index`), so the rules
never leak into the template and can be unit-tested directly.

### Collapse behaviour

- Uses semantic native `<details>` / `<summary>`; operable by mouse and keyboard, with a visible
  focus ring.
- `Chapter 0001–0025` (the first group) is **expanded by default**; every other existing Chapter is
  **collapsed by default**.
- Each Chapter is independent — expanding one never force-closes another.
- State is conveyed by the arrow direction (`▸` / `▾`).

---

## Learning Progress

The homepage tracks which articles you have finished. Everything lives in the browser — no account,
no backend, no sync service. A mark is written from two places: the toggle on the homepage, and an
**automatic mark on the article page** once you have listened through the audio *and* answered every
question correctly.

### Per-article marks and Chapter roll-up

- Every row in the directory has a round toggle to the **right** of the title: an outlined grey
  circle when unmarked, a green check when done. The title link keeps working as before; the toggle
  is a separate `<button>` carrying `aria-pressed`, a state-dependent `aria-label` and a 36 px hit
  area (34 px on mobile).
- Clicking a toggle never navigates and never collapses or expands the Chapter: the handler calls
  `preventDefault()` + `stopPropagation()`, and the button lives outside `<summary>` anyway.
- The Chapter header carries its own roll-up — `done/total`, **its own small progress bar** and the
  same icon pair — that turns green only when **every article that actually exists in that Chapter**
  is done. Each bar is driven by that Chapter's own articles, so finishing something in one Chapter
  never moves another Chapter's bar. The denominator comes from the generated markup
  (`data-chapter-total`), never from an assumed 25. The state is derived on every render, so there is
  no separate "chapter completed" flag that can drift.
- A new article joins the list unchecked with nothing to configure: storage holds only the set of
  completed IDs, not one record per article.

### Auto-complete from the article page

Finishing an article no longer requires going back to the homepage:

- **Both conditions, not either.** The audio must be listened to **≥ 90 %** *and* every question must
  be graded correct. Meeting one of them changes nothing but the status line.
- **What counts as "listened".** `audio-player.js` accumulates *media* seconds from `timeupdate`
  ticks and reports the ratio through a `dailylingo:listen` event. Any single step larger than
  1.5 s is discarded, because `timeupdate` fires roughly four times a second — a drag or a
  sentence jump would otherwise credit the whole skipped span and let you "finish" an article by
  dragging the handle to the end. Accumulating media time (not wall-clock) also means 0.75x and
  1.25x playback are judged exactly like 1x.
- **What counts as "all correct".** `main.js` derives it from the graded state (`is-correct` on
  every `.question`) and broadcasts a `dailylingo:quiz` snapshot after every check, reset or option
  change. Changing an option clears the graded mark, so a previously correct answer no longer
  counts until you check it again.
- **It only ever adds, never removes.** A completed article stays completed even if you later change
  an answer or replay the audio; removing a mark stays a deliberate act on the homepage. The write
  is a union with the existing set, so marks you made elsewhere are never overwritten.
- **Visible feedback.** The article header carries a status line that starts with the build-time
  hint, then shows `听力 45% · 答对 3/5` while you work, turns green with `✅ 本篇已标记为完成` when
  the mark lands, and says the mark could not be saved (with `⚠️`) if `localStorage` is unavailable.
- **No audio or no questions ⇒ no auto-mark.** Both are prerequisites, so the build writes
  `data-study-auto="false"` and the page says so up front instead of promising something that can
  never happen; the homepage toggle remains the way to mark those articles.

Because the write goes through the same `markCompleted()` used by the homepage, the record is
byte-for-byte the same shape as a manual mark — the index shows the check the next time you open it.

### Homepage statistics

A compact card above the directory shows `completed / total · percent` and a 6 px bar
(`role="progressbar"`, with `aria-valuenow` / `aria-valuetext` kept in sync and the numbers
announced politely). Only real articles are counted — Chapter labels, navigation links and the
brand are not. With zero articles the page shows `0 / 0` and `0%` rather than dividing by zero.
Because the numbers are computed from the same DOM the directory renders, adding an article and
rebuilding is all it takes for it to join the total; existing marks are unaffected.

### Settings dialog (top-left)

A gear button in the top-left corner of the homepage header opens a modal `<dialog>`
(`showModal()`; `Esc`, a backdrop click and the close button all dismiss it). Export/import live
there, deliberately out of the reading path.

- **Export** downloads `dailylingo-progress-YYYYMMDD.json` through a `Blob` + `<a download>`: the
  schema version, the completed IDs and timestamps — no article text, no audio, nothing personal.
- **Import** reads the file you pick, validates it, and then shows a **preview** before touching
  anything: the valid IDs in the file, how many you have now, and the result each mode would give.
- **Merge** (the default) takes the union, so nothing you already marked is cleared. **Overwrite**
  replaces the set with the file's, which *can* clear marks, so it demands a second, explicit
  confirmation.
- Invalid JSON, an unsupported `schemaVersion`, a malformed structure, or an ID list that matches
  nothing in this project all leave the stored progress untouched, with a message saying so.
- IDs are zero-padded strings (`"0001"`). Unknown IDs are ignored **and counted**, malformed
  entries are skipped and counted, and duplicates collapse.
- **Mobile app**: the bottom of the panel links straight to the Android package
  (`apps/android/publisher/DailyLingo.apk?v=<fingerprint>`, with a `download` attribute), so a tap on
  a phone saves the APK locally and it installs from there. When the package is not in the
  repository the whole block is **omitted** rather than leaving a link that 404s.

### Storage format

`localStorage["dailylingo_learning_progress_v1"]`:

```json
{
  "schemaVersion": 1,
  "completedArticles": ["0001", "0002", "0003"],
  "updatedAt": "2026-10-16T08:00:00.000Z"
}
```

- The article **number** is the identity, never the title — renaming an article keeps its mark,
  changing its number does not.
- Leading zeros are preserved; numbers beyond four digits keep every digit.
- A corrupt value is copied to `dailylingo_learning_progress_v1__corrupt` and then reset, with a
  visible notice, so a broken record can never take the homepage down.
- If storage is unavailable (private mode, disabled, quota exhausted) the page says so and keeps
  working for the current session — the marks simply do not survive a reload.

### Browser scope and migration

`localStorage` belongs to **one origin in one browser profile**. Two browsers, two phones, an
Android WebView, a desktop and a laptop do not share marks, and nothing is uploaded anywhere. JSON
export/import is the only migration path. Redeploying the site cannot reset marks that are already
in your browser, because the browser scopes them to the origin, not to a deployment.

## Article Page Sections

Rendered in a fixed order, all articles sharing the same template, CSS and JavaScript:

| # | Section | Contents |
|---|---|---|
| 1 | **Article** | Number, title, **WAV player**, English body. The player is rendered **under the section heading and above the first paragraph**, so the natural order is: start the audio, then read |
| 2 | **Words** | Word table (word / IPA / part of speech / Chinese gloss / example). On narrow screens the table scrolls inside its own container, so the **page itself never scrolls horizontally** |
| 3 | **Questions** | Single-choice and fill-in questions, graded by vanilla JavaScript with no backend |
| 4 | **Answers** | **Collapsed by default**; expanding reveals correct answers, acceptable answers and explanations |
| 5 | **Continue** | Back to the index, previous article, next article (showing the real number and title of the target) |

- Question IDs are unique per page (`Q1`, `Q2`, …) and answers are bound to questions through them.
- The player is placed **above the body text** and is `position: sticky` while the article scrolls,
  so the progress bar and the speed controls stay reachable during reading. Removing the
  `.section-article .player` rule in `assets/css/style.css` turns the sticky behaviour off without
  affecting anything else.
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
- `0.75x` / `1x` / `1.25x` playback rate
- Volume control
- Status messages: loading / buffering / ready / playing / paused / finished
- An explicit error message when the audio file is missing or fails to load

When the duration is not yet available, it is shown as `--:--` and nothing else on the page breaks.

**If an article's WAV is missing**, the player area shows a notice while the article body, word
table, questions, answers and navigation **all keep working**. The build emits a warning instead of
aborting the other pages.

### Read-Along Highlight

While the audio plays, the sentence being spoken is **bolded and tinted**, and it follows playback.
Seeking works the same way as before — dragging the progress bar, `←` / `→`, `Home` / `End`, or
clicking a sentence — and the highlight re-syncs immediately, so there is never a stale highlight
sitting on the previous sentence after a jump.

**Clicking a sentence plays from there** (it starts playing if the audio was paused). Selecting text
with the mouse does **not** trigger a jump, otherwise copying a word would rewind the audio.

Where the timing comes from — the TTS tool emits **no timestamps**, so `scripts/timeline.py` derives
them from the WAV itself at build time:

1. a 10 ms **peak** envelope separates speech from silence (peak rather than RMS, because -60 dB
   residue in a pause drags an RMS window up);
2. every silence run of at least 100 ms becomes a **candidate boundary**. A pause is an atomic unit:
   one pause carries at most one boundary — otherwise a long paragraph break swallows a whole
   sentence;
3. dynamic programming picks exactly *N-1* of them for *N* sentences, under the expectation that each
   sentence's **voiced duration** (silence excluded) is proportional to its syllable count.

Three details turned out to matter:

- **Voiced time, not wall-clock time.** Pauses after commas inflate wall-clock duration and would
  systematically push boundaries towards long sentences.
- **Cost per sentence, not cumulative drift.** A cumulative measure lets one sentence be squeezed
  while its neighbour absorbs the drift — measured: 13 syllables crammed into 0.87 s. Per-sentence
  cost has no such hole.
- **Quoted speech plus its attribution is one unit.** `“Oh no! Where is my ticket?” she says.` is read
  with no pause between the quote and `she says.`, so that boundary is not observable in the audio at
  all; splitting it forces the optimizer to dump a boundary somewhere else and shifts every later
  sentence.

Nothing is computed at runtime — the timings ship as `data-start` / `data-end` attributes on each
sentence. If the WAV is missing or cannot be analysed (not 16-bit PCM, for example), the body is
rendered as plain paragraphs and only the highlight is absent; the player and everything else keep
working.

### Generating Audio with EnglishAudio

Audio is produced by an external tool — the build script **never** synthesises speech and **never**
transcodes. This project uses **EnglishAudio** (Piper + ONNX, fully offline: no network access and
no text ever leaves the machine). It can live in either place:

- **On the system `PATH`** — EnglishAudio is installed machine-wide, so `EnglishAudio.exe` and
  `eaudio.cmd` are callable by name. **No absolute path is recorded anywhere in this repository**:
  different machines keep the tool in different places, and a hard-coded path breaks on the next
  machine;
- `<this repo>/tools\eaudio.cmd` — optional fallback: copy the whole package in. `tools/` is
  `.gitignore`d because the package is ~100 MB (including a 63 MB voice model).

`scripts/watch.py --audio` locates it in the following order, and if nothing is found it simply
rebuilds the pages and prints a notice:

```text
--audio-tool <path>  >  env var DAILYLINGO_AUDIO_TOOL  >  <repo>/tools/eaudio.cmd
                     >  PATH: eaudio.cmd / EnglishAudio.exe / EnglishAudio
                     >  <repo>/tools/eaudio.cmd
```

```bat
:: Single file: reads the ## Article section -> writes a same-named WAV
EnglishAudio.exe "content\0006.A_Visit_to_the_Library.md" --dist="sources"

:: Batch: convert every .md under content/
for %f in (content\*.md) do EnglishAudio.exe "%f" --dist="sources"

:: Or let the watcher fill in missing WAVs and rebuild for you
python scripts/watch.py --audio
```

The tool only reads the `## Article` section — `## Words`, `## Questions`, `## Answers` and
`## Continues` are never spoken. A body containing non-English characters is rejected outright
(exit code 4), and the Markdown must be UTF-8.

> **Re-generate the WAV after editing the body.** The watcher only fills in *missing* files; it does
> not detect that the text changed, so an edited article keeps a stale recording until you re-run
> the tool.

Every WAV file in this repository was produced by that tool, and all of them share the same
parameters — **mono / 16 bit / 22 050 Hz**, one file per article. Read back with Python's `wave`
module:

| File | Channels / bit depth / sample rate | Duration | Size |
|---|---|---|---|
| `0001.A_New_Hobby.wav` | mono / 16 bit / 22 050 Hz | 37.22 s | 1 641 488 B |
| … (one row per article) | mono / 16 bit / 22 050 Hz | varies | varies |

### Auto-Rebuild on Markdown Changes

No need to re-run the build by hand while writing: `watch.py` polls `content/**/*.md` and
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

- **Full rebuild** (fifty-five articles, ~0.71 s in process with the timeline cache warm; the first run of a process takes ~1.90 s
  because it analyses each WAV for sentence timings, which are then cached against the file's
  size/mtime and only recomputed when the audio itself changes): adding or removing an article
  changes the
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
  - article → assets: `../assets/css/style.css?v=<hash>`, `../assets/js/*.js?v=<hash>`
  - article → audio: `../sources/0001.A_New_Hobby.wav`
  - previous / next: plain filenames in the same directory
- **CSS and JS carry a content fingerprint** — `?v=` plus the first eight hex digits of the file's
  SHA-256. GitHub Pages answers these files with `Cache-Control: max-age=600`, so editing a
  stylesheet without changing its URL leaves phones on the previous copy for up to ten minutes,
  which looks exactly like "the fix did not work". Changing the content changes the URL, which
  forces a refetch. The fingerprint comes from `build.asset_version()` (file contents only), so
  builds stay byte-for-byte reproducible.
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

## Windows Desktop App

`apps/windows/` is a WinForms shell that hosts WebView2 and opens the live site directly — nothing
is copied. It starts on a `Lingo` splash screen and only switches to the site once the navigation
succeeds; with no network (or on timeout) it shows "请连接网络，当前无资源" instead. Learning
progress is mirrored to `dailylingo-progress.json` next to the executable, **in exactly the same
format as the web export**, so either side can import the other's file.

```bash
# Run it as-is (needs the .NET 8 Desktop Runtime and the WebView2 Runtime)
apps\windows\publisher\DailyLingo.Desktop.exe

# Re-publish
cd apps/windows && dotnet publish -c Release -r win-x64 --self-contained false -o publisher
```

Startup flow, progress syncing, debug switches and known limits are documented in
[`apps/windows/README.md`](apps/windows/README.md).

---

## Android App

`apps/android/` is a system-WebView shell: it also loads the live site directly, with the same
startup flow as the desktop app (a `Lingo` splash screen, then the site only once the navigation
succeeds; offline or timed out shows "请连接网络，当前无资源"). Learning progress is mirrored to
`dailylingo-progress.json` in the app's private directory, **byte-for-byte compatible with the web
export** (LF endings).

```bash
cd apps/android
python tools/build_apk.py                        # builds publisher/DailyLingo.apk
adb install -r publisher/DailyLingo.apk          # install on the phone
adb shell am start -n com.dailylingo.app/.MainActivity
```

No Gradle: the build script drives the SDK's own `aapt2 / javac / d8 / zipalign / apksigner` and
uses nothing outside the Python standard library. The SDK is located through `ANDROID_SDK_ROOT`
(or `--sdk`) and the JDK through `JAVA_HOME` (or Android Studio's bundled `jbr`).

Progress file location, two-way syncing, debug switches (`--ez force_offline true`) and known
limits are documented in [`apps/android/README.md`](apps/android/README.md).

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
   content/0026-0050/0021.My_Weekend.md
   ```

   Put it in the folder matching its Chapter (create the folder if it is a new range); the build
   scans recursively, so a flat `content/0021.My_Weekend.md` still works. The filename can even be a
   placeholder — `python scripts/fix_content.py --apply` renames it from the `# Title` and rewrites
   the neighbouring `previous` / `next` links in one go (`--check` only reports):

   ```bash
   python scripts/fix_content.py --check   # what would change, exit 1 if anything
   python scripts/fix_content.py --apply   # rename + relink, idempotent
   ```

2. Write the raw title and body: `# My Weekend`, then `## Article`.
3. Fill in `## Words` (3 or 5 columns), `## Questions` and `## Answers`.
4. Generate the same-named WAV with EnglishAudio and place it in `sources/` (see
   [Generating Audio with EnglishAudio](#generating-audio-with-englishaudio)):

   ```bat
   EnglishAudio.exe "content\0021.My_Weekend.md" --dist="sources"
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

scan `content/` (recursively) → parse Markdown and metadata → validate numbering / title / structure / duplicate
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
  …                                   # one such line per article
DailyLingo 构建完成
  文章总数：55
  Chapter 分组：3
    Chapter 0001–0025（默认展开）：25 篇
    Chapter 0026–0050（默认折叠）：25 篇
    Chapter 0051–0075（默认折叠）：5 篇
  警告：0 条
```

*(Abridged for readability — the real output prints one `文章 NNNN …` line per article and lists
every title under its Chapter. The CLI output is currently in Chinese; the format is stable.)*

### Validation

```text
$ python scripts/validate.py
结果：PASS 2527 / FAIL 0 / WARN 0
```

Covers: article data; number uniqueness and ascending order; Chapter range boundaries and the
"only non-empty Chapters" rule; the homepage containing the brand, the progress card and the directory (still with negative
checks for summaries / difficulty / audio status); the first Chapter being
expanded; the order of the five sections; **a top-left `返回目录` link on every article page, placed
before the `<h1>`**; **the player sitting inside `Article`, under the heading
and above the first paragraph**; **a divider between the player and the body text**; **the player
controls being volume plus exactly three speed buttons (`0.75x` / `1x` / `1.25x`, no ±5 s)** on pages
whose WAV exists — a page whose audio has not been generated yet must instead emit no player
controls at all (only the `player-unavailable` note);
**the body split into sentences carrying a strictly increasing, contiguous timeline that starts at 0
and ends exactly at the WAV duration, with the sentence texts joining back into the original
paragraphs character for character**;
**the icon files existing, being valid PNG/SVG, and being declared
on every page with the right relative prefix**; browser title and heading consistency; word-table
row counts; question counts; the grading key matching the Answers section; Answers being collapsed
by default; previous/next links and titles; first/last article boundaries; absence of
root-absolute paths; existence of static assets; byte-identical rebuilds (a mismatch caused purely
by line endings is called out as such, instead of being reported as an unexplained byte difference);
**the progress card, one toggle per real article (all initially unchecked), a stats total and
`aria-valuemax` equal to the real article count, Chapter roll-up totals equal to each Chapter's
real count, the settings dialog with its export/import controls, `progress.js` carrying the
storage key plus the schema version while making no network calls**; **every article page declaring
its `data-article-id` and a status line whose `data-study-auto` matches whether that article really
has both audio and questions, both new scripts referenced with a content fingerprint, the listen /
quiz event names identical on both sides of the contract, and the auto-mark script making no
network calls**.

### Automated tests

```text
$ pytest -q
457 passed in 20.0s
```

| File | Cases | Coverage |
|---|---|---|
| `tests/test_build.py` | 110 | Article parsing (missing number / missing title / invalid number / duplicate number / filename-number mismatch / Chinese and special characters), number display rules (including beyond four digits), Chapter boundaries (`0001`/`0025`/`0026`/`0050`/`0051`/`0075`/`9999`/`10001`, i.e. 25 per Chapter), correct grouping across gaps, empty Chapters not rendered, ascending order within a group, first group expanded, a new article creating a new group, a group disappearing after its last article is deleted, homepage links resolvable, titles consistent site-wide, browser tab containing the number, previous/next links and first/last boundaries, navigation independent of grouping, 3- and 5-column word tables, question-type inference, compact answer strings, **numbered answer lists (`1. **B. …** explanation`, both the plain and the escaped `1\.` spelling, for stems and answers alike), 11 boundary cases for `extract_choice_key` (`cook` is not read as `C`)**, `题型：填空` with multiple acceptable answers, `______` preserved, invalid answer configurations detected, missing answers reported, Answers collapsed by default, grading data matching the answers, `normalize_answer` edge cases, **the player rendered above the body text (with and without a WAV)**, **a divider between the player and the body text**, **no ±5 s buttons and exactly three speed buttons**, **icon declarations carrying the correct relative prefix, home page icon next to the brand, icon assets valid PNG/SVG with the expected dimensions**, a missing WAV warning without affecting other sections, CSS/JS/audio relative paths, **CSS/JS URLs carrying a content fingerprint (`?v=` + 8 hex digits)**, GitHub Pages subpath, reproducible builds, **articles discovered recursively under `content/<chapter>/` folders (nested-only, mixed flat + nested, hidden folders ignored, the same number in two folders still conflicts)** |
| `tests/test_frontend.py` | 7 | Executes `assets/js/main.js` for real in Node: correct / incorrect / empty single-choice selections, case insensitivity, leading and trailing whitespace, trailing punctuation, multiple acceptable answers, blank input never correct; plus a sample-by-sample consistency check against `build.normalize_answer` |
| `tests/test_progress.py` | 32 | Homepage structure for the progress feature (one toggle per real article, all starting unchecked, stats total / `aria-valuemax` / Chapter totals matching reality, settings dialog and its export-import controls, an Android package link carrying `download` and a content fingerprint, the block omitted when the APK is missing, empty site rendering `0 / 0`) **plus the pure logic executed in Node**: zero-padded IDs, payload validation (JSON syntax / `schemaVersion` / structure), dedupe and invalid-entry counting, ignoring unknown IDs, merge union, statistics without dividing by zero, Chapter completion on the real count, export payload shape, filename and import round-trip |
| `tests/test_progress_dom.py` | 18 | Drives the generated homepage in **jsdom** with real click events and a real `localStorage`: first visit empty, toggle updates stats / storage / Chapter, unchecking reverts, Chapter turns green only when complete, **each Chapter's own progress bar and counter move independently (checked on a synthetic two-Chapter site)**, reload restores, corrupt data quarantined, storage-disabled degradation, import preview, merge, overwrite behind a second confirmation, cancelling overwrite, invalid JSON / unsupported version leaving progress intact, unknown IDs ignored and counted, export payload and dialog open/close. Skipped automatically when jsdom is not installed |
| `tests/test_timeline.py` | 133 | `scripts/timeline.py`: sentence splitting (abbreviations such as `Mrs.`, terminators inside quotes, an attribution after a quote merged back, a long following sentence *not* merged), lossless splitting verified against **every paragraph of every article**, syllable estimation, silence detection on synthesised WAVs, the DP picking the pause closest to the syllable ratio, falling back to a grid when there is no pause at all, timeline covering the whole file, monotonic contiguous windows, graceful empty results for 8-bit / missing audio, consistency against the real articles and real WAVs, and the build emitting `data-start` / `data-end` (or plain paragraphs when audio is absent) |
| `tests/test_content_links.py` | 112 | Every `## Continue` block in the Markdown sources: each relative link resolves on disk, previous/next equal the **number-adjacent** article even when it sits in another Chapter folder, first `previous` and last `next` point back to the homepage, and the `0025` ↔ `0026` boundary (which crosses `0001-0025/` → `0026-0050/`) is checked explicitly |
| `tests/test_fix_content.py` | 15 | `scripts/fix_content.py`: slug rules (apostrophes dropped, punctuation removed, spaces → underscores), **every real article's filename already equals `slugify(title)`**, placeholder names renamed, links recomputed across Chapter folders, rerunning is a no-op, `--check` reports without touching files, duplicate numbers and a missing `# Title` are rejected |
| `tests/test_player_dom.py` | 9 | Drives the generated article page in **jsdom** with a stand-in `Audio`: nothing highlighted before playback, highlight follows `currentTime` (0 / 2 / 4 s → sentences 0 / 1 / 2), clicking a sentence seeks to its start and starts playing, clicking while text is selected does nothing, rewinding moves the highlight back, exactly one sentence active. Skipped automatically when jsdom is not installed |
| `tests/test_auto_complete.py` | 8 | Executes `audio-player.js` + `study-completion.js` in Node **without a DOM**: the listen accumulator (first tick only sets the baseline, a normal 0.25 s step accumulates, a step of exactly 1.5 s still counts, forward / backward seeks are discarded, a frozen clock adds nothing) and the completion boundary (0.89 no, 0.90 yes, one wrong answer no, empty question set no, no snapshot no); plus the generated markup — `data-article-id` on every page, `data-study-auto` matching whether audio *and* questions really exist, both scripts referenced with a fingerprint, and the homepage manual toggle still present |
| `tests/test_auto_complete_dom.py` | 13 | Drives a **generated article page** in jsdom with the real `main.js` / `progress.js` / `study-completion.js`: first visit untouched, quiz-only does not complete, playback-only does not complete, 50 % playback does not complete, full playback + all correct marks and persists, the reverse order (listen first, then answer) marks too, reopening shows the existing mark, changing an answer afterwards keeps it, the write is a union with existing records, corrupt storage is quarantined then marked, unavailable storage reports failure. Article ID and question count are read from the build, never hard-coded. Skipped automatically when jsdom is not installed |

Every test uses temporary directories and never touches the real `content/` or `sources/`.
`test_progress_dom.py` additionally needs `jsdom` on this machine; it is a development-only
helper (not a site dependency) and the whole file is skipped when it is missing.

### Local static server

```text
$ python -m http.server 8123
200 25185  text/html              <- /
200 9916   text/html              <- /src/0001.A_New_Hobby.html
200 …                               <- /src/0002 … 0020  (one page per article)
200 25081  text/css               <- /assets/css/style.css
200 7291   application/javascript <- /assets/js/main.js
200 9610   application/javascript <- /assets/js/audio-player.js
200 26252  application/javascript <- /assets/js/progress.js
200 919    image/svg+xml          <- /assets/images/favicon.svg
200 942    image/png              <- /assets/images/favicon-32.png
200 4682   image/png              <- /assets/images/favicon-180.png
200 1641488 audio/wav             <- /sources/0001.A_New_Hobby.wav
200 …                               <- /sources/0002 … 0020  (one WAV per article)
```

*(Abridged: all 120 paths — the homepage plus 55 article pages, 55 WAVs, the shared assets and the Android package — were
requested and answered `200`; the per-article rows are collapsed to one example plus `…` so this
listing stays readable as the collection grows.)*

> **`python -m http.server` ignores `Range`.** A `Range: bytes=0-1023` request still comes back as
> `200` with the whole file and no `Accept-Ranges` header, so drag-to-seek cannot be exercised
> against the local server. GitHub Pages does honour it (see below).

### Published site

```text
$ curl -I https://zc110747.github.io/DailyLingo/
200                                  <- /
200  text/css                       <- /assets/css/style.css
200  application/javascript         <- /assets/js/main.js
200  application/javascript         <- /assets/js/audio-player.js
200  audio/wav                      <- /sources/0001.A_New_Hobby.wav
200  audio/wav                      <- /sources/0002 … (one WAV per article)
206  Partial Content (Range)        <- /sources/0001.A_New_Hobby.wav
```

The homepage served from GitHub Pages lists every article under `Chapter 0001–0025`. WAV
responses support HTTP Range requests (`206 Partial Content`, verified), so seeking works on the
live site.

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
- **Escaped list markers made the answers unparsable.** The new `0007` wrote its answers as
  `1\. **B. Her mother.** …` — the period escaped with a backslash, which is what markdown editors
  emit to avoid auto-numbering, and in CommonMark it is simply a literal period. The numbered-list
  pattern expected a bare `.`, so no answer was matched and the build aborted with
  `Q1…Q5 missing answer`. `_ANS_NUMBERED_RE`, `_Q_NUMBERED_RE` and `_ANS_CHOICE_KEY_RE` now accept
  an optional backslash before the separator, so `1.` and `1\.` are interchangeable for both stems
  and answers; two regression tests cover it, including a check that the backslash never leaks into
  the rendered page.
- **Spaces in filenames.** `0006.A_Visit_to_the Library.md` desynchronised the `sources/` audio
  filename from the page links (the generated `href` contained a space too). The file was renamed to
  underscore form (`0006.A_Visit_to_the_Library.md` / `.wav`) and the old files were removed.
- **Article title not matching its body.** `0005` was titled *A Busy Morning* (duplicating `0002`)
  while its body describes a Saturday on a farm. It was renamed to *A Day on the Farm* — number,
  source filename, H1, audio and the neighbouring `## Continues` cross-references all updated.
- **Stale audio after editing a body.** The `0005` WAV had been generated before the body was
  edited, so the recording no longer matched the text. The watcher only fills in *missing* files, so
  the audio had to be regenerated explicitly. This is now documented as a required step.
- **A pushed CSS fix that a phone refused to show.** The 200 px-tall mobile Continue cards were
  fixed and deployed, yet the phone still rendered them tall. The deployed stylesheet was in fact
  correct — GitHub Pages serves CSS with `Cache-Control: max-age=600`, and the phone had fetched
  the previous copy minutes before the deploy, so it kept using the cached one. Two changes came
  out of this: `?v=<content hash>` on the CSS/JS URLs (see *GitHub Pages Path Compatibility*), and
  the layout fix moved out of the media query. `flex: 1 1 200px` on a shared rule becomes a
  **height** of 200 px the moment a container switches to `flex-direction: column`; the rule is now
  `flex: 1 1 0` + `min-width: 200px`, which is pixel-identical in the row layout and safe in the
  column layout.
- **A validator false positive on pages without a WAV.** `validate.py` asserted "volume plus three
  speed buttons" on *every* page, but a page whose audio has not been generated yet renders only the
  `player-unavailable` hint and no controls at all, so `rates=[]` and the run reported a `FAIL`
  (surfaced by adding `0009` before generating its WAV). The check is now branched: with a player it
  asserts the three speeds and the absence of ±5 s buttons, without one it asserts that no player
  controls were emitted.
- **A hard-coded path to the audio tool.** `watch.py`'s fallback carried an absolute path to
  EnglishAudio, which stops resolving as soon as the tool is reinstalled or the project is opened on
  another machine — that is exactly what happened (the path broke twice as the source repo moved).
  Because the tool is installed on the system `PATH`, `resolve_audio_tool()` now looks it up by name
  (`eaudio.cmd` / `EnglishAudio.exe` / `EnglishAudio`) and **no absolute path is recorded anywhere in
  the repository**. Verified: it resolves on this machine and `watch.py --once` rebuilds all 55
  articles in 2524 ms.
- **A line-ending trap aimed at the "byte-identical rebuild" guarantee.** `core.autocrlf=true` was
  set on the development machine and the repository had no `.gitattributes`, so a fresh clone would
  check `src/*.html` out as **CRLF** while `build.py` always writes LF. Reproduced by converting the
  ten generated pages in a scratch tree to CRLF: `validate.py` reported ten `FAIL`s on a site that
  was in fact perfectly fine. Fixed by committing `.gitattributes` (`* text=auto eol=lf`,
  `*.bat text eol=crlf`, binary assets marked `binary`) and renormalising the seven `content/*.md`
  files whose copies in the index still held CRLF; `validate.py` now also names a CRLF-only
  mismatch explicitly instead of silently reporting a byte difference.

---

## Known Limitations and Manual Verification

Everything the automated tests can prove is listed above. The following items were **not** executed
on this machine, so no "verified" claim is made for them:

1. **No end-to-end browser-interaction automation.** Nothing in `pytest` drives a browser (the
   read-along highlight is the exception — it was checked by hand-driven headless Chromium, see
   item 8 — but that check is not part of the suite), so "click a Chapter to expand, drag the
   progress bar to seek, switch playback speed, type an answer and press Check" are not covered by
   automated cases. What *is* covered:
   the grading rules are executed for real in Node (see above), and the structure and semantics of
   the generated HTML (`<details>` / `<summary>` / `role="slider"` / `aria-live` / `aria-controls`)
   are statically asserted by `validate.py`. Please walk through [Local Preview](#local-preview) by
   hand in a browser. (The learning-progress interactions added later *are* driven for real in
   jsdom — see item 7.)
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
6. **The icon and the sticky player are not visually verified in a browser.** The SVG/PNG assets are
   structurally checked (dimensions, PNG signature, declaration on every page) and the icon was
   reviewed as a rendered image, but how the favicon looks in a real tab bar at 16 px, and how the
   sticky player behaves while scrolling on a phone, need a browser session. If the sticky
   behaviour is unwanted, delete the `.section-article .player` rule in `assets/css/style.css`.
7. **The learning-progress UI is verified in a DOM, not in a browser.** Its behaviour has real
   coverage — `tests/test_progress_dom.py` drives the generated homepage in jsdom with real click
   events and a real `localStorage` — but pixels are not verified: this environment cannot launch
   a browser, so the gear position, the 6 px bar, the two icon states and the dialog at 390 px
   still deserve a quick look through [Local Preview](#local-preview).

8. **Whether the read-along highlight is *correct* needs ears, not tests.** The timeline is not
   supplied by the TTS tool — it is inferred from the WAV's silence structure plus a syllable
   ratio, with boundaries landing on pauses and a typical error of 0.1–0.3 s; a very short sentence
   (`Who knows?`) can flash by. This machine did check the *behaviour* in headless Chromium: the
   highlight advances with playback, jumping to 80 % lands on the right sentence immediately,
   clicking a sentence plays from it, 1.25× keeps up, rewinding moves the highlight back, long
   articles auto-scroll, and a 390 px screenshot looks right. **Whether what you hear is the sentence
   that is bolded still needs one pass through [Local Preview](#local-preview)** — especially for an
   article whose WAV no longer matches its edited body (see "Re-generate the WAV after editing the
   body" above).

9. **The auto-mark's "listened" ratio is verified by arithmetic and event wiring, not by playing
   real audio.** The accumulator has its own unit tests (`addListenStep`) and the whole flow is
   driven in jsdom with synthetic `dailylingo:listen` / `dailylingo:quiz` events, but this session
   had no browser or audio device, so the real `timeupdate` cadence at 0.75x / 1.25x, and whether
   `ended` fires exactly when expected, were not observed. Both thresholds are single named
   constants — `REQUIRED_RATIO` in `assets/js/study-completion.js` and `LISTEN_STEP_LIMIT` in
   `assets/js/audio-player.js` — so tuning them is a one-line change, and `validate.py` asserts
   that the ratio stays at 0.9.

---

**[English](README.md) | [简体中文](README-CH.md)**
