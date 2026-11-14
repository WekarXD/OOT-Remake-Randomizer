# Shuffle Songs: Anywhere — Design (short)

Status: the user chose "any item, as OoTR" and asked me to go ahead ("ponte directamente", 2026-11-14). Follows Song Locations (`2026-11-14-song-locations-design.md`, released). Batch 23 (`docs/test-batch-23.md`) is the spike it builds on.

## Why

This is OoTR's second "Shuffle Songs" value. The 12 songs join the general item pool, and the 12 song scenes become ordinary item locations.

## Goals, non-goals, anti-goals

- **Goal:** with Anywhere, songs can land in any eligible site:
  - an eligible chest;
  - a Gold Skulltula that drops, under Tokensanity;
  - one of the 12 song scenes.

  The song scenes can give anything the fill puts there: a song, a key item or a minor item. The seed stays beatable.
- **Goal:** Off and Song Locations behave exactly as today.
- **Non-goals:** Dungeon Rewards (the next value); chest models or texts (a chest holding a song shows a rupee, accepted in batch 19); dialogue text.
- **Anti-goal:** a song scene that hands over its original song as well as its new item.

## What is known

- **A chest can give a song:** batch 19, Song of Storms (`Drop__DropActor` = `Item_Melody_*`).
- **A song scene can give any item** by renaming its grant's `ActorName` (`GetPouchContent:GetPouchContentByActorName`). Batch 23 confirmed a red rupee (`Obj_Rupee_Red`) and Deku Nuts (`TBox_DekuNutBundle`), each with its "you got" message. Batch 7 confirmed a key item from a gift scene.
- **The lesson has to go when a scene gives no song.** It ends with `LearningOcarinaPlayAuto` or `PlayAutoForSeek`, which *adds the melody just played* to the pouch, so the original song would come along. With Skip cutscenes the lessons are already unreachable from the scene's entry (checked in batch 23). Without the skip they must be bypassed.
- **The crater scene sets `IsGet.Item_Melody_FireBolero` itself.** Song Locations renames it to the new song's flag. A non-song item has no such flag, so the event is bypassed.
- **The windmill reads `IsGet.Item_Melody_StormSong`.** The Song Locations patch (read `HavePlayedEvent.Dm_MelodyGet_Storm` instead) applies whenever Storm is not the windmill's item.

## Approaches

| Approach | Trade-off | Decision |
|---|---|---|
| Song scenes join the fill as 12 extra sites (synthetic site ids mapped to their OoTR locations); songs join the moving items with the key items | Reuses the whole fill (assumed fill, ammo, Skulltulas, filler) | **Chosen** |
| A separate songs-only phase, then key items | Cannot put key items or minor items on song scenes, so it is not Anywhere | Rejected |

## Design

**Setting.** `SHUFFLE_SONGS` gains `'anywhere'` (site label "Anywhere"). With key items in `vanilla` mode there are no other sites to move songs to, so Anywhere raises `FillError` ("Anywhere needs key items shuffled"). That is my call: it is clearer than silently falling back to Song Locations.

**Fill.**

- Each song location becomes a site with a synthetic negative id (`-1` … `-12`, in `SONGS` order). Its original content is its song, and it maps to its OoTR location in `site_loc`.
- Songs join `moving` with the key items. In the logic they enter `fixed` and the `owned` lists as their OoTR names.
- Song scenes may receive key items, songs, ammo and filler like any mapped chest. They are not in `no_key`.
- `Placement.chests` leaves the synthetic ids out. `Placement.songs` maps each song location to whatever its site received.
- The Skulltula check (`_gs_forbidden` in `generate`) also looks at the songs, so a song is never put on a Skulltula that cannot drop it.

**Patch.** `song_flow_patches` accepts any actor per location, not only a permutation of the songs. For a location whose item changed:

- **New item is a song:** as today. The grant is renamed, the lessons get the new melody, and the lesson end is retargeted.
- **New item is not a song:**
  - the grant is renamed;
  - the lesson's **end** (`LearningOcarinaPlayAuto` / `PlayAutoForSeek`, the only part that adds the melody played to the pouch) is **retargeted to the plain `Dm_SY_Ocarina:PlayAuto`** (used by the frogs' minigame). It closes the lesson and plays the tune back without adding any song. Removing the end, or the whole lesson, froze the crater in batch 24b, because the end also closes the lesson's dialog and ends the ocarina sequence. The teacher therefore plays the original notes and Link repeats them without getting that song. (`bypass` stays for the crater's `IsGet` set;)
  - in the crater, the `IsGet` set is bypassed the same way.

  Bypassing changes no event, string or size. Entry subflow lists may still name a bypassed call, which is a harmless superset.
- **Windmill:** patched whenever its item is not Song of Storms.

**Spoiler.**

- Songs found in chests or Skulltulas join the "Key items" list, labelled with their OoTR names.
- The "Songs" section lists what each song scene gives.
- `_label` knows song actors.

**Site.** The select gains "Anywhere". The hint says that the song scenes can give any item.

**Test batch 24** (teleport next to each scene, per the user's rule):

- **24a, Impa, without the full skip:** this checks the lesson bypass, which only happens without the skip. That is a justified exception to "always on the full skip". Impa gives a Deku Shield (`TBox_Shield_Deku`, a chest-style minor item).
- **24b, the crater, adult preset:** Sheik gives the Hookshot, which checks the crater bypass.

**Acceptance:** an Anywhere seed with the skip.

## Left to the builder

- The exact synthetic-id scheme.
- How the spoiler marks synthetic sites.
- The test seeds.
