"""Configuración del usuario (user_config.json en la raíz del proyecto)."""
import json
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / 'user_config.json'


def load(path: Path) -> dict:
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def save(path: Path, d: dict) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)
