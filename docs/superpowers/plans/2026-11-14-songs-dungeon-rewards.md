# Shuffle Songs: Dungeon Rewards — Design and Plan (short)

The user asked to "do everything that is left at once, no questions, test at the end" (2026-11-14), so every call below is mine and is listed for review.

**Goal:** OoTR's third "Shuffle Songs" value. The 12 songs go only to OoTR's 12 dungeon-reward locations (non-MQ list in OoTR `Fill.py`). The other 10 song scenes become ordinary item locations, as in Anywhere.

The 12 locations:

- the 8 boss Heart Containers (Queen Gohma, King Dodongo, Barinade, Phantom Ganon, Volvagia, Morpha, Twinrova, Bongo Bongo);
- Sheik in Ice Cavern;
- Song from Impa;
- Gerudo Training Ground Maze Path Final Chest (Ice Arrows);
- Bottom of the Well Lens of Truth Chest.

## Calls (mine)

- **All 12 sites always get a song.** 12 songs fill 12 sites, so the 8 boss hearts always give a song, and their 8 Heart Containers join the general pool as minor items.
- **Boss hearts:** each `Obj_Heart_Container` in its dungeon's `*_Static` banc (one per dungeon, found by scanning) has its `Gyaml` replaced by a wrapper `Obj_Rando_<song>`, a clone of the token as for Skulltulas. Its `Hash` and links are kept, so the boss logic that reveals it still applies. Untested in game.
- **Song wrappers:** songs lack `AnimationRef` and `GameParameterTableRef`, so `wrap_source` accepts a song with only `ActorNameRef`, `ModelInfoRef` and `PouchContentRef`. The token's two refs are kept. Only `Item_Melody_*` contents get this, so Tokensanity outputs do not change.
- **GTG and BotW chests:** they are in `NO_KEY_TARGET_ZONES`. As in OoTR they take songs (only songs). That risks the key-logic issue, accepted and noted. Their Ice Arrows and Lens of Truth join the key-item pool.
- **Dungeon Rewards with vanilla key items** raises `FillError`, as Anywhere does.
- **Song scenes** that give a non-song keep their lesson, ended with the plain `PlayAuto` (batch 24).

## Tasks (inline, TDD; test in game at the end)

1. **`wrappers`:** songs can be wrapped. Test: `wrap_source(game, 'Item_Melody_StormSong') == 'Item_Melody_StormSong'`, a non-song content's result is unchanged, and the cloned pack keeps the token's AnimationRef.
2. **`game.boss_hearts()`:** returns `[(hash, banc, location)]`, 8 rows, one per dungeon. A test checks the 8 OoTR locations.
3. **`fill`:**
   - `'dungeon_rewards'` in `SHUFFLE_SONGS`;
   - synthetic heart sites (`HEART_SITE_IDS`, -101…) and the scene sites from Anywhere;
   - a song phase restricted to the 12 reward sites (assumed fill, owning the remaining songs and the key items to place);
   - then the key items, then the rest;
   - `Placement` gains `hearts: {location: actor}`.

   Tests:
   - songs are exactly on the 12 sites;
   - 20 seeds are beatable;
   - Heart Containers are moved, and the multiset is kept;
   - vanilla keys raise;
   - Off, Song Locations and Anywhere are unchanged.
4. **`patch.write_mod`:** takes `actor_swaps: {hash: gyaml}` and builds wrappers for the swapped songs. **`generate`:** passes the hearts. **`spoiler`:** a Boss hearts section, songs in "Key items". **Site and browser:** the option is added. Tests: in a generated mod, each heart's actor is its song's wrapper, and the wrapper pack exists.
5. **Test batch 25:** teleport to Gohma's room. Her heart gives Song of Storms, and Impa gives a Deku Shield. **Acceptance seed** with Dungeon Rewards. Docs: README, TODO and guides. Final review, then wait for the user's test.
