# Test batch 26: Great Fairy rewards (spike)

Groundwork for shuffling the Great Fairy rewards (`docs/great-fairies-research.md`). Built with `tools/make_fairy_batch.py <nup> <out> 26a|26b|26c`, on the full skip. Leaving Link's house teleports you onto the fountain's **Triforce point** (a new start position on it, facing the basin) with the Fairy Ocarina and Zelda's Lullaby.

Every variant patches the fountains the way the shuffle would:

- **Another item:** the fountain's `Dm_SY_GetInEvent` call gives another item. The special grant entries (`GetInEvent_GreatFairyDin`, `_Wisdom`, `_Courge`) add their own animations (a new gauge, the double gauge, defense), so they are pointed at the generic `GetInEvent_Demo_NotLookatObjectEntry`. The full skip copies Din's grant (events 308 and 615), and both copies are patched.
- **Free fairies, as in OoTR:** every pay question (`TalkChoice2`) goes to "yes", every rupee check (`HasRuppe`) goes to its "enough" case and every payment (`IncreaseRupee`) is skipped, in the fountain's flow and in Din's (the others call its shared `Pay`). The first visit always grants, so refusing to pay cannot lose the item. `HavePlayedEvent` is set when the event ends, whichever path it took.
- **Revisits:** the fountain reads `HavePlayedEvent.Dm_FairyFountain_<name>` instead of `IsGet.<own reward>`, so a revisit only heals, even when the vanilla reward was found elsewhere.
- **No Din gate:** `TriForcePoint` summons every fairy without `IsGet.Item_DinFire`. Vanilla needs Din's Fire for all fairies but Din, because Din's Fire brings the magic meter.
- **No spin guide:** the Power fairy's spin attack guide (`ActionGuide`) is skipped when she gives something else.

Pouch data (`PouchActorInfo`): Din's Fire, Farore's Wind, Nayru's Love and `Item_FairyBless_MP` all have `ExpansionAvility: MPMaxUP` with `MPMax: 24`, and `Item_FairyBless_MPDouble` has 48. Each of them should bring the magic meter.

| Variant | Fountain | Gives | Start |
|---|---|---|---|
| 26a | Death Mountain Trail (Din), child | Farore's Wind | Double magic (`Item_FairyBless_MPDouble`), no rupees |
| 26b | Hyrule Castle (Power), child | Boomerang | No magic, no Din's Fire |
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

Attempt 2 (2026-11-14), 26a: the same line. The rewrite for attempt 2 had dropped the question patch, and answering "No" leads to `DontPay1`, whose line also says Link has too few rupees. Every `TalkChoice2` now goes to "yes" as well. Checked by walking each fountain's flow from `EntryPoint0`: no question, rupee check, payment or refusal is reachable, and the grant is. Rebuilt for attempt 3 (all three variants).

Attempt 3 (2026-11-14), 26a: the same line. Its label is `Dm_FairyFountain_0600_01` (in `Mals/EUes`, `EventFlowMsg/Dm_FairyFountain_Din.msbt`), reached only from Din's `DontPay2` entry, which the *other* fountains call. **The remake swaps Din's and Power's fountains against the N64.** Power's flow warps its camera to the castle's Triforce point and Din's to the mountain's, so the castle fountain is Power's and the top of Death Mountain is Din's. The other four are where expected. 26a had teleported to the castle, which is Power's fountain and was not patched, so it still charged. Fixed: 26a now goes to the top of Death Mountain (Din) and 26b to the castle (Power). This also matches what the user saw before: the mountain fairy first (Din, no gate), then the castle (Power, which needs Din's Fire). Rebuilt for attempt 4 (26a and 26b; 26c unchanged).

Attempt 4 (2026-11-14): **26b works.** The castle fountain (Power) gives the Boomerang, and it can be used. **26a** (Din, at the top of the mountain) has no rupee problem any more, but it **gives nothing**. Din's flow keeps the full skip's old trimming (its rewrite fails with a conflict, see `docs/test-full-skip-child-2.md`). Both copies of the grant (308, 615) were patched, and on paper both are reached from `EntryPoint0`. Added **26d**, which is 26a without the full skip: if it gives Farore's Wind, the trimming loses the grant; if not, the patch does.

Attempt 5 (2026-11-14): **26d gives Farore's Wind**, so the patch works on Din's vanilla flow. The full skip does rewrite Din: it makes a copy per call site, and the file grows. So either that rewrite loses the grant, or the batch's patch of the grown file does. Only Din's file grows, so only 26a used the new `bfevfl` path that appends strings after the relocated data. Added **26e**: the full skip with Din's fountain untouched, and 100 rupees from the preset (new `StartPreset.rupees`). If it gives Din's Fire, the new string path is the suspect; if not, the full skip's rewrite of Din loses the grant, which would also affect seeds without the fairy shuffle.
