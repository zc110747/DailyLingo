# DailyLingo

**[English](README.md) | [简体中文](README-CH.md)**

A daily English-learning site: short graded readings with real WAV narration, a key-word table,
reading-comprehension practice with instant grading, and fully automatic article navigation.

Pure static site — **no login, no database, no backend, no remote API**. The build output is
committed as-is and served straight from GitHub Pages.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](#quick-start)
[![Runtime dependencies: none](https://img.shields.io/badge/runtime%20dependencies-none-success.svg)](#quick-start)
[![Tests: 109 passed](https://img.shields.io/badge/tests-109%20passed-success.svg)](#verification-results)
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
  elapsed time, duration, live progress, click-to-seek, drag-to-seek, `0.75x` / `1x` / `1.25x`
  speed, volume, loading/finished/error states — every indicator is driven by real playback events.
- **Play first, then read** — the player sits directly under the `Article` heading and **above the
  body text**, separated from it by a thin divider with breathing room on both sides, and sticks
  to the top of the viewport while you scroll, so you can start the audio and then read along
  without ever scrolling back to the controls.
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
├── content/                    # Article source of truth (Markdown)
│   ├── 0001.A_New_Hobby.md
│   └── …                       # 0002, 0003, … one per article
├── sources/                    # WAV files from the external TTS tool (same basename as the .md)
│   ├── 0001.A_New_Hobby.wav
│   └── …                       # 0002, 0003, … one per article
├── assets/
│   ├── css/style.css           # Site-wide styles (desktop + mobile)
│   ├── js/audio-player.js      # Audio player
│   ├── js/main.js              # Question grading / page interactions
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
│   └── test_frontend.py        # Grading logic executed for real in Node
├── watch.bat                   # Double-click to start watching on Windows
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
| `content/` | Article source of truth | **Yes**, maintained by hand |
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
    …
```

*(The directory lists every article in the Chapter in ascending order; only the first entry is shown
here. The real homepage is never abbreviated.)*

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

### Generating Audio with EnglishAudio

Audio is produced by an external tool — the build script **never** synthesises speech and **never**
transcodes. This project uses **EnglishAudio** (Piper + ONNX, fully offline: no network access and
no text ever leaves the machine). It can live in either place:

- `E:\cnb\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd` — the source
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
"E:\cnb\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd"^
  "content\0006.A_Visit_to_the_Library.md" --dist="sources"

:: Batch: convert every .md under content/
for %f in (content\*.md) do ^
  "E:\cnb\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd" "%f" --dist="sources"

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

- **Full rebuild** (ten articles, ~0.12 s in process): adding or removing an article changes the
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
   content/0009.My_Weekend.md
   ```

2. Write the raw title and body: `# My Weekend`, then `## Article`.
3. Fill in `## Words` (3 or 5 columns), `## Questions` and `## Answers`.
4. Generate the same-named WAV with EnglishAudio and place it in `sources/` (see
   [Generating Audio with EnglishAudio](#generating-audio-with-englishaudio)):

   ```bat
   "E:\cnb\git\Desktop_Vibe_Coding\009.ai_voice\publisher\eaudio.cmd"^
     "content\0009.My_Weekend.md" --dist="sources"
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
  …                                   # one such line per article
DailyLingo 构建完成
  文章总数：10
  Chapter 分组：1
    Chapter 0001–0100（默认展开）：10 篇
  警告：0 条
```

*(Abridged for readability — the real output prints one `文章 NNNN …` line per article and lists
every title under its Chapter. The CLI output is currently in Chinese; the format is stable.)*

### Validation

```text
$ python scripts/validate.py
结果：PASS 380 / FAIL 0 / WARN 0
```

Covers: article data; number uniqueness and ascending order; Chapter range boundaries and the
"only non-empty Chapters" rule; the homepage containing nothing but the brand and the directory
(including negative checks for summaries / difficulty / audio status); the first Chapter being
expanded; the order of the five sections; **the player sitting inside `Article`, under the heading
and above the first paragraph**; **a divider between the player and the body text**; **the player
controls being volume plus exactly three speed buttons (`0.75x` / `1x` / `1.25x`, no ±5 s)** on pages
whose WAV exists — a page whose audio has not been generated yet must instead emit no player
controls at all (only the `player-unavailable` note);
**the icon files existing, being valid PNG/SVG, and being declared
on every page with the right relative prefix**; browser title and heading consistency; word-table
row counts; question counts; the grading key matching the Answers section; Answers being collapsed
by default; previous/next links and titles; first/last article boundaries; absence of
root-absolute paths; existence of static assets; byte-identical rebuilds (a mismatch caused purely
by line endings is called out as such, instead of being reported as an unexplained byte difference).

### Automated tests

```text
$ pytest -q
109 passed in 2.31s
```

| File | Cases | Coverage |
|---|---|---|
| `tests/test_build.py` | 105 | Article parsing (missing number / missing title / invalid number / duplicate number / filename-number mismatch / Chinese and special characters), number display rules (including beyond four digits), Chapter boundaries (`0001`/`0100`/`0101`/`0200`/`0201`/`0300`/`301`/`9999`/`10001`), correct grouping across gaps, empty Chapters not rendered, ascending order within a group, first group expanded, a new article creating a new group, a group disappearing after its last article is deleted, homepage links resolvable, titles consistent site-wide, browser tab containing the number, previous/next links and first/last boundaries, navigation independent of grouping, 3- and 5-column word tables, question-type inference, compact answer strings, **numbered answer lists (`1. **B. …** explanation`, both the plain and the escaped `1\.` spelling, for stems and answers alike), 11 boundary cases for `extract_choice_key` (`cook` is not read as `C`)**, `题型：填空` with multiple acceptable answers, `______` preserved, invalid answer configurations detected, missing answers reported, Answers collapsed by default, grading data matching the answers, `normalize_answer` edge cases, **the player rendered above the body text (with and without a WAV)**, **a divider between the player and the body text**, **no ±5 s buttons and exactly three speed buttons**, **icon declarations carrying the correct relative prefix, home page icon next to the brand, icon assets valid PNG/SVG with the expected dimensions**, a missing WAV warning without affecting other sections, CSS/JS/audio relative paths, **CSS/JS URLs carrying a content fingerprint (`?v=` + 8 hex digits)**, GitHub Pages subpath, reproducible builds |
| `tests/test_frontend.py` | 4 | Executes `assets/js/main.js` for real in Node: correct / incorrect / empty single-choice selections, case insensitivity, leading and trailing whitespace, trailing punctuation, multiple acceptable answers, blank input never correct; plus a sample-by-sample consistency check against `build.normalize_answer` |

Every test uses temporary directories and never touches the real `content/` or `sources/`.

### Local static server

```text
$ python -m http.server 8123
200 2517   text/html              <- /
200 9916   text/html              <- /src/0001.A_New_Hobby.html
200 …                               <- /src/0002 … 0010  (one page per article)
200 17162  text/css               <- /assets/css/style.css
200 7291   application/javascript <- /assets/js/main.js
200 9610   application/javascript <- /assets/js/audio-player.js
200 919    image/svg+xml          <- /assets/images/favicon.svg
200 942    image/png              <- /assets/images/favicon-32.png
200 4682   image/png              <- /assets/images/favicon-180.png
200 1641488 audio/wav             <- /sources/0001.A_New_Hobby.wav
200 …                               <- /sources/0002 … 0010  (one WAV per article)
```

*(Abridged: all 27 paths — 10 article pages, 10 WAVs, the homepage and the shared assets — were
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

The homepage served from GitHub Pages lists every article under `Chapter 0001–0100`. WAV
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
- **A stale local path to the audio tool.** `watch.py`'s fallback pointed at
  `D:\user_project\…\009.ai_voice\publisher\eaudio.cmd`, which no longer exists — the EnglishAudio
  source repo now lives under `E:\cnb\git\Desktop_Vibe_Coding\009.ai_voice\publisher\`. The
  candidate list and both READMEs were updated, and `resolve_audio_tool()` was checked to actually
  return a readable path (`--audio` therefore works again).
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
6. **The icon and the sticky player are not visually verified in a browser.** The SVG/PNG assets are
   structurally checked (dimensions, PNG signature, declaration on every page) and the icon was
   reviewed as a rendered image, but how the favicon looks in a real tab bar at 16 px, and how the
   sticky player behaves while scrolling on a phone, need a browser session. If the sticky
   behaviour is unwanted, delete the `.section-article .player` rule in `assets/css/style.css`.

---

**[English](README.md) | [简体中文](README-CH.md)**
