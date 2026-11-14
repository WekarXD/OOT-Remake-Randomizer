# Test batch 26: Great Fairy rewards (spike)

Groundwork for shuffling the Great Fairy rewards (`docs/great-fairies-research.md`). Built with `tools/make_fairy_batch.py <nup> <out> 26a|26b|26c`, on the full skip. Leaving Link's house teleports you onto the fountain's **Triforce point** (a new start position on it, facing the basin) with the Fairy Ocarina and Zelda's Lullaby.

Every variant patches the fountains the way the shuffle would:

- **Another item:** the fountain's `Dm_SY_GetInEvent` call gives another item. The special grant entries (`GetInEvent_GreatFairyDin`, `_Wisdom`, `_Courge`) add their own animations (a new gauge, the double gauge, defense), so they are pointed at the generic `GetInEvent_Demo_NotLookatObjectEntry`. The full skip copies Din's grant (events 308 and 615), and both copies are patched.
- **Free fairies, as in OoTR:** every rupee check (`HasRuppe`) goes to its "enough" case and every payment (`IncreaseRupee`) is skipped, in the fountain's flow and in Din's (the others call its shared `Pay`). The first visit always grants, so refusing to pay cannot lose the item. `HavePlayedEvent` is set when the event ends, whichever path it took.
- **Revisits:** the fountain reads `HavePlayedEvent.Dm_FairyFountain_<name>` instead of `IsGet.<own reward>`, so a revisit only heals, even when the vanilla reward was found elsewhere.
- **No Din gate:** `TriForcePoint` summons every fairy without `IsGet.Item_DinFire`. Vanilla needs Din's Fire for all fairies but Din, because Din's Fire brings the magic meter.
- **No spin guide:** the Power fairy's spin attack guide (`ActionGuide`) is skipped when she gives something else.

Pouch data (`PouchActorInfo`): Din's Fire, Farore's Wind, Nayru's Love and `Item_FairyBless_MP` all have `ExpansionAvility: MPMaxUP` with `MPMax: 24`, and `Item_FairyBless_MPDouble` has 48. Each of them should bring the magic meter.

| Variant | Fountain | Gives | Start |
|---|---|---|---|
| 26a | Hyrule Castle (Din), child | Farore's Wind | Double magic (`Item_FairyBless_MPDouble`), no rupees |
| 26b | Death Mountain Trail (Power), child | Boomerang | No magic, no Din's Fire |
| 26c | Death Mountain Crater (Wisdom), adult | Nayru's Love | No magic; Goron Tunic |

## Setup

- [ ] Remove any other `Rando_*`, `TestBatch*` or `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch26a` (then `b`, then `c`) to `load/0400486024DEC000/`, start a **new game** and leave the house.

## Check (each variant)

- [ ] Do you appear inside the fountain, on the Triforce symbol? ______
- [ ] Playing Zelda's Lullaby there: does the Great Fairy appear (26b and 26c: without Din's Fire, Navi should not stop you)? ______
- [ ] Answering **No** to paying: does she still give the item? ______
- [ ] Do you get the variant's item (message, item screen)? ______
- [ ] The magic bar after the item: none, normal or double? (26a: was it double before?) ______
- [ ] Can you use the item (26a Farore's Wind, 26c Nayru's Love; magic spent)? ______
- [ ] Leave the fountain, come back and play the Lullaby again: does she only heal, without offering anything? ______
- [ ] 26b: no spin attack guide after the Boomerang? ______
- [ ] Any hang or black screen? When? ______

## Results

Attempt 1 (2026-11-14), 26a: the fairy says Link **has too few rupees** and gives nothing. Only the pay question had been patched, but the full skip goes straight to the rupee check (event 676 -> 17, no question) and inlines `Pay`'s body (`IncreaseRupee` at 677 and 265, a second check at 602). The batch now passes every `HasRuppe` and skips every `IncreaseRupee` instead. Rebuilt for attempt 2 (all three variants).
