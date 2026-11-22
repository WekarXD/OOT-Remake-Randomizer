# OoTR "Open" settings: research (2026-11-22)

Goal: OoTR's Open section (Forest, Kakariko Gate, Door of Time, Zora's Fountain,
Gerudo's Fortress, Dungeon Boss Shortcuts), with OoTR's defaults: Closed Forest, Closed
Gate, **Door of Time: Song of Time**, Zora's Fountain closed, Gerudo's Fortress default,
no shortcuts. Only the Door of Time default differs from the remake: the remake asks for
the 3 stones, the Ocarina of Time and the Song of Time (`vanilla_settings.json`:
`open_door_of_time = stones_oot_sot`). With OoTR's default the dungeon rewards can be on
any boss with no deadlock, and the Ocarina of Time scene asks for the three stone
*items*, not the three child bosses. Test batch: `tools/make_open_batch.py` (35a–35h).

## Door of Time

- Flow `DoorOfTime`, challenge `DoorOfTime` (steps Step02 … Step06, Complete).
- `DoorOfTime_CheckStoneNum` (event 12) decides the Ocarina of Time: `Get_StoneOfFire_IsCompleted_Exp`
  then `Get_StoneOfWater_IsCompleted_Exp` (Forest assumed done); all three → `Step03`
  (event 11), else `Step2_1` / `Step2_2` and `DoorOfTime_GetStoneCount`. It is called from
  `Dm_SY_BancChange_EscapeDungeon` only, so it runs when leaving a child dungeon.
- The stones have saved flags `IsGet.Item_Stone_Forest/Fire/Water` (GameDataList Bool).
  A new BoolExp row (`ganon.threshold_program` over them) can replace the three queries:
  35g tests that the game accepts an added row. BoolExp rows are not saved
  (`SaveFileIndex -1`) and the list is not sorted by hash.
- Hyrule Field's Ocarina of Time trigger (`Logic/HyruleField_Child_Prefab_32f7`) checks the
  `DoorOfTime` step against Step04, `HavePlayedEvent.HyruleField_DoorOfTime_Escape` and
  `HyruleField_GetOcarinaOfTime_Area`.
- The door (`Logic/Market_Common_f252`, `ActorLogicGateDoor.isOpen`) reads
  `Market_Child_TimeTempleDoor_Opened` and the `DoorOfTime` step against Step06.
  `DoorOfTime_OpenDoor` (Song of Time at the altar, `Obj_TimeTemple_SpiritStoneBase_A_01`)
  checks `DoorOfTime_IsAfter_Step04_Exp`, the flag and `HavePlayedEvent.Dm_TimeTemple_0010`, then
  sets the flag and Step06.
- Master Sword: `DoorOfTime_DiscoverySword` fires from an area present while
  `Market_Child_FoundMasterSword` is false; `DoorOfTime_Draw` (first time: Rauru) has no
  quest check of its own. 35a: is the flag enough to open the door and draw the sword?
  35b: does the altar take the Song of Time before the Ocarina of Time?
- Open question for 'Song of Time' if 35b fails: open the door when the Song of Time is
  learned (set the flag in the song scenes), which the logic's `can_play(Song_of_Time)`
  covers. The check must also run where the last stone can now come from (an adult boss,
  Rauru), not only on leaving a child dungeon.

## Kakariko Gate

- Guard `Npc_Hylia_Soldier_003`: `ShowItem_ZeldaLetter` removes the letter from the pouch,
  plays `Dm_Kakariko_0010` and sets `Npc_Hylia_Soldier_003_GateOpen` (default false).
- The Happy Mask Shop is `SubEvent_MaskSalesman` (Step01 from `Npc_Hylia_042_Child`;
  `SubEvent_MaskSalesman_IsAfter_Step01_Exp`). 35c: is the gate flag enough, and does the
  shop open with it?

## Zora's Fountain

- `Get_StoneOfWater`: talking to King Zora → Step04/Step05; `StoneOfWater_UseRutoletter`
  sets `Get_StoneOfWater_ReadRutoLetter` and Step06. King Zora's AI schedules
  (`Npc_Zora_KingZora_child/adult`) only switch talks; his position is not a `Presence`
  flag in the maps. 35e/35f: does Step06 move him, as a child and as an adult?

## Gerudo's Fortress

- Rescue: flow `SageOfSpirit_RescueCarpenter`, ints
  `GerudoFortress_Meet_FourCarpenter_NumOfCarpenterFound/Helped`, `Dm_Gerudo_0020` at 4
  helped, challenge `SageOfSpirit` (Step01 `Npc_Hylia_012_Adult`, Step02 `Npc_Gerudo_006`,
  which also sets `Gerudo_phantomdesert_gate`). 35h is exploratory.

## Forest

- Leaving the forest: `test_start.FOREST_EXIT_FLAGS` (already proven: Kokiri boy blocker
  `KokiriForest_Npc_Kokiri_007_Child_Blocker_00` false and the exit scenes played).
- Mido: `KokiriForest_Npc_Kokiri_Mido_Child_Blocker` (default true). 35d.

## Dungeon Boss Shortcuts

Not researched yet: eight dungeons, each with its own flags.
