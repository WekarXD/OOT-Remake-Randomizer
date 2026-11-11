"""Asociaciones del remake (Hash) -> ubicación de OoTR: cofres y Skulltulas doradas."""
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
    # True: el cofre pierde su GetEventName (evento que solo entrega el objeto).
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
    # 'confirmed': comprobada en el juego, determinada por los datos o con
    # requisitos idénticos a la otra candidata. 'guessed': falta comprobarla.
    status: str
    note: str


def load_gs_map(path=GS_MAP_PATH) -> dict[int, GsEntry]:
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)
    return {int(h): GsEntry(int(h), e['location'], bool(e['dungeon']),
                            e['status'], e['note'])
            for h, e in raw.items()}
