"""Game database: items, events (bosses, dungeons, ...) and where items drop.

data/db.json comes from lib.remnant2.analyzer by AndrewSav (MIT, see data/LICENSE-lib.remnant2.analyzer):
https://github.com/AndrewSav/lib.remnant2.analyzer
data/names.json (EN/RU names of items, bosses, locations) comes from RemnantOverseer by Angelore
(MIT, see data/LICENSE-RemnantOverseer): https://github.com/Angelore/remnant-two-overseer
"""
import json
import os
import re
from collections import defaultdict

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_DB_PATH = os.path.join(_DATA, "db.json")
_NAMES_PATH = os.path.join(_DATA, "names.json")
_db = None
_names = None


def names():
    global _names
    if _names is None:
        try:
            with open(_NAMES_PATH, "r", encoding="utf-8") as f:
                _names = json.load(f)
        except Exception:
            _names = {}
    return _names


def localized(key, fallback=None):
    """Name for a db Id / quest Id / location label in the current UI language."""
    if not key:
        return fallback
    from .i18n import get_lang
    n = names()
    if get_lang() == "ru":
        v = n.get("ru", {}).get(key)
        if v:
            return v
    v = n.get("en", {}).get(key)
    return v or fallback

# db type -> (instance data class, has quantity). Derived from how the game stores these
# item kinds in real inventories. Everything else (weapons, mods, fragments, skills,
# archetypes, prisms...) needs extra data and is not offered for adding.
ADD_RULES = {
    "ring": ("EquipmentInstanceData", False),
    "amulet": ("EquipmentInstanceData", False),
    "armor": ("EquipmentInstanceData", False),
    "relic": ("EquipmentInstanceData", False),
    "engram": ("EquipmentInstanceData", False),
    "consumable": ("EquipmentInstanceData", True),
    "concoction": ("EquipmentInstanceData", True),
    "currency": ("ItemInstanceData", True),
    "material": ("ItemInstanceData", True),
    "mutator": ("EquipmentModInstanceData", False),
}

LOOT_TYPES = {"ring", "amulet", "armor", "relic", "engram", "consumable", "concoction", "material",
              "mutator", "weapon", "mod", "fragment", "armorspecial", "specialmod", "prism", "dream"}

WORLD_NAMES = {
    "World_Base": "Ward 13 / Base", "World_Jungle": "Yaesha", "World_Fae": "Losomn", "World_Nerud": "N'Erud",
    "World_Root": "Root Earth", "World_Labyrinth": "Labyrinth", "World_City": "City",
    "World_DLC1": "DLC1 · Awakened King", "World_DLC2": "DLC2 · Forgotten Kingdom",
    "World_DLC3": "DLC3 · Dark Horizon",
}


class DB:
    def __init__(self, entries):
        self.entries = entries
        self.by_id = {}
        self.by_path = {}
        self.drops = defaultdict(list)      # DropReference -> [item entries]
        for e in entries:
            self.by_id.setdefault(e["Id"], e)
            p = e.get("ProfileId")
            if p:
                self.by_path.setdefault(p.lower(), e)
            ref = e.get("DropReference")
            if ref and p and e.get("Type") in LOOT_TYPES:
                self.drops[ref].append(e)

    def item_name(self, e):
        n = localized(e["Id"], e.get("Name"))
        if n:
            return n
        from .profile import pretty_name
        return pretty_name(e.get("ProfileId") or e["Id"], use_db=False)

    def english_name(self, e):
        return names().get("en", {}).get(e["Id"]) or e.get("Name") or e["Id"]

    def name_for_path(self, path):
        e = self.by_path.get((path or "").lower())
        return localized(e["Id"], e.get("Name")) if e else None

    def by_id_ci(self, item_id):
        e = self.by_id.get(item_id)
        if e is None:
            if not hasattr(self, "_ci"):
                self._ci = {k.lower(): v for k, v in self.by_id.items()}
            e = self._ci.get(item_id.lower())
        return e

    def event(self, quest_name):
        e = self.by_id.get(quest_name)
        return e if e is not None and e.get("Type") in ("event", "quest") else None

    def catalog(self):
        """Every item that can be added from the editor, sorted by type and name."""
        out = [e for e in self.entries if e.get("ProfileId") and e.get("Type") in ADD_RULES]
        out.sort(key=lambda e: (e["Type"], self.item_name(e).lower()))
        return out


def db():
    global _db
    if _db is None:
        try:
            with open(_DB_PATH, "r", encoding="utf-8") as f:
                _db = DB(json.load(f))
        except Exception:
            _db = DB([])
    return _db


def world_label(world_key):
    return WORLD_NAMES.get(world_key or "", world_key or "—")


def split_camel(s):
    s = re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[0-9])(?=[A-Za-z])", " ", s)
    return re.sub(r"\s+", " ", s.replace("_", " ")).strip()
