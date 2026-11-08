"""Asociación cofre del remake (Hash) -> ubicación de OoTR."""
import json
from dataclasses import dataclass
from pathlib import Path

MAP_PATH = Path(__file__).resolve().parent / 'data' / 'location_map.json'


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
