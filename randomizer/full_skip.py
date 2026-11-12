"""Full cutscene skip: target list (randomizer/data/full_skip.json) and mod files."""
from collections.abc import Mapping
from pathlib import Path

TARGETS_PATH = Path(__file__).resolve().parent / 'data' / 'full_skip.json'


def external_entries(callers: Mapping[tuple[str, str], set[str]], flow: str,
                     entry: str) -> frozenset[str]:
    """Entries of `flow` that other files call (see `entry_callers`), except `entry`."""
    return frozenset(e for f, e in callers if f == flow and e != entry)
