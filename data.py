import json, os
from nicegui import ui

DB_PATH   = 'data/database.json'
MEDIA_DIR = 'media'

def load_data() -> list:
    os.makedirs('data', exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, 'r', encoding='utf-8') as f:
                d = json.load(f)
                return d if isinstance(d, list) else []
        except Exception:
            return []
    return []

def save_data():
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(family_data, f, indent=4, ensure_ascii=False)

# family_data — единственный объект-список, который НИКОГДА не переприсваивается.
# Все операции только мутируют его (append, remove, extend, clear).
family_data: list[dict] = []
family_data.extend(load_data())  # наполняем данными при старте
state = {'selected': None}
view_state = {'mode': 'profile'}
form  = {}

def imap():
    return {p['id']: p for p in family_data}

def initials(name: str) -> str:
    parts = name.strip().split()
    return (''.join(p[0] for p in parts[:2])).upper() or '?'

def get_relations(person):
    m = imap()
    parents  = [m[pid] for pid in person.get('parents', []) if pid in m]
    children = [p for p in family_data if person['id'] in p.get('parents', [])]
    sib_ids  = set()
    for par in parents:
        for p in family_data:
            if par['id'] in p.get('parents', []) and p['id'] != person['id']:
                sib_ids.add(p['id'])
    siblings = [m[s] for s in sib_ids if s in m]
    return parents, children, siblings

