# Site redesign: generator look and settings presets

Date: 2026-11-14 · Status: approved

## Intent

The GitHub Pages site works but looks too plain. Make it look like a real
generator, in the spirit of ootrandomizer.com's generator, and let players
start from a preset instead of reading every option.

## Goals

- A generator-style layout with its own visual identity.
- Settings presets with a description, modelled on OoTR's "Settings Presets"
  panel (Default / Beginner, Easy Mode, Hell Mode).

## Non-goals

- Settings string, race seed, seed hash icons (discussed and left for later).
- Any change to the Python randomizer, the worker protocol or the options it
  accepts.
- New settings.

## Anti-goals

- Nintendo / Zelda artwork, logos or OoTR's look copied as is. Ideas, not assets.
- A CSS or JS framework, a build step, or new dependencies.
- Breaking the current flow: pick .nup → options → generate → zip download,
  the saved settings, keyboard access to the tabs, or the phone layout.

## Constraints

- Plain HTML/CSS/JS in `site/` (index.html, style.css, app.js), deployed by
  `tools/build_site.py` + `.github/workflows/pages.yml`. `tests/test_build_site.py`
  must keep passing.
- Page text stays in English (public repo).
- Another branch (`feat/full-skip`) is adding a `dungeon_rewards` value to the
  Shuffle Songs select in the same files; the merge will need that option and
  its hint carried into the new markup.

## Approaches

1. **Everything in the web page (chosen).** Restyle and restructure the three
   site files; presets are a small table in app.js. Simplest, no Python touched,
   easy to check by hand.
2. Presets defined in Python and sent by the worker with the item list. One
   source of truth that a CLI could use, but more plumbing for something only
   the web uses today.
3. A CSS framework (Tailwind, Bootstrap). Rejected: weight without benefit at
   this page size.

## Design

### Look (mockup "B")

- Header band: dark forest-green gradient, gold title, short tagline, and a
  light/dark toggle (☀/☾) on the right.
- Left **sidebar** with the sections (General, Items, Logic, Install). It
  replaces the top tabs and keeps the tablist semantics and arrow-key
  navigation (vertical). On phone width it becomes a horizontal, scrollable bar
  at the top.
- Options grouped in **cards**; checkboxes become **toggle switches** (still
  real `<input type="checkbox">`, styled).
- Long grey hint paragraphs become **ⓘ tooltips** next to the label, opened on
  hover, focus or tap (must work on touch and with the keyboard).
- **Sticky bottom bar**: seed field, 🎲, and "Generate and download", always
  visible. Status messages stay near it.
- Palette: own forest green + gold, defined as CSS tokens, with a light and a
  dark theme. Default follows the system; the toggle overrides it and is
  remembered in localStorage.

### Presets

- A **"Settings Presets" card at the top of General**: a select and, beside it
  (below on phones), the description of the selected preset.

| Preset | Key items | Tokensanity | Shuffle Songs | Skip cutscenes |
|---|---|---|---|---|
| Default / Beginner | Any chest | Off | Off | Off |
| Easy Mode | Any chest | Off | Song Locations | On |
| Hell Mode | Any chest | All | Anywhere | On |

  Descriptions (final wording is the builder's): Beginner — for players who
  know the vanilla game, similar progression, no timesavers. Easy — for those
  who have seen a randomizer before, cutscenes skipped. Hell — everything
  shuffled as much as this version allows, still always beatable.
- Loading a preset sets those four options and clears the excluded items. It
  never touches the seed or the spoiler checkbox.
- Changing any option after that switches the select to **"[Custom]"**.
- The chosen preset is saved with the other settings; on load, if the saved
  options no longer match it, show "[Custom]".

## Left to the builder

Exact colours, spacing, tooltip implementation, description wording, and how
the sidebar collapses at phone width (no horizontal page scroll, 16px gutter).
