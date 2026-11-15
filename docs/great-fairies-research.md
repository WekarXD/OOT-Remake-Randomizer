# Great Fairies in the remake: research notes (2026-11-14)

This is the groundwork for shuffling the 6 Great Fairy rewards, as OoTR does. The user agreed to the approach on 2026-11-14:

1. research;
2. remake logic rules;
3. a test batch with a teleport next to each fountain;
4. the option itself, always on when key items are shuffled.

## The fountains

| Remake flow | Reward (`ActorName`) | Price (rupees) | OoTR location |
|---|---|---|---|
| `Dm_FairyFountain_Power` | `Item_FairyBless_MP` | 50 | HC Great Fairy Reward (the castle fountain in the remake) |
| `Dm_FairyFountain_Wisdom` | `Item_FairyBless_MPDouble` | 200 | DMC Great Fairy Reward (Magic Meter) |
| `Dm_FairyFountain_Courage` | `Item_FairyBless_DefenseDouble` | 500 | OGC Great Fairy Reward (Double Defense) |
| `Dm_FairyFountain_Din` | `Item_DinFire` | 25 | DMT Great Fairy Reward (the mountain-top fountain in the remake) |
| `Dm_FairyFountain_Frore` | `Item_FaroreWind` | 100 | ZF Great Fairy Reward (Farore's Wind) |
| `Dm_FairyFountain_Nayru` | `Item_NayruLove` | 300 | Colossus Great Fairy Reward (Nayru's Love) |

- **The grant:** each scene calls `Dm_SY_GetInEvent:GetInEvent*` with the reward's `ActorName`. The variants are `GetInEvent_GreatFairyDin`, `_GreatFairyWisdom`, `_GreatFairyCourge` and `GetInEvent_Demo_NotLookatObjectEntry`.
- **Prices:** the remake's Great Fairies **charge rupees**, which OoTR's do not.
  - On the first visit (`FirstTimeAnother`) the fairy asks whether you pay (`EventQueryTalkChoice2`), then checks `EventQueryHasRuppe` for the price.
  - The shared pay, appear and disappear entries live in `Dm_FairyFountain_Din` (`Pay`, `DontPay1`, `DontPay2`, `GreatFairy_Appear`, `GreatFairy_Disappear`).
  - The 500-rupee Courage fairy needs the bigger wallet (the remake's wallets hold 200, then 500; batch 19).
- **Trigger:** playing Zelda's Lullaby at the fountain's Triforce point. The `TriForcePoint` entries are `Demo_FairyFountain_<name>`, plus `Check_MeetFirst`, `Check_Complete` and `RemainNumber`.
- **Each scene reads its own reward**, like the windmill did with Song of Storms. `EntryPoint0` branches on the following, where case value 0 is true and 1 is false:
  - `HavePlayedEvent.Dm_FairyFountain_<name>` false: the first time, `FirstTimeAnother`.
  - Played, and `IsGet.<reward>` false: `VisitedNoAbility`, the offer again.
  - Played, and `IsGet.<reward>` true: `RecoverSequence`, healing only.

  With the reward shuffled, the ownership check must read the fountain's own grant instead, or a reward found elsewhere would turn the fountain into healing only.
- **Din's flow also reads every other reward** (`IsGet` of MP, MPDouble, DefenseDouble, Farore's Wind and Nayru's Love), along with `GreatFairy_MeetFirst`, `Meet_GreatFairy_RemainNumber == 2` and `PlayerStatus.MPMax == 0` (which leads to `GreatFairy_HasNoMPOnDinDemo`).

## Order: the `Meet_GreatFairy` quest

The steps are, in order:

1. `Ready`;
2. `GoToTopOfMountain`, set when you leave Dodongo's Cavern (`Dm_SY_BancChange_EscapeDungeon` 35);
3. `GoToFountain`;
4. `GetFairyBreath`;
5. `GoToHyruleCastle`;
6. `Complete`.

`TriForcePoint` sets `GoToHyruleCastle` and `Complete`. The Death Mountain Trail logic graphs (`DeathMountainTrail_Child_Prefab_*`) read `Meet_GreatFairy_IsAfter_GetFairyBreath_Exp`.

The user saw this in game: **the Hyrule Castle fountain (Din) cannot be used until the one at the top of Death Mountain has been visited.** The DMT fountain itself probably needs Dodongo's Cavern done. OoTR has neither rule, so the logic needs remake rules for them.

## Magic

From batch 19:

- **Din's Fire from a chest:** it grants the magic meter on the first pickup.
- **`Item_FairyBless_MP`:** it gave the **spin attack**, not magic.

What each fountain reward really does, and where the magic meter comes from, is to be checked in the test batch.

## Findings for batch 26 (2026-11-14)

- **Where the fountains are:** inside the overworld maps, not in maps of their own (`DeathMountainTrail_*`, `HyruleCastle`, `DeathMountainCrater_*`, `ZoraFountain_*`, `DesertColossus_*`, `GanonCastle`). Each has an `Obj_TriForcePoint_A_*` actor at the spot where Link stands.
- **Din's and Power's fountains swap places against the N64** (batch 26, attempt 3): each flow's camera warps to its fountain's Triforce point, and Power's goes to the castle while Din's goes to the top of Death Mountain. The others are Wisdom at DMC, Courage at OGC, Frore at ZF and Nayru at the Colossus.
- **The order is Din (the mountain) first.** This matches what the user saw. `TriForcePoint:Sub_PlayOcarinaSequence_FairyFountain` takes `SpecialAbility` (Power 1, Din 2, Frore 3, Wisdom 4, Nayru 5, Courage 6). For every ability except Din's it checks `IsGet.Item_DinFire`; without it, Navi talks and the fairy does not come. The quest steps at the mountain (`GoToFountain`, `GetFairyBreath`, set by `DeathMountainTrail_Common_*` logic) only send you on and stop the falling rocks. The Din visit sets `GoToHyruleCastle`. `HyruleCastle_Prefab_b02d` reads `HavePlayedEvent.Dm_FairyFountain_Power`, which may be what the user saw at the castle.
- **Magic:** in `PouchActorInfo`, Din's Fire, Farore's Wind, Nayru's Love and `Item_FairyBless_MP` each have `MPMaxUP` with `MPMax` 24, and `MPDouble` has 48. The Power fairy shows the spin attack guide (`ActionGuide` type 5) after her grant.
- **Din's entry** reads `GreatFairy_MeetFirst` (first fairy ever), then `IsGet.Item_DinFire`, not `HavePlayedEvent`. The other fountains read `HavePlayedEvent.Dm_FairyFountain_<name>`, then `IsGet.<reward>`.
- **`HavePlayedEvent` is set when the event ends**, whichever path it took. With the price kept, refusing to pay would mark the fountain as visited. GameDataList is a big-endian BYML v7 with hashed names, so there is no cheap new per-fountain flag. That is why batch 26 makes the fairies free, as OoTR does.
- **The full skip copies some events**, for example Din's grant at 308 and 615. It also puts its new data between the string pool and the RELT. `bfevfl` now appends new strings after the relocated data and rebuilds the RELT in that case.

## Next

Done:

- test batch 26 (`docs/test-batch-26.md`);
- the design (`docs/superpowers/specs/2026-11-15-great-fairies-design.md`);
- the implementation (`docs/superpowers/plans/2026-11-15-great-fairies.md`).

The acceptance seed `HADAS1` is in `docs/test-great-fairies.md`.
