"""Remake (Hash) -> OoTR location mappings: chests and Gold Skulltulas."""
import json
from dataclasses import dataclass
from pathlib import Path

MAP_PATH = Path(__file__).resolve().parent / 'data' / 'location_map.json'
GS_MAP_PATH = Path(__file__).resolve().parent / 'data' / 'gs_map.json'


@dataclass(frozen=True)
class LocationEntry:
    hash: int
    location: str | None
    status: str
    needs_event_patch: bool
    # True: the chest loses its GetEventName (an event that only hands over the item).
    strip_event: bool = False


def load_map(path=MAP_PATH) -> dict[int, LocationEntry]:
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)
    return {int(h): LocationEntry(int(h), e['location'], e['status'],
                                  bool(e['needs_event_patch']),
                                  bool(e.get('strip_event', False)))
            for h, e in raw.items()}


@dataclass(frozen=True)
class GsEntry:
    hash: int
    location: str
    dungeon: bool
    # 'confirmed': checked in game, determined by the data, or with
    # requirements identical to the other candidate. 'guessed': still to be checked.
    status: str
    note: str
    # True: the remake's behaviour contradicts OoTR's logic; it does not
    # receive key items.
    no_key: bool = False


def load_gs_map(path=GS_MAP_PATH) -> dict[int, GsEntry]:
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)
    return {int(h): GsEntry(int(h), e['location'], bool(e['dungeon']),
                            e['status'], e['note'],
                            bool(e.get('no_key', False)))
            for h, e in raw.items()}
