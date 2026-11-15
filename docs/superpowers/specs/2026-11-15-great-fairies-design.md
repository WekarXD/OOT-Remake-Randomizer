# Great Fairy rewards in the pool — Design

Status: the user approved the approach on 2026-11-14: research, logic rules, a test batch with a teleport, then the option, always on with shuffled key items. The research (`docs/great-fairies-research.md`) and test batch 26 (`docs/test-batch-26.md`, every variant works) are done. This document is the design; the plan follows.

## Why

OoTR always shuffles the six Great Fairy rewards with the other major items. The goal of the project is to resemble OoTR. Today the six fountains always give their own reward, and the logic treats them as fixed.

## Goals, non-goals, anti-goals

- **Goal:** with key items set to "Any chest", the six fountain rewards join the moving items, and the six fountains become item locations. A fountain can give any item the fill puts there. The seed stays beatable.
- **Goal:** with key items set to "Vanilla", nothing changes. The fountains stay as they are today: they charge rupees, Din's Fire gates the other fairies, and each gives its own reward.
- **Non-goals:**
  - the fountains' price (the remake charges 25 to 500 rupees). The fairies become free, as in OoTR. Bringing the price back is in `docs/TODO.md`.
  - the price still named in the fairy's question. This is cosmetic, and it is in `docs/TODO.md`.
  - chest models and texts.
- **Anti-goals:**
  - a fountain that gives its item twice, which would happen if a revisit offered it again;
  - a fountain that never gives its item, because it reads its vanilla reward found elsewhere, or because the player refused to pay;
  - a fountain item that the fairy cannot hand over and that hangs the game.

## What is known (research and batch 26)

| Remake flow | Fountain (OoTR location) | Remake reward | OoTR item |
|---|---|---|---|
| `Dm_FairyFountain_Power` | castle (`HC Great Fairy Reward`) | `Item_FairyBless_MP` | Magic Meter |
| `Dm_FairyFountain_Din` | top of Death Mountain (`DMT Great Fairy Reward`) | `Item_DinFire` | Dins Fire |
| `Dm_FairyFountain_Wisdom` | crater (`DMC Great Fairy Reward`) | `Item_FairyBless_MPDouble` | Magic Meter |
| `Dm_FairyFountain_Frore` | Zora's Fountain (`ZF Great Fairy Reward`) | `Item_FaroreWind` | Farores Wind |
| `Dm_FairyFountain_Nayru` | Desert Colossus (`Colossus Great Fairy Reward`) | `Item_NayruLove` | Nayrus Love |
| `Dm_FairyFountain_Courage` | outside Ganon's Castle (`OGC Great Fairy Reward`) | `Item_FairyBless_DefenseDouble` | Double Defense |

- **The remake swaps two rewards against the N64.** The castle fairy gives the spin attack and the magic, and the mountain fairy gives Din's Fire. This was found from each flow's camera warp and confirmed by batch 26. The fountains' locations match OoTR; only their vanilla rewards differ. The fill works by location, so this only matters for the vanilla content of each site.
- **The grant** is one `Dm_SY_GetInEvent` call with `ActorName`. Din, Wisdom and Courage use their own entries, which add a gauge or defense animation. For another item, these are pointed at `GetInEvent_Demo_NotLookatObjectEntry` (batch 26c, Wisdom).
- **Revisits:** every fountain decides "heal only" from `IsGet.<own reward>`. Reading `HavePlayedEvent.Dm_FairyFountain_<name>` instead (as the windmill does) works (batch 26a). With the price removed, the first visit always grants, so "played" means "given".
- **Free:** batch 26 made the fairies free. Every pay question (`TalkChoice2`) goes to "yes", every rupee check (`HasRuppe`) to "enough", and every payment (`IncreaseRupee`) is skipped. This applies in the fountain's flow and in Din's, whose `Pay`, `DontPay1` and `DontPay2` entries the other fountains call.
- **The Din gate:** `TriForcePoint` refuses every fairy but Din's without `IsGet.Item_DinFire`. Pointing the check at its "true" case removes the gate (26b, 26c).
- **Spin attack guide:** the Power fairy opens `ActionGuide` type 5 after her grant. It is skipped when she gives something else (26b).
- **Magic:** in `PouchActorInfo`, Din's Fire, Farore's Wind, Nayru's Love and `Item_FairyBless_MP` each have `MPMaxUP` 24, and `MPDouble` has 48. Each one brings the meter (26c: Nayru's Love with no magic before). A 24 item keeps an earlier double bar (26a). So the order does not matter, and no progressive handling is needed.
- **The full skip** rewrites the fountains, except Din's, which plays whole since batch 26e because its rewrite lost the item. Power and Wisdom were tested on the skip, and the patches handle the rewrite's inlined copies of the rupee checks.
- **OoTR's access rule** for all six locations is `can_play(Zeldas_Lullaby)`. Its regions already model how each fountain is reached (the castle boulder, the crater wall and so on). The remake's own conditions are the Din gate and the price, and both are removed. **So no access rule is added.**
- **`Dm_SY_GetInEvent:GetInEvent` hangs** with `Item_BulletBag_Small` and `TBox_DekuSeedBundle` (batch 25). Whether a fountain can give a Gold Skulltula token is untested, as it is for song scenes.

## Approaches

| Approach | Trade-off | Decision |
|---|---|---|
| **A.** The six fountains join the fill as synthetic sites (like the song scenes under Anywhere); their rewards join the moving items as key items | Reuses the whole fill (assumed fill, exclusions, ammo, Skulltulas). The rewards appear in the "Exclude items" grid | **Chosen** |
| **B.** As A, but keep the prices: `TriForcePoint` only summons a fairy when Link can pay | Closer to the remake, but needs new events in `TriForcePoint` plus rupee and wallet logic. Courage's 500 rupees exceed the 200 the starting wallet holds | Rejected for now (in `docs/TODO.md`) |
| **C.** A separate on/off setting | The user decided "always on with shuffled key items" | Rejected |

## Design

**Items** (`items.py`). The six rewards join `KEY_ITEMS` with their OoTR names, `LABELS` and `KEY_ITEM_HOME`:

- `Item_FairyBless_MP` and `Item_FairyBless_MPDouble` → `Magic Meter`, labelled "Magic Meter" and "Double Magic";
- `Item_DinFire` → `Dins Fire`;
- `Item_FaroreWind` → `Farores Wind`;
- `Item_NayruLove` → `Nayrus Love`;
- `Item_FairyBless_DefenseDouble` → `Double Defense`.

Being key items, they:

- move with the others;
- can be excluded, in which case the item stays at its own fountain;
- never go to `no_key` sites.

**Logic** (`logic/world.py`). One remake helper:

`'Magic_Meter': "'Magic Meter' or Dins_Fire or Farores_Wind or Nayrus_Love"`

Any of these items brings the meter. Everything OoTR gates on `Magic_Meter` then accepts it: the Lens, the magic arrows, `can_use` of spells, and some enemy rules. There are no access rules and no rupee rules.

**Fill** (`fill.py`).

- With key items set to "Any chest", each fountain becomes a site with a synthetic id (`-201` to `-206`, in table order). Its original content is its remake reward, and it maps to its OoTR location in `site_loc`. The base sets it to filler, as for chests. Its reward is moving, unless excluded.
- **What a fountain may receive:**
  - any key item, song or minor item;
  - **never** a Gold Skulltula token (untested, like song scenes);
  - **never** `Item_BulletBag_Small` or `TBox_DekuSeedBundle` (they hang `GetInEvent`).

  This is my call: block only the hangs that are known, and let the acceptance seed show any others. The fountains are filled before the chests, from contents that are allowed, the same way the song scenes are.
- `Placement` gains `fairies: dict[str, str]`, mapping each OoTR fountain location to what it gives. It is empty with "Vanilla" key items.
- "Vanilla" key items: no fountain sites, and nothing changes.

**Patch** (`randomizer/fairies.py`, new). It mirrors `songs.song_flow_patches`:

```
fairy_flow_patches(read, fairies) -> {flow: bytes}
```

`read` gives the current version of a flow, the full skip's if it wrote one. When `fairies` is non-empty, every fountain is patched, even one that keeps its own reward. That keeps the six consistent: all free, all with the revisit fix. The patches are batch 26's:

- **Grant:** every `Dm_SY_GetInEvent` call with the vanilla `ActorName` is renamed; there can be several, because the full skip copies them. When the item changes, a special entry is pointed at the generic one.
- **Spin attack guide:** skipped when the Power fountain gives something else.
- **Revisit:** the single `IsGet.<own reward>` query reads `HavePlayedEvent.Dm_FairyFountain_<name>`. Exactly one is required; any other count raises.
- **Free:** all `TalkChoice2` and `HasRuppe` checks go to their "yes" case, and every `IncreaseRupee` is skipped. This covers the six fountains and Din's flow (shared `Pay`, `DontPay*`).
- **`TriForcePoint`:** the two-case `IsGet.Item_DinFire` gate goes to its "true" case. Exactly one is required.

Every lookup is by value, never by event index. An unexpected count raises (`FairyPatchError`), so a game update fails loudly. The spike's helpers move here with tests: `_switch_case_targets`, `_retarget`, `make_free`, `patch_fountain` and `patch_triforce`. `songs._rename_flag` and `bypass` are reused, and so is the `bfevfl` support for new strings in grown flows.

**Generate.** It calls `fairy_flow_patches` on top of the full skip's files, as it does for the songs. The fountains' flows can be grown files; the RSTB size changes are handled as for the song flows. The Skulltula check (`_gs_forbidden`) covers the six rewards like any key item.

**Spoiler.** A "Great Fairies" section lists the six fountains and what each gives. The rewards appear in "Key items" with their labels.

**Site.** There is no new setting. The key items help says that with "Any chest" the Great Fairy rewards are shuffled too, and that the fairies are free.

## Tests

- **Items and logic:**
  - `Magic_Meter` holds with any one of the five magic items, and fails without them;
  - the Lens location logic follows from that.
- **Fill:**
  - with "Any chest", the six rewards land on reachable sites, and 20 seeds are beatable;
  - fountains never get a token or the two items that hang;
  - an excluded reward stays at its fountain;
  - "Vanilla" key items give the same placement as today;
  - the songs settings combine with this.
- **Patch, on the real game file** (needs `OOT_NUP`):
  - each fountain's grant gives the new item and a special entry is generic;
  - no rupee check, payment or refusal is reachable from `EntryPoint0`;
  - exactly one revisit query reads `HavePlayedEvent`;
  - the Din gate is gone;
  - the Power guide is skipped only when her item changes;
  - all of this also holds on the full skip's versions.
- **Generate:** a generated mod contains the six patched fountains, `TriForcePoint` and Din's flow, and the spoiler section.

## In-game acceptance

A seed with "Any chest" and the skip on. Its guide lists, from the spoiler, what three fountains give, including one that gives a minor item such as rupees. The aim is to confirm that a fountain can hand over a minor item and that the castle and mountain fountains are mapped correctly.

## Decisions taken (mine, for review)

1. The fairies are free (OoTR). The price is in the TODO.
2. Fountains never get tokens, `Item_BulletBag_Small` or `TBox_DekuSeedBundle`; every other item is allowed.
3. `Magic_Meter` is satisfied by any magic item, so Din's Fire, Farore's Wind and Nayru's Love bring their own meter.
4. All six fountains are patched whenever the rewards are shuffled, including one that keeps its own reward.
5. No access rule: OoTR's regions plus the removed gate and price match the remake.
6. `Item_FairyBless_MP` and `MPDouble` are both "Magic Meter", with no progressive levels (order does not matter, batch 26a).
