# Test batch 22: the windmill and crater song patches

Part of "Shuffle Songs: Song Locations" (design: `docs/superpowers/specs/2026-11-14-song-locations-design.md`). Two song scenes check the song they normally give, and both are patched:

- **Windmill** (`Npc_Hylia_009_Adult`): the man only starts his scene (`Dm_MelodyGet_Storm`) if you do **not** own Song of Storms. If Storm came from somewhere else first, that location would be lost. The patch makes his four checks ask whether his own scene has played (`HavePlayedEvent.Dm_MelodyGet_Storm`) instead.
- **Crater** (`Dm_MelodyGet_Fire`): the scene marks `IsGet.Item_Melody_FireBolero` whatever it gives. The patch marks the song it actually gives.

| Scene | Normally | In this batch |
|---|---|---|
| Sheik in the crater | Bolero of Fire | **Song of Storms** |
| Windmill man (adult) | Song of Storms | **Bolero of Fire** |

You get Song of Storms first, at the crater. That is exactly the case that used to stop the windmill scene.

The batch is built on the full cutscene skip (childhood phase, as seeds use it) by `tools/make_song_batch.py`. It uses the first **adult** start preset: Link becomes an adult the way the game does when the Master Sword is drawn again (`ReplaceEquipmentForEraChange`, then `Sequence_IsChildhood` false), then he is teleported.

## Setup

- [ ] Remove any other `Rando_*`, `TestBatch*` or `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch22` to `load/0400486024DEC000/`.
- [ ] Start a **new game** and walk out of Link's house. You receive the **Ocarina of Time**, the **Goron Tunic** and the **Hookshot**, become an **adult**, and are teleported to the **Death Mountain Crater warp pad** (start position `FireBolero`).
- [ ] What the preset sets (sources):
  - the fire quest `SageOfFire` is advanced Ready → StopDaruniaJr → TalkDaruniaJr → MoveStatue → EnterCrater → **MeetSheik**. The order comes from `RSDB/Challenge`; the crater's logic graphs (`DeathMountainCrater_Adult_Prefab_a0e2`, `e63c`) start Sheik's scene around MeetSheik, while `HavePlayedEvent.Dm_MelodyGet_Fire` is unset.
  - the storm quest `SubEvent_GetStormSong` is set to `Ready`. This is a guess: the windmill man's talk checks `SubEvent_GetStormSong_IsAfter_Ready_Exp`, and his talk advances it to `ReadyForGetStormSong` himself.
- [ ] Equip the Goron Tunic if the heat timer appears.

## Check

Crater:

- [x] Are you an adult, with the Master Sword? Yes (attempt 1).
- [x] Does Sheik appear (on arrival, or when you step off the warp pad)? Yes, on arrival (attempt 1).
- [x] Does he give you **Song of Storms** (not the Bolero)? Yes (attempt 1).

Windmill (walk down Death Mountain Trail to Kakariko and enter the windmill):

- [ ] Talk to the man with the box. Does his scene start (he plays the song and you learn it), even though you already own Song of Storms? If not, try playing the ocarina in front of him and note what happens. ______
- [ ] Does he give you the **Bolero of Fire**? ______
- [ ] Do both songs work: Storm (for example in the windmill or at a Gossip Stone grotto), Bolero (warps to the crater)? ______

In general:

- [ ] Did anything look wrong after becoming an adult (equipment, Navi, black screens)? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

Attempt 1 (2026-11-14): becoming an adult works (Master Sword included). Sheik appears on arrival at the crater and gives **Song of Storms**, so the crater patch works. The crater could not be left: the warp pad's ledge needs the Hookshot. Rebuilt for attempt 2 with the Hookshot; only the windmill half is left (needs a new game).
