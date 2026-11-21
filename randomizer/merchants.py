"""The expensive merchants sell once (NPC gifts batch 3a, design
docs/superpowers/specs/2026-11-21-npc-gifts-batch-3a-design.md; test batches 31 and 32).

In the game both resell (31d, 31e2), and Medigoron refuses when the Giant's Knife, the
broken knife or Biggoron's Sword is in the pouch. With Shuffle Expensive Merchants each
sells once, whatever it holds. The sold-out flags are saved flags of Medigoron's that this
patch leaves with no setter: his talk goes straight to the sale, skipping his pouch checks
and his one-time comments (`SageOfFire_Check`), the only places that set them.
- Medigoron: the sale (`SimpleShop`, his entry) sets `MEDIGORON_SOLD` after the grant;
  his talk asks it first (his own query on it, event 69) and only sells while it is off.
- The carpet salesman (the child one calls the adult's `Talk`): `Npc_Hylia_044_Buy`,
  which `SimpleShop` sets after his sale, is not saved (`SaveFileIndex` -1), so it is
  renamed to `CARPET_SOLD`. His talk asks it before his pitch and, once set, says
  "Tú aquí otra vez" and ends, without opening the rupee display.
"""
from __future__ import annotations

from collections.abc import Callable

from .formats.bfevfl import (ACTION, END, SUBFLOW, SWITCH, EventFlow, patch_pointers,
                             set_string_param)
from .formats.evfl_append import ActionSpec, append_events

MEDIGORON = 'Npc_Goron_Medigoron_Adult'
CARPET = 'Npc_Hylia_044_Adult'
SHOP = 'SimpleShop'
MEDIGORON_SOLD = 'HaveTalked_Special.Npc_Goron_Medigoron_Adult_Talk_Event26'
CARPET_SOLD = 'HaveTalked_Special.Npc_Goron_Medigoron_Adult_Talk_Event3'
CARPET_BUY = 'Npc_Hylia_044_Buy'  # the game's flag: reset on leaving the map
CARPET_AGAIN = 'EventFlowMsg/Npc_Hylia_044_Adult:Talk_01'  # "¡Tú aquí otra vez!"
GRANT_FLOW = 'Dm_SY_GetInEvent'
TRUE, FALSE = 0, 1  # case values of a bool query


class MerchantPatchError(ValueError):
    pass


def _one(flow: EventFlow, what: str, match: Callable[[int], bool]) -> int:
    hits = [i for i in range(len(flow.events)) if match(i)]
    if len(hits) != 1:
        raise MerchantPatchError(f'{len(hits)} events match {what}.')
    return hits[0]


def _query(flow: EventFlow, query: str, key: str, value: str) -> int:
    return _one(flow, f'{query} {value}', lambda i: flow.events[i].kind == SWITCH
                and flow.events[i].query == query and flow.action_params(i).get(key) == value)


def _case_slot(flow: EventFlow, i: int, value: int) -> tuple[int, int]:
    """(slot offset, target) of the case of event `i` for `value`."""
    cases_p = flow._u64(flow._events_p + 0x30 * i + 0x18)
    for k, target in enumerate(flow.events[i].cases):
        if flow._u32(cases_p + 8 * k) == value:
            return flow.link_slots[('case', i, k)], target
    raise MerchantPatchError(f'Event {i} has no case {value}.')


def _medigoron(data: bytes) -> bytes:
    f = EventFlow(data)
    talk = f.entry_points['Talk']
    if f.events[talk].kind != SUBFLOW:
        raise MerchantPatchError(f'{MEDIGORON}: Talk does not start with a call.')
    sold = _query(f, 'EventQueryIsGameDataBool', 'GameDataName', MEDIGORON_SOLD)
    knife = _query(f, 'EventQueryIsExistInPouch', 'Actor', 'Weapon_Sword_Giant')
    broken = _query(f, 'EventQueryIsExistInPouch', 'Actor', 'Weapon_Sword_BrokenGiant')
    _, chatter = _case_slot(f, knife, TRUE)  # what he says once you have his knife
    _, sale = _case_slot(f, broken, FALSE)  # his sale, with nothing in the pouch
    links = {f.link_slots[('next', talk)]: sold,
             _case_slot(f, sold, TRUE)[0]: chatter,
             _case_slot(f, sold, FALSE)[0]: sale}
    return patch_pointers(data, links)


def _shop(data: bytes) -> bytes:
    f = EventFlow(data)
    grant = _one(f, f'{SHOP} grant', lambda i: f.events[i].kind == SUBFLOW
                 and f.events[i].sub_flow == GRANT_FLOW)
    buy = _one(f, CARPET_BUY, lambda i: f.events[i].kind == ACTION
               and f.action_params(i).get('GameDataName') == CARPET_BUY)
    after = f.events[grant].next
    data = set_string_param(data, buy, 'GameDataName', CARPET_SOLD)
    data, (setter,) = append_events(data, [ActionSpec(
        'GameDataActor', 'EventTriggerSetGameDataBool',
        {'GameDataName': MEDIGORON_SOLD, 'Index': -1, 'Value': True})])
    f = EventFlow(data)
    return patch_pointers(data, {f.link_slots[('next', grant)]: setter,
                                 f.link_slots[('next', setter)]: after})


def _carpet(data: bytes) -> bytes:
    f = EventFlow(data)
    price = _one(f, 'SimpleShop_Price', lambda i: f.events[i].kind == ACTION
                 and f.action_params(i).get('GameDataName') == 'SimpleShop_Price')
    query = _query(f, 'EventQueryIsGameDataBool', 'GameDataName', CARPET_BUY)
    rupees = _one(f, 'the rupee display', lambda i: f.events[i].kind == ACTION
                  and f.events[i].action == 'EventTriggerOpenRupeeDisplay')
    if f.events[rupees].next != query:
        raise MerchantPatchError(f'{CARPET}: the rupee display does not lead to his query.')
    again_slot, again = _case_slot(f, query, TRUE)
    pitch_slot, pitch = _case_slot(f, query, FALSE)
    greeting = f.events[price].next
    links = {f.link_slots[('next', price)]: query,  # ask before the greeting
             pitch_slot: greeting,
             f.link_slots[('next', rupees)]: pitch,
             f.link_slots[('next', again)]: END}  # sold out: one line, then the end
    data = patch_pointers(data, links)
    data = set_string_param(data, query, 'GameDataName', CARPET_SOLD)
    return set_string_param(data, again, 'MessageId', CARPET_AGAIN)


def sold_out_patches(read: Callable[[str], bytes]) -> dict[str, bytes]:
    """{flow: patched bytes} for the merchants' three flows; `read(flow)` gives the
    current version (one the gift patch may already have written). Raises
    MerchantPatchError when a flow does not have the expected shape."""
    return {MEDIGORON: _medigoron(read(MEDIGORON)), SHOP: _shop(read(SHOP)),
            CARPET: _carpet(read(CARPET))}
