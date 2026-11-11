"""Full cutscene skip: action table loader (effects-only event flow rewriting)."""
import json
from fnmatch import fnmatchcase
from pathlib import Path

TABLE_PATH = Path(__file__).resolve().parent / 'data' / 'skip_actions.json'


class SkipTable:
    def __init__(self, data):
        self.actions = data.get('actions', {})
        self.actor_actions = data.get('actor_actions', {})
        self.queries = data.get('queries', {})
        self.subflows_drop = list(data.get('subflows_drop', []))

    @classmethod
    def load(cls, path=TABLE_PATH):
        with open(path, encoding='utf-8') as f:
            return cls(json.load(f))

    def keeps(self, actor, action):
        """True if the action must stay. Unknown and 'review' actions are kept."""
        cls = self.actor_actions.get(f'{actor}.{action}') if actor else None
        if cls is None:
            cls = self.actions.get(action)
        return cls != 'drop'

    def collapses(self, query):
        return self.queries.get(query) == 'collapse'

    def drops_subflow(self, flow, entry):
        name = f'{flow}/{entry}'
        return any(fnmatchcase(name, p) for p in self.subflows_drop)
