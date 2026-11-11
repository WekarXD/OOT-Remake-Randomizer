# Test batch 1

Goal: check three things with simple mods before continuing with the randomizer.

## Before you start

- Disable or remove the earlier mods **RandoTest** and **RandoTest_Gancho**.
- Use **only one TestBatch at a time** (enable one, test, disable it, then the other).
- Copy the batch folder from `test-mod/0400486024DEC000/` (TestBatch1 or TestBatch2) to Lichii's mod folder for the game.
- For each test note: the item received, the text or scene that appears, whether it shows up in the inventory or menu, and whether it can be used.
- **The notes matter more than the checkboxes.** A checkbox alone is no use to us if we do not know what happened.
- Meaning of the checkboxes in each test: **OK** = I receive the new item indicated and it appears in the menu or inventory; **FAIL** = I receive nothing, I receive the original item, the item does not appear or cannot be used, or the game hangs. If something else happens, describe it in the notes.

## TestBatch1 (child save, Kokiri Forest)

### Mido's house chests

Mido's house has 4 chests. You are not told which is which: open them all and identify each one by what it gives you. Fill in the table (if the chests are not where indicated, note where you find them):

| Chest (position in the house) | What it gave me |
|---|---|
| Chest 1: ______ | ______ |
| Chest 2: ______ | ______ |
| Chest 3: ______ | ______ |
| Chest 4: ______ | ______ |

Possible new items: Longshot, Golden Gauntlets, Mirror Shield, Ice Arrows. If any chest gives you a rupee (blue or green) or anything else, write it down as is.

### Test 1: Kokiri Sword (R1)
- Where: hidden area (narrow passage) of Kokiri Forest, the Kokiri Sword chest.
- Normally gives the Kokiri Sword; now the chest contains a green rupee.
- What to do: open the chest. Note whether you still receive the sword or only the rupee.
- Note: item received: ______  text/scene: ______  in inventory: ______  usable: ______
- [ ] OK (I receive the green rupee)   [ ] FAIL (I receive the sword anyway, or nothing, or the game hangs)

### Test 2: Longshot without Hookshot (R2)
- Where: Mido's house, the chest that gives the Longshot.
- What to do: open it without having the Hookshot. Check whether you receive it, whether it shows in the menu and whether it can be used.
- Note: item: ______  text/scene: ______  in inventory: ______  usable: ______
- [ ] OK (I receive the Longshot and it shows in the menu)   [ ] FAIL

### Test 3: Golden Gauntlets without the bracelet or silver (R2)
- Where: Mido's house, the chest that gives the Golden Gauntlets.
- What to do: open it without having the earlier gauntlets.
- Note: item: ______  text/scene: ______  in inventory: ______  usable: ______
- [ ] OK (I receive the gauntlets and they show in the menu)   [ ] FAIL

### Test 4: Mirror Shield as a child (R3)
- Where: Mido's house, the chest that gives the Mirror Shield.
- What to do: open it as a child. Check whether it stays in the inventory or is lost (for example when changing screens or saving and reloading).
- Note: item: ______  text/scene: ______  in inventory: ______  usable: ______  lost: ______
- [ ] OK (I receive it and it is kept)   [ ] FAIL (I do not receive it, it is lost or the game hangs)

### Test 5: Ice Arrows without a bow (R2/R3)
- Where: Mido's house, the chest that gives the Ice Arrows.
- What to do: open it without a bow. Check whether anything appears in the menu and whether it can be used.
- Note: item: ______  text/scene: ______  in inventory: ______  usable: ______
- [ ] OK (I receive the arrows and they show in the menu)   [ ] FAIL

## TestBatch2 (needs an adult save)

### Test 6: Serenade of Water (R1)
- Where: Ice Cavern, the chest at the end (normally the Iron Boots).
- The chest now contains a blue rupee.
- What to do: reach the end and open the chest. Check whether you still learn the Serenade of Water and whether you receive the Iron Boots.
- Note: item: ______  scene/text: ______  Serenade learned: ______
- [ ] OK (I receive the blue rupee and the Serenade is learned)   [ ] FAIL (I receive the boots, the Serenade is not learned or the game hangs)

## Final notes

When you finish, send the results and any odd details (texts, game crashes, scenes that hang).

## Results

### TestBatch1 (child save, Kokiri Forest)
- **Mido's house**: all four new items were received and can be used:
  - Longshot, without having the Hookshot first.
  - Golden Gauntlets, without having the earlier gauntlets first.
  - Mirror Shield, as a child.
  - Ice Arrows, as a child. They also unlocked the magic meter.
- **Kokiri Sword chest** (R1): gave the green rupee, but its event still showed the sword scene and gave the sword. The sword can be used, but does not show in the inventory. So this chest needs its event handled.

### TestBatch3 (sword chest without its event)
- The event (`GetEventName`) was removed from the Kokiri Sword chest and the Boomerang was put inside. The chest gave the Boomerang and did **not** give the sword. An event that only hands over the item can be removed without problems.
- The Deku Tree part could not be tested: the old save had lost the sword that the event gave.

### TestBatch2 (adult save)
- Pending.
