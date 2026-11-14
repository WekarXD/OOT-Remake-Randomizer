# Test batch 25: a song on a boss Heart Container (Dungeon Rewards)

Part of "Shuffle Songs: Dungeon Rewards" (plan `docs/superpowers/plans/2026-11-14-songs-dungeon-rewards.md`). The boss Heart Containers give songs. Each one's actor (`Obj_Heart_Container`) is swapped for a **song wrapper** (`Obj_Rando_Item_Melody_*`): a clone of the Gold Skulltula token carrying the song's identity, with the token's animation and parameter table, since songs have none. Its `Hash` and links stay, so it should still appear when the boss dies. This is untested.

Built with `tools/make_song_batch.py <nup> <out> 25`, on the full skip. Leaving Link's house teleports you into **Gohma's room** (`InsideTheDekuTree` start position `DefeatBoss`, next to her Heart Container). You get the Fairy Ocarina, the Kokiri Sword, a Deku Shield and the Fairy Slingshot. Gohma's heart gives **Song of Storms**.

## Setup

- [ ] Remove any other `Rando_*`, `TestBatch*` or `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch25` to `load/0400486024DEC000/`, start a **new game** and leave the house.
- [ ] Equip the sword and the shield if they are not, and assign the Slingshot.

## Check

- [ ] Do you appear in Gohma's room? Does Gohma's fight start (or is she already gone)? ______
- [ ] After beating Gohma, does something appear where the Heart Container would be? What does it look like? ______
- [ ] Picking it up: do you get **Song of Storms** (message, song list), and **not** a Heart Container? ______
- [ ] Does Song of Storms play? ______
- [ ] Does the usual exit (blue warp) still appear and work? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

Attempt 1 (2026-11-14): the Slingshot came without ammo, so it could not shoot. The preset now also gives the Bullet Bag (`Item_BulletBag_Small`) and Deku Seeds (`TBox_DekuSeedBundle`). Rebuilt for attempt 2.

Attempt 2 (2026-11-14): after the items, the screen stays **black** with Link's house music: the map change into the dungeon never finishes. The Deku Tree's map entrance (`FieldAndDungeonEntranceEventRequestActor`) passes the arrival event `Dm_SY_BancChangeArrive_InsideTheDekuTree_01`, and plays the intro unless `HavePlayedEvent.Dm_Deku_0000` is set. Start presets now take a `boot_event`; batch 25 passes that arrival and marks the intro played. Rebuilt for attempt 3.

Attempt 3 (2026-11-14): still black. Attempt 4 teleports to the dungeon's own **entrance** position (`Entrance`), with the same arrival event, to tell whether teleporting into a dungeon fails at all or only the boss-room position does. If it works, walk down to Gohma (climb to the top floor and drop through the web to the basement).
