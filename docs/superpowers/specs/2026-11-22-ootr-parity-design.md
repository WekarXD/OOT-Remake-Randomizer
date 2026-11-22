# OoTR parity: everything left — Design

Status: the user asked for everything left at once (2026-11-22). After test batch 33a/33b passed, they said "Estoy cansado de tantas pruebas vamos a darlo como bueno y vamos a hacer directamente una version lo mas parecida a OOTR y sobre esa depuro jugando". So the rest of batch 33 is accepted untested, and debugging happens in play. Research: `docs/remaining-items-research.md`.

## Goal

With key items set to "Any chest", the pool resembles OoTR's default as closely as the remake allows. A seed must stay beatable under the logic. Where the logic and the game differ, the logic must be the stricter one.

## What changes

| Block | Change | Always or setting |
|---|---|---|
| E. Fixed chests | The Boomerang, Hookshot, Iron Boots, Hover Boots, Silver Gauntlets and Mirror Shield chests move like any chest. `needs_event_patch` becomes false, and the story event (`GetEventName`) stays: it does not hand over the item (33a, 33b). | always |
| C. Freestanding Pieces of Heart | Each `Obj_Heart_Piece` actor mapped to an OoTR location becomes a world gift (a wrapper), in both era maps. | always |
| A. NPCs | Kak Anju as Adult (Pocket Egg), DMT Biggoron (Biggoron Sword), Kak Granny Buy Blue Potion, Deku Theater Skull Mask and Mask of Truth become gift rows. | always |
| B. Dungeon rewards | `shuffle_dungeon_rewards` (OoTR's name): `'reward'` (default, as OoTR) shuffles the 3 stones and 6 medallions among the 9 reward scenes; `'vanilla'` keeps them. | setting |

## Decisions (mine, for the user to correct while playing)

1. **Dungeon rewards in the logic.** The game opens the Door of Time and the bridge on the bosses beaten (no flow checks a stone or medallion). So `REMAKE_HELPERS` turns each reward item into its boss's defeat event (`Kokiri_Emerald` → `'Defeat Queen Gohma'`, …, `Spirit_Medallion` → `'Defeat Twinrova'`). The logic then asks for what the game asks for, wherever the rewards land. The Light Medallion stays an item: no rule needs it under these settings.
2. **The rewards only move among the 9 reward sites** (OoTR's `'reward'`): a plain shuffle, since the logic no longer depends on where they go.
3. **Freestanding hearts:** only the actors whose OoTR location is clear are mapped. A doubtful one stays vanilla. Their sites hold what world gifts may hold (wrappable contents).
4. **Out:**
   - the magic beans (one sale would give the placed item ten times; OoTR's default is off);
   - the upgrade scrubs (their grant is shared with a remake-only scrub in Kokiri Forest);
   - the full adult trade (OoTR's default is off);
   - the pot, crate and grotto hearts (not found as actors).
5. **Items:**
   - `Item_PocketEgg` is OoTR's `Pocket Egg`, a key item: it starts the vanilla trade chain;
   - `Item_Sword_Biggoron`, `Item_Bottle_BluePotion` and the Deku stick and nut bags are minor items.

## Tests

- The six chests are in the fill.
- The gift rows rename only their grants, in vanilla and full-skip versions.
- A freestanding heart's wrapper is built in both era maps.
- Each reward scene renames its grant.
- The logic maps each reward to its defeat event.
- 20 seeds with `shuffle_dungeon_rewards='reward'` are beatable. With `'vanilla'`, the rewards stay.
- A generated mod contains it all.
