"""Test batch 35: OoTR's "Open" settings, what the game needs for each (on the full skip).

35a Door of Time open: `Market_Child_TimeTempleDoor_Opened` set; child in the Temple of
    Time with the Kokiri Sword. Is the door open? Can Link draw the Master Sword?
35b Song of Time at the altar before the Ocarina of Time: child in the Temple of Time
    with the Fairy Ocarina and the Song of Time. Does playing it at the altar open the door?
35c Kakariko Gate open: `Npc_Hylia_Soldier_003_GateOpen` set; child at Kakariko's
    entrance. Is the gate to Death Mountain open? Is the Happy Mask Shop open?
35d Open Forest (Mido): `KokiriForest_Npc_Kokiri_Mido_Child_Blocker` cleared; child by
    the Lost Woods with nothing. Does Mido let Link to the Deku Tree?
35e Zora's Fountain, child: `Get_StoneOfWater` moved to Step06 (Ruto's Letter read);
    child at Zora's Domain. Has King Zora moved? Can Link reach the fountain?
35f Zora's Fountain, adult: the same quest steps, adult at Zora's Domain.
35g Door of Time on the stones: the Ocarina of Time check (`DoorOfTime_CheckStoneNum`)
    asks for the three stone items, through a new GameDataList BoolExp row; child at
    Queen Gohma with the Goron Ruby and the Zora Sapphire (Dodongo's Cavern and Jabu not
    done). After Gohma, Hyrule Field by the market: does Zelda's escape play?
35h Gerudo's Fortress open (exploratory): `SageOfSpirit` to Step02 and four carpenters
    helped; adult at the fortress. Are the guards friendly? Do the gates open?
Usage: python -I tools/make_open_batch.py <nup> <out_mod_dir> <35a..35h>
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_start_batch import Batch, add_start, write_mod  # noqa: E402
from randomizer import ganon  # noqa: E402
from randomizer.formats import byml  # noqa: E402
from randomizer.formats.bfevfl import EventFlow, set_string_param  # noqa: E402
from randomizer.full_skip import files_with_fallback  # noqa: E402
from randomizer.game import GameData  # noqa: E402
from randomizer.generate import FULL_SKIP_PHASE  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402
from randomizer.test_start import StartPreset  # noqa: E402

STONE_FLAGS = ('IsGet.Item_Stone_Forest', 'IsGet.Item_Stone_Fire', 'IsGet.Item_Stone_Water')
STONES_EXP = 'Rando_HasAllStones_Exp'
DOOR_FLOW = 'DoorOfTime'
STONE_EXPS = ('Get_StoneOfFire_IsCompleted_Exp', 'Get_StoneOfWater_IsCompleted_Exp')

OCARINA, SWORD, SHIELD = 'Item_Ocarina_Fairy', 'Item_Sword_Kokiri', 'TBox_Shield_Deku'
ZORA_STEPS = tuple(('Get_StoneOfWater', s) for s in
                   ('Step01', 'Step02', 'Step03', 'Step04', 'Step05', 'Step06'))
TEMPLE = ('Market_Child', 'LightPrelude')

PRESETS = {
    '35a': StartPreset(*TEMPLE, items=(SWORD, SHIELD),
                       flags=(('Market_Child_TimeTempleDoor_Opened', True),)),
    '35b': StartPreset(*TEMPLE, items=(SWORD, SHIELD, OCARINA, 'Item_Melody_TimeSong')),
    '35c': StartPreset('KakarikoVillage_Child', 'KakarikoVillage_Entrance',
                       items=(SWORD, SHIELD), flags=(('Npc_Hylia_Soldier_003_GateOpen', True),)),
    '35d': StartPreset('KokiriForest_Child', 'KokiriForest_FrontOfLostWood',
                       flags=(('KokiriForest_Npc_Kokiri_Mido_Child_Blocker', False),)),
    '35e': StartPreset('ZoraDomain_Child', 'ZoraDomain_FromZoraRiver', items=(SWORD, SHIELD),
                       challenge_steps=ZORA_STEPS),
    '35f': StartPreset('ZoraDomain_Adult', 'ZoraDomain_FromZoraRiver', adult=True,
                       challenge_steps=ZORA_STEPS),
    '35g': StartPreset('InsideTheDekuTree', 'DefeatBoss',
                       items=(OCARINA, SWORD, SHIELD, 'Item_Range_SlingShot',
                              'Item_BulletBag_Medium', 'Item_Stone_Fire', 'Item_Stone_Water'),
                       boot_event='Dm_SY_BancChangeArrive_InsideTheDekuTree_01'),
    '35h': StartPreset('GerudoFortress_Adult', 'GerudoFortress_FromGerudoValley', adult=True,
                       challenge_steps=(('SageOfSpirit', 'Step01'), ('SageOfSpirit', 'Step02')),
                       ints=(('GerudoFortress_Meet_FourCarpenter_NumOfCarpenterFound', 4),
                             ('GerudoFortress_Meet_FourCarpenter_NumOfCarpenterHelped', 4))),
}


def with_stones_exp(raw: bytes) -> bytes:
    """GameDataList with a new BoolExp row: all three stone items owned."""
    ver, root = byml.load(raw)
    rows = root['Data']['BoolExp']
    template = rows[0]
    row = {**template, 'Hash': type(template['Hash'])(ganon.mm3(STONES_EXP)),
           'Values': ganon.threshold_program(STONE_FLAGS, 3)}
    data = {**root['Data'], 'BoolExp': list(rows) + [row]}
    return byml.dump({**root, 'Data': data}, ver, big_endian=True)


def door_on_stones(data: bytes) -> bytes:
    """`DOOR_FLOW` with the Ocarina of Time check's quest queries asking for `STONES_EXP`."""
    flow = EventFlow(data)
    hits = [e.index for e in flow.events
            if e.query == 'EventQueryIsGameDataBoolExp'
            and flow.action_params(e.index).get('GameDataName') in STONE_EXPS]
    if len(hits) != 3:
        raise ValueError(f'{DOOR_FLOW}: expected 3 stone queries, found {hits}')
    for i in hits:
        data = set_string_param(data, i, 'GameDataName', STONES_EXP)
    return data


def build(nup: NupArchive, name: str) -> dict[str, bytes]:
    game = GameData(nup)
    batch = Batch(nup)
    batch.files.update(batch.unpack(files_with_fallback(game, FULL_SKIP_PHASE)[0]))
    if name == '35g':
        batch.files[ganon.GAMEDATA_LIST] = with_stones_exp(batch.read(ganon.GAMEDATA_LIST))
        door = game.flow_path(DOOR_FLOW)
        batch.files[door] = door_on_stones(batch.read(door))
    add_start(batch, PRESETS[name])
    return batch.compressed()


def main() -> None:
    if len(sys.argv) != 4 or sys.argv[3] not in PRESETS:
        raise SystemExit(__doc__)
    nup_path, out, name = sys.argv[1:4]
    with NupArchive(nup_path) as nup:
        write_mod(out, build(nup, name))


if __name__ == '__main__':
    main()
