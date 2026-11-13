# Free the Bomb Bag — Design (short)

Status: approved by the user on 2026-11-13. Step 1 of the "resemble OoTR" work, which adds the item types OoTR shuffles and this randomizer does not (see `docs/test-batch-19.md`).

## Why

Since commit 2ad8165 the Bomb Bag has stayed fixed in its Dodongo's Cavern chest, because its bombs could not be thrown when it came from any other chest. Batch 19 found the cause. In the remake, bombs cannot be thrown until the **Goron's Bracelet** is owned, wherever the bag comes from. The chest was never the problem.

## Goals, non-goals, anti-goals

- **Goal:** the Bomb Bag is shuffled again like the other key items, and the logic never expects bombs before the bracelet.
- **Non-goal:** testing whether Bombchus need the bracelet. They are gated the same way as a precaution (the user's call).
- **Anti-goal:** a seed that needs bombs before the bracelet can be owned.

## Approaches

| Approach | Trade-off | Decision |
|---|---|---|
| Logic requires the Bomb Bag **and** the bracelet to use bombs | Small change, matches the game | **Chosen** |
| Keep the bag fixed | Nothing to build, but it is exactly the limitation we want to remove | Rejected |
| Give the bracelet at the start | Changes the game | Rejected |

## Design

- **Logic:** a remake helper override, `Bomb_Bag` → `'Bomb Bag' and Progressive_Strength_Upgrade`. OoTR's rules use `Bomb_Bag` everywhere bombs are needed (`Bombs`, `has_bombchus`, `found_bombchus` and the World files), so a single override covers bombs and Bombchus. The bracelet is strength level 1 at Darunia's Joy (fixed, from an event). The overrides sit next to `REMAKE_RULES` in `randomizer/logic/world.py` and are merged into the helpers given to the `Compiler`.
- **Fill:** the Dodongo's Cavern Bomb Bag chest goes back to `needs_event_patch: false` and `strip_event: true` in `location_map.json`, as it was before 2ad8165.
- **Docs:** the README and `docs/TODO.md` say the Bomb Bag moves.
- **Tests:**
  - the logic does not reach a bomb-only location with the bag and without the bracelet, and reaches it with both;
  - the map no longer lists the chest as needing an event patch;
  - with some seed, the fill places the Bomb Bag outside Dodongo's Cavern.
- **In game:** generate a seed whose Bomb Bag is outside its chest and play up to the bombs.

## Left to the builder

The exact test seeds and the bomb-only location used in the logic test.
