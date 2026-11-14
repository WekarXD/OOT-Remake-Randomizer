# Site Redesign and Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the GitHub Pages generator its own generator-style look (sidebar, cards, toggles, tooltips, sticky bar, light/dark) and add OoTR-style settings presets.

**Architecture:** Plain static files in `site/`. Preset data and the pure preset logic live in a new classic script `site/presets.js` that also loads in Node for tests; `app.js` wires it to the DOM. Markup and CSS are restructured in place; the worker protocol and Python are untouched.

**Tech Stack:** HTML, CSS (custom properties), vanilla JS (classic scripts), Node 24 `node:test` for JS unit tests, Python `unittest` as the single test entry point.

**Spec:** `docs/superpowers/specs/2026-11-14-site-redesign-design.md`

## Global Constraints

- No framework, no build step, no new dependency; only `site/index.html`, `site/style.css`, `site/app.js`, new `site/presets.js`, and tests change.
- Page text in English.
- No Nintendo/Zelda artwork or logos; own palette: forest green + gold, as CSS tokens on `:root`, light and dark.
- Dark/light: follows `prefers-color-scheme` unless the toggle set `data-theme="light"|"dark"` on `<html>`; choice stored in localStorage key `oot-remake-rando-theme`.
- Every localStorage read/write in try/catch; the page works with storage blocked.
- Phone width (375px): 16px side gutter, no horizontal page scroll.
- Option values sent to the worker are exactly today's: `key_items_mode`, `excluded_items`, `spoiler`, `skip_cutscenes`, `tokensanity`, `shuffle_songs`, `seed`.

## Review Focus

1. A preset value the Python side rejects (typo, value not on this branch such as `dungeon_rewards`) → Generate fails. Expected: every preset passes `browser.parse_settings`. Test in Task 1.
2. Settings saved by the old page (no preset field, maybe excluded items) → select shows the matching preset or `[Custom]`, never a wrong preset. Test in Task 1 (`match`), wiring re-check after items render in Task 3.
3. Renaming/moving markup drops an id `app.js` uses → silent `null` crash at load. Test in Task 2.
4. Phone width: sticky bar covers the status messages or the last option. Expected: page has bottom padding ≥ bar height; status visible. Manual check in Task 4.
5. Keyboard only: sidebar reachable with arrow keys (Up/Down and Left/Right), tooltips open with Enter/Space and close with Escape. Manual check in Task 4.

---

### Task 1: Preset data and logic (`site/presets.js`)

**Files:**
- Create: `site/presets.js`
- Create: `tests/js/presets.test.cjs`
- Create: `tests/test_site_js.py`

**Interfaces:**
- Produces (global `Presets` in the browser, `module.exports` in Node):
  - `Presets.LIST`: array of `{id, label, description, settings}` where `settings` = `{key_items_mode, tokensanity, shuffle_songs, skip_cutscenes}`; ids in order `'beginner'`, `'easy'`, `'hell'`; labels `Default / Beginner`, `Easy Mode`, `Hell Mode`.
  - `Presets.CUSTOM = 'custom'`, label `[Custom]`.
  - `Presets.apply(options, id) -> options`: returns a **new** object: `options` with the preset's four settings and `excluded_items: []`; `seed` and `spoiler` untouched. Throws `Error('Unknown preset: <id>')`.
  - `Presets.match(options) -> id | 'custom'`: the preset whose four settings equal `options` and whose `excluded_items` is empty (missing counts as empty); otherwise `'custom'`.
  - `Presets.describe(id) -> string`: description, or `'Your own settings.'` for custom.

Values (from the spec):

| id | key_items_mode | tokensanity | shuffle_songs | skip_cutscenes |
|---|---|---|---|---|
| beginner | any_chest | off | off | false |
| easy | any_chest | off | song_locations | true |
| hell | any_chest | all | anywhere | true |

Descriptions: Beginner — for players who know the vanilla game: similar progression, no timesavers. Easy — for players who have seen a randomizer before: songs shuffled among song spots, cutscenes skipped. Hell — everything this version can shuffle, shuffled; still always beatable.

- [ ] **Step 1: Write the failing Node tests** in `tests/js/presets.test.cjs` (`require('../../site/presets.js')`, `node:test`, `node:assert/strict`):
  - `apply keeps seed and spoiler and clears exclusions`: `apply({seed:'S', spoiler:false, excluded_items:['Item_Hammer'], key_items_mode:'vanilla', tokensanity:'all', shuffle_songs:'off', skip_cutscenes:false}, 'easy')` deep-equals `{seed:'S', spoiler:false, excluded_items:[], key_items_mode:'any_chest', tokensanity:'off', shuffle_songs:'song_locations', skip_cutscenes:true}`.
  - `apply does not mutate its input`: input deep-equal to a copy taken before.
  - `apply throws on unknown id`: `/Unknown preset: nope/`.
  - `match finds each preset`: for every `LIST` entry, `match(apply(base, id)) === id`.
  - `match returns custom with exclusions`: `match({...apply(base,'hell'), excluded_items:['Item_Hammer']}) === 'custom'`.
  - `match returns custom for old saved settings`: `{key_items_mode:'vanilla', tokensanity:'off', shuffle_songs:'off', skip_cutscenes:false, excluded_items:[]}` → `'custom'`.
  - `old defaults match beginner`: `{key_items_mode:'any_chest', tokensanity:'off', shuffle_songs:'off', skip_cutscenes:false}` (no `excluded_items` key) → `'beginner'`.

- [ ] **Step 2: Write the Python wrapper** `tests/test_site_js.py`:
  - `test_node_presets`: runs `node --test tests/js/` (cwd repo root), asserts return code 0; `skipTest` when `shutil.which('node')` is None.
  - `test_presets_accepted_by_python`: runs `node -e` that prints `JSON.stringify(require('./site/presets.js').LIST)`; for each preset, `browser.parse_settings({**p['settings'], 'seed': 'x'})` must not raise, and the parsed `Settings` fields equal the preset's four values.

- [ ] **Step 3: Run, expect FAIL** — `python -m unittest tests.test_site_js -v` → errors, `site/presets.js` missing.

- [ ] **Step 4: Implement `site/presets.js`** as an IIFE: `(function (root) { … if (typeof module === 'object' && module.exports) module.exports = api; else root.Presets = api; })(this);`, `'use strict'`, `Object.freeze` on `LIST` entries.

- [ ] **Step 5: Run, expect PASS** — `python -m unittest tests.test_site_js tests.test_build_site -v`.

- [ ] **Step 6: Commit** — `git add site/presets.js tests/js tests/test_site_js.py && git commit -m "feat: site settings presets logic"`

---

### Task 2: New layout and look (markup + CSS)

**Files:**
- Modify: `site/index.html` (whole file restructured)
- Modify: `site/style.css` (rewritten)
- Test: `tests/test_site_js.py` (add one test)

**Interfaces:**
- Consumes: nothing from Task 1 yet (the presets card markup is added here, wiring in Task 3).
- Produces (ids/classes Task 3 relies on): every id `app.js` uses today stays (`nup`, `nup-status`, `seed`, `dice`, `skip-cutscenes`, `spoiler`, `generate`, `result`, `engine`, `mode`, `items`, `tokensanity`, `shuffle_songs`, the `tab-*`/`panel-*` pairs) plus new: `preset` (select), `preset-desc` (description `<p>`), `theme` (toggle button). Tooltip markup: `<button type="button" class="tip" aria-expanded="false" aria-controls="tip-X" aria-label="About <option>">ⓘ</button>` followed by `<p class="tip-text" id="tip-X">…</p>`. `<script src="presets.js">` before `app.js`.

Layout per spec: header band (title, tagline "Item randomizer for the Switch 2 remake of Ocarina of Time. Runs in your browser.", `#theme` button right); body = sidebar `role="tablist" aria-orientation="vertical"` with the four tabs + main panels; General panel starts with the "Settings Presets" card (`#preset` with options beginner/easy/hell/custom, `#preset-desc` beside it, stacked under 600px); options in `.card`s; checkboxes styled as switches via a `.switch` class on the label (input stays a real checkbox); every current `.hint` paragraph that explains one option becomes a tooltip, notes not about one option (Market Treasure Chest note, install steps, "fixed in this version") stay as text; sticky footer `.bar` holding `#seed`, `#dice`, `#generate`, with `#result` just above the bar inside the sticky area. Under 720px the sidebar becomes a horizontal scrolling bar above the panels (`aria-orientation` is updated in Task 3). Theme tokens: `:root` light values, `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {…} }`, `:root[data-theme="dark"] {…}`; `body` has an explicit background. `main` gets bottom padding ≥ bar height.

- [ ] **Step 1: Write the failing test** `test_markup_has_every_id_app_uses` in `tests/test_site_js.py`: collect ids from `site/app.js` with regex `\$\('([\w-]+)'\)`, add the four `panel-*` ids and the new ids `preset`, `preset-desc`, `theme`; assert each appears as `id="…"` in `site/index.html`. Also assert `index.html` loads `presets.js` before `app.js`.

- [ ] **Step 2: Run, expect FAIL** — `python -m unittest tests.test_site_js -v` → missing `preset`, `preset-desc`, `theme`, `presets.js`.

- [ ] **Step 3: Rewrite `site/index.html` and `site/style.css`** as described above.

- [ ] **Step 4: Run, expect PASS** — `python -m unittest tests.test_site_js tests.test_build_site -v`.

- [ ] **Step 5: Commit** — `git add site tests/test_site_js.py && git commit -m "feat: generator-style site layout and theme"`

---

### Task 3: Wire presets, theme toggle, tooltips, vertical tabs (`site/app.js`)

**Files:**
- Modify: `site/app.js`, `site/index.html` (inline theme script in `<head>` only)

**Interfaces:**
- Consumes: `Presets.LIST`, `Presets.apply`, `Presets.match`, `Presets.describe`, `Presets.CUSTOM` (Task 1); ids and tooltip markup from Task 2.
- Produces: `writeOptions(o)` — sets every control from an options object (inverse of the existing `options()`), including the rendered item checkboxes; `syncPreset()` — sets `#preset` to `Presets.match(options())` and `#preset-desc` to `Presets.describe(...)`.

Behaviour:
- `#preset` `change`: if value is a preset id, `writeOptions(Presets.apply(options(), value))`; then `syncPreset()`; choosing `custom` changes nothing.
- Any `change` on `#mode`, `#tokensanity`, `#shuffle_songs`, `#skip-cutscenes`, or an item checkbox (delegate on `#items`) → `syncPreset()`.
- Call `syncPreset()` after restoring saved settings, and again after `renderItems` in the `ready` handler (saved exclusions only exist then — Review Focus 2).
- Preset is derived, not stored: no new field in the saved settings.
- Theme: `#theme` switches to the opposite of the current effective theme, sets `document.documentElement.dataset.theme`, stores it (try/catch), updates its `aria-label` ("Switch to light mode"/"Switch to dark mode") and glyph ☀/☾. A 3-line inline `<script>` in `<head>` applies the stored theme before paint (try/catch).
- Tooltips: click on `.tip` toggles `aria-expanded` and the `open` class on its `aria-controls` target; Escape closes the open one and returns focus to its button; click outside closes it. Hover also shows it, via CSS, only under `(hover: hover)`.
- Tabs: the arrow handler accepts ArrowUp/ArrowDown as well as Left/Right; a `matchMedia('(max-width: 720px)')` listener sets `aria-orientation` to `horizontal`/`vertical`.

- [ ] **Step 1: Implement the behaviour above.** Keep `options()` and the worker code as is.
- [ ] **Step 2: Run** `python -m unittest tests.test_site_js tests.test_build_site tests.test_browser -v` → PASS.
- [ ] **Step 3: Smoke-check in a browser** — `python tools/build_site.py && python -m http.server 8000 -d _site`, open `http://localhost:8000`: no console errors; each preset changes the four controls and the description; changing Tokensanity after choosing Easy shows `[Custom]`; reload keeps the settings and shows the same preset; theme toggle survives reload.
- [ ] **Step 4: Commit** — `git commit -am "feat: wire presets, theme toggle and tooltips"`

---

### Task 4: Visual and accessibility pass

**Files:**
- Modify: `site/style.css`, `site/index.html`, `site/app.js` (fixes only)

- [ ] **Step 1: Check at 1280×800 and 375×740, light and dark** (screenshots via devtools): no horizontal scroll; 16px gutters; sticky bar never hides `#result` or the last option; muted text and gold readable on both themes (WCAG AA for body text).
- [ ] **Step 2: Keyboard pass** (Review Focus 5): Tab reaches theme toggle, preset select, sidebar, every control, tooltips, Generate; arrows move between sections; Enter/Space opens a tooltip, Escape closes it.
- [ ] **Step 3: Full flow with a real `.nup`** if `OOT_NUP` is set: pick file → Hell Mode → Generate → zip downloads; its spoiler shows tokensanity all and songs anywhere.
- [ ] **Step 4: Fix what the checks found; run** `python -m unittest discover -s tests` → PASS.
- [ ] **Step 5: Commit** — `git commit -am "fix: site layout polish"` (skip if nothing changed).

Merge note for whoever merges `feat/full-skip`: its `dungeon_rewards` option and hint must be re-added to the new Shuffle Songs control (as a tooltip), and `SHUFFLE_SONGS` in `app.js` keeps the value.
