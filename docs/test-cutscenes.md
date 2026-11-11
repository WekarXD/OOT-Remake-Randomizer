# Cutscene skipping tests

Goal: check in-game that story cutscenes can be skipped without breaking anything. There are three rounds, and each includes everything from the previous one.

## Before you start

- Copy the round's folder from `test-mod/0400486024DEC000/` (`TestScenes1`, `TestScenes2` or `TestScenes3`) to Lichii's `load/0400486024DEC000/` folder.
- Keep **only one test or randomizer mod active at a time**. Remove or disable the others (TestBatch, RandoTest, etc.) before testing.
- Always start a **new game**.
- **The notes matter more than the checkboxes.** If something fails, note where and what you saw.

## Round 1: TestScenes1 (the intro only)

- [ ] When starting the new game, the intro can be skipped with the button.
- [ ] After skipping it, Navi and Saria appear as usual.
- [ ] I get the sword and the shield, and I can enter the Deku Tree.

Notes: ______

## Round 2: TestScenes2 (all cutscenes)

Disable TestScenes1 and enable TestScenes2. New game again.

- [ ] The Deku Tree cutscenes, up to receiving the Kokiri Emerald, appear without the story dialogue.
- [ ] I receive the Kokiri Emerald.
- [ ] The talk with Zelda in the castle garden is shorter. Only her recorded animations, the menu where you choose what to ask her and her questions still appear. The surrounding cutscenes (up to Zelda's Lullaby) are also shorter.
- [ ] I receive Zelda's Letter.
- [ ] I learn Zelda's Lullaby.
- [ ] At the end of each stretch I stay in the same place where I used to end up.

Also, throughout the whole test watch for the following:

- [ ] **Hangs:** the game does not freeze or get stuck in any cutscene. If it happens, note in which cutscene or place.
- [ ] **Unfinished cutscenes:** did any cutscene end up unfinished or with a black screen? If so, note which and where.
- [ ] **Disappearing texts:** no text that should appear is missing (signs, system notices, control explanations). If any is missing, note which and where.

Notes: ______

## Round 3: TestScenes3 (all cutscenes and forced conversations)

Disable TestScenes2 and leave **only TestScenes3** active. New game again.

- [ ] **Mido:** when talking to him his blocking text does not appear, but he still does not let me pass until I have the sword and the shield.
- [ ] **Kokiri at the forest exit:** when bumping into or talking to him while he blocks the way, no line of text appears (round 2b), but he still does not let me pass until I finish the Deku Tree. The small speech bubble he gives when you approach the exit still appears: it cannot be removed with this method.
- [ ] **Deku Scrub in the Deku Tree who gives the order clue:** his full conversation comes back (round 2), and also his siblings' and the one for hitting them.
- [ ] **Z-targeting:** the Kokiri's Z-targeting tutorial no longer appears.
- [ ] I reach the Deku Tree and finish it.
- [ ] I reach Hyrule Castle (Zelda) without problems.
- [ ] **Zelda in the garden:** the first time you see her, the cutscene plays **in full**, as in the original game (round 2b: trimmed, it left Link frozen). If you talk to her again (pressing A), that conversation is shorter. I still receive Zelda's Letter and learn Zelda's Lullaby.
- [ ] **Cutscenes that left Link frozen** (round 2b): now they play in full, with their text, as in the original game. No cutscene leaves Link standing still waiting with no text. There are 12 cutscenes in Kokiri Forest, the Deku Tree, Hyrule Field, the Castle, Lon Lon Ranch and Kakariko, among them the death of the Deku Tree and Zelda in the garden (flows `Dm_Kokiri_0060/0130/0145/0155`, `Dm_Deku_0003`, `Dm_HrlField_0020`, `Dm_HrlCastle_0000/0020/0035/0050`, `Dm_LonLon_0020`, `Dm_Kakariko_0010`).
- [ ] I reach Kakariko without problems.

Things that **still appear** (this is normal, not failures):

- **The Great Deku Tree** still speaks in his first talk, in the long conversation and in his death (round 2b). Each of his lines runs in parallel with an animation; removing it would leave that part of the cutscene empty, and the original game never does that, so it is left alone. His death now plays in full.
- Navi's "Z-target" prompt will still appear. It cannot be removed with this method. Only the Kokiri's tutorial should disappear.
- Gameplay hints stay: the Deku Scrubs that give clues, Navi's notices in dungeons and the Temple of Time altar (round 2).

Notices that are now trimmed **across the whole game**, not just as a child. Note if any behaves strangely:

- [ ] The soft soil spots for planting magic beans.
- [ ] Navi's reminder about Gold Skulltulas.
- [ ] The guards that stop you in Kakariko.

And, as in round 2:

- [ ] **Hangs:** the game does not freeze or get stuck in any cutscene. If it happens, note where.
- [ ] **Black screens:** no cutscene ends up unfinished or with a black screen. If it happens, note which and where.
- [ ] **Missing items:** I receive everything I should (Kokiri Emerald, Zelda's Letter, Zelda's Lullaby, sword, shield...). If something is missing, note what and where.
- [ ] **Disappearing texts:** no text that should appear is missing (signs, system notices, control explanations). If any is missing, note which and where.
- [ ] **Forced conversations that still appear:** note which still appear and where.

Notes: ______

## Results
