"""Terminology and proper names: langs/<lang>/terms.csv.

Every name and game term (characters, Medabots, parts, actions, places, Robattle...) is written ONCE, in the
language's terms file, and texts refer to it with a key:

  {{robattle}}        the term as written in terms.csv          ("Robattle")
  {{robattle|pl}}     its plural (column `plural`)               ("Robattles")
  {{robattle|cap}}    first letter in capitals                   ("Robattle" -> "Robattle", "medal" -> "Medal")
  {{robattle|up}}     all capitals                               ("ROBATTLE")

Change a term in terms.csv and the build writes it everywhere in the game.
"""
import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KEY = re.compile(r'\{\{([A-Za-z0-9_.-]+)((?:\|[a-z]+)*)\}\}')


def load(lang: str) -> dict:
    p = REPO / 'langs' / lang / 'terms.csv'
    if not p.exists():
        return {}
    with open(p, encoding='utf-8', newline='') as f:
        return {r['id']: r for r in csv.DictReader(f)}


def expand(text: str, table: dict, errors: list = None) -> str:
    def sub(m):
        t = table.get(m.group(1))
        if t is None:
            if errors is not None:
                errors.append(m.group(0))
            return m.group(0)
        mods = m.group(2).split('|')[1:]
        s = (t.get('plural') or t['text']) if 'pl' in mods else t['text']
        if 'cap' in mods:
            s = s[:1].upper() + s[1:]
        if 'up' in mods:
            s = s.upper()
        return s
    return KEY.sub(sub, text) if '{{' in text else text


def expander(lang: str):
    table = load(lang)
    return lambda text: expand(text, table)
