"""High level editing API for profile.sav (characters, inventory, archetypes)."""
import re

from .nav import walk, _walk_bag
from .core import (SaveFile, SaveData, UObject, PropertyBag, Property, FName, ObjectRef,
                   ByteProp, SaveFormatError)

SCRIPT = "/Script/GunfireRuntime."

# Known currencies / materials (path -> display name). Shown in the "Materials" view
# even when the character does not own them yet.
CURRENCIES = [
    ("Scrap", "/Game/World_Base/Items/Materials/Scraps/Material_Scraps.Material_Scraps_C"),
    ("Lumenite Crystal", "/Game/World_Base/Items/Materials/LumeniteCrystal/Material_LumeniteCrystal.Material_LumeniteCrystal_C"),
    ("Corrupted Lumenite Crystal", "/Game/World_Base/Items/Materials/LumeniteCrystal/Material_LumeniteCorrupted.Material_LumeniteCorrupted_C"),
    ("Corrupted Shard (max 10)", "/Game/World_Base/Items/Materials/LumeniteCrystal/Material_CorruptedShard.Material_CorruptedShard_C"),
    ("Relic Dust", "/Game/World_Base/Items/Materials/GemFragments/Material_RelicDust.Material_RelicDust_C"),
    ("Simulacrum", "/Game/World_Base/Items/Materials/Simulacrum/Material_Simulacrum.Material_Simulacrum_C"),
    ("Iron", "/Game/World_Base/Items/Materials/Irons/01_Iron/Material_Iron.Material_Iron_C"),
    ("Forged Iron", "/Game/World_Base/Items/Materials/Irons/02_ForgedIron/Material_ForgedIron.Material_ForgedIron_C"),
    ("Galvanized Iron", "/Game/World_Base/Items/Materials/Irons/03_GalvanizedIron/Material_GalvanizedIron.Material_GalvanizedIron_C"),
    ("Hardened Iron", "/Game/World_Base/Items/Materials/Irons/04_HardenedIron/Material_HardenedIron.Material_HardenedIron_C"),
    ("Blood Moon Essence", "/Game/World_Jungle/Items/Materials/World/BloodMoonEssence/Material_BloodMoonEssence.Material_BloodMoonEssence_C"),
    ("Alien Alloy (DLC3)", "/Game/World_DLC3/Items/Special/AlienAlloy/Material_AlienAlloy.Material_AlienAlloy_C"),
    ("Mythril Alloy (DLC3)", "/Game/World_DLC3/Items/Special/MythrilAlloy/Material_MythrilAlloy.Material_MythrilAlloy_C"),
    ("Ancient Alloy (DLC3)", "/Game/World_DLC3/Items/Special/AncientAlloy/Material_AncientAlloy.Material_AncientAlloy_C"),
]
CURRENCY_NAMES = {p: n for n, p in CURRENCIES}

# XP at which an archetype is level 10 (observed in real saves; the game caps here).
ARCHETYPE_MAX_XP = 117125

_PREFIXES = ("Material_", "Consumable_", "Ring_", "Amulet_", "Weapon_", "Armor_", "Relic_",
             "RelicFragment_", "Mod_", "Gem_", "Trait_", "Archetype_", "Engram_", "Quest_Item_",
             "Quest_Hidden_Item_", "Item_HiddenContainer_", "Item_", "MetaGem_", "Talisman_", "Perk_", "SkillTrait_", "Skill_", "Head_", "Body_", "Legs_", "Gloves_")


def pretty_name(path, use_db=True):
    if not path:
        return "?"
    if use_db:
        from .itemdb import db
        name = db().name_for_path(path)
        if name:
            return name
    if path in CURRENCY_NAMES:
        return CURRENCY_NAMES[path]
    leaf =path.rsplit("/", 1)[-1].split(".", 1)[0]
    stripped = True
    while stripped:
        stripped = False
        for p in _PREFIXES:
            if leaf.startswith(p) and len(leaf) > len(p):
                leaf = leaf[len(p):]
                stripped = True
                break
    leaf = leaf.replace("_", " ")
    leaf = re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[A-Z])(?=[A-Z][a-z])", " ", leaf)
    return re.sub(r"\s+", " ", leaf).strip()


def category(path):
    if not path:
        return "?"
    if "/Items/" in path:
        c = path.split("/Items/", 1)[1].split("/", 1)[0]
    else:
        c = "Other"
    if c == "Trinkets":
        c = "Amulets" if "/Amulets/" in path else "Rings" if "/Rings/" in path else c
    if c == "Weapons":
        if "/Melee/" in path:
            c = "Melee"
    return c


class Item:
    """One inventory entry."""

    def __init__(self, char, entry):
        self.char = char
        self.entry = entry  # PropertyBag of the InventoryItem struct

    @property
    def id(self):
        return self.entry["ID"].value

    @property
    def path(self):
        return self.entry["ItemBP"].value.path

    @property
    def name(self):
        return pretty_name(self.path)

    @property
    def category(self):
        return category(self.path)

    @property
    def instance(self):
        ref = self.entry.get("InstanceData")
        return ref.value.obj if ref is not None else None

    @property
    def instance_type(self):
        o = self.instance
        return o.path.replace(SCRIPT, "") if o is not None else None

    def _iprop(self, key):
        o = self.instance
        if o is None or o.props is None:
            return None
        return o.props.get(key)

    @property
    def quantity(self):
        p = self._iprop("Quantity")
        if p is not None:
            return p.value
        return 1 if self.instance_type in ("ItemInstanceData",) or self.has_quantity_field else None

    @property
    def has_quantity_field(self):
        return self._iprop("Quantity") is not None

    @property
    def stackable(self):
        """True for items whose count is meaningful (materials, consumables)."""
        if self.has_quantity_field:
            return True
        c = self.category
        return self.instance_type == "ItemInstanceData" and c in ("Materials", "CraftingMaterial", "Consumables")

    @property
    def level(self):
        p = self._iprop("Level")
        if p is None:
            return 0 if self.levelable else None
        v = p.value
        return v.value if isinstance(v, ByteProp) else v

    @property
    def levelable(self):
        t = self.instance_type
        return t in ("RangedWeaponInstanceData", "EquipmentModInstanceData") or (
            t == "EquipmentInstanceData" and self.category in ("Weapons", "Melee", "Relics", "RelicFragments"))

    def set_quantity(self, qty):
        qty = int(qty)
        if not (0 < qty <= 2147483647):
            raise ValueError("quantity must be 1..2147483647")
        o = self.instance
        if o is None:
            raise SaveFormatError("item has no instance data")
        p = self._iprop("Quantity")
        if p is not None:
            p.value = qty
            return
        if o.props is None:
            o.props = PropertyBag(terminator=self.char.sd.fname("None"))
            if not o.extra:
                o.extra = b"\0\0\0\0"
        o.props.props.append(self.char.make_int("Quantity", qty))

    def set_level(self, level):
        level = int(level)
        if not (0 <= level <= 255):
            raise ValueError("level must be 0..255")
        o = self.instance
        p = self._iprop("Level")
        if p is not None:
            if isinstance(p.value, ByteProp):
                p.value.value = level
            else:
                p.value = level
            return
        if level == 0:
            return
        if o.props is None:
            o.props = PropertyBag(terminator=self.char.sd.fname("None"))
            if not o.extra:
                o.extra = b"\0\0\0\0"
        o.props.props.append(self.char.make_byte("Level", level))

    def __repr__(self):
        return "Item(%d %s q=%s l=%s)" % (self.id, self.name, self.quantity, self.level)


class Archetype:
    def __init__(self, char, entry):
        self.char = char
        self.entry = entry

    @property
    def path(self):
        return self.entry["TraitBP"].value.path

    @property
    def name(self):
        return pretty_name(self.path)

    @property
    def level(self):
        return self.entry["Level"].value

    @property
    def xp(self):
        p = self.entry.get("InstanceData")
        return p.value if p is not None else 0

    @property
    def slot(self):
        return self.entry["SlotIndex"].value

    def set_xp(self, xp):
        xp = int(xp)
        if not (0 <= xp <= ARCHETYPE_MAX_XP):
            raise ValueError("XP must be 0..%d" % ARCHETYPE_MAX_XP)
        p = self.entry.get("InstanceData")
        if p is None:
            raise SaveFormatError("archetype entry has no XP field")
        p.value = xp


class Trait:
    def __init__(self, char, entry):
        self.char = char
        self.entry = entry

    @property
    def path(self):
        return self.entry["TraitBP"].value.path

    @property
    def name(self):
        return pretty_name(self.path)

    @property
    def level(self):
        return self.entry["Level"].value

    @property
    def kind(self):
        p = self.path
        if "/Archetypes/" in p:
            return "archetype"
        if "/Traits/Core/" in p:
            return "core"
        leaf = p.rsplit("/", 1)[-1]
        if leaf.startswith(("Perk_", "SkillTrait_")):
            return "perk"
        return "trait"

    def set_level(self, lvl):
        lvl = int(lvl)
        if not (0 <= lvl <= 10):
            raise ValueError("trait level must be 0..10")
        self.entry["Level"].value = lvl


class Character:
    def __init__(self, profile, slot, obj):
        self.profile = profile
        self.slot = slot
        self.obj = obj  # SavedCharacter UObject
        blob = obj.props["CharacterData"].value
        self.sd = blob.value  # nested SaveData
        if not isinstance(self.sd, SaveData):
            raise SaveFormatError("unexpected character data")
        self.master = self.sd.objects[0]
        self.components = {c.key: c for c in (self.master.components or [])}

    # -- summary --
    def _p(self, key, default=None):
        p = self.obj.props.get(key)
        return p.value if p is not None else default

    @property
    def archetype(self):
        return pretty_name(self._p("Archetype") or "").replace(" UI", "")

    @property
    def secondary(self):
        return pretty_name(self._p("SecondaryArchetype") or "").replace(" UI", "")

    @property
    def power_level(self):
        return self._p("PowerLevel")

    @property
    def item_level(self):
        return self._p("ItemLevel")

    @property
    def trait_rank(self):
        return self._p("TraitRank")

    def _comp_prop(self, comp, key):
        c = self.components.get(comp)
        if c is None or c.props is None:
            return None
        return c.props.get(key)

    @property
    def experience(self):
        p = self._comp_prop("Progression", "Experience")
        return p.value if p is not None else None

    @property
    def trait_points(self):
        p = self._comp_prop("Traits", "TraitPoints")
        return p.value if p is not None else None

    # -- property builders (names go into this character's names table) --
    def make_int(self, name, value):
        sd = self.sd
        return Property(sd.fname(name), sd.fname("IntProperty"), int(value), size=4, index=0, pg=b"\0")

    def make_bool(self, name, value):
        sd = self.sd
        return Property(sd.fname(name), sd.fname("BoolProperty"), 1 if value else 0, size=0, index=0, pg=b"\0")

    def make_ref(self, name, index):
        sd = self.sd
        return Property(sd.fname(name), sd.fname("ObjectProperty"), ObjectRef(index, sd.objects),
                        size=4, index=0, pg=b"\0")

    def make_byte(self, name, value):
        sd = self.sd
        bp = ByteProp()
        bp.enum_name = sd.fname("None")
        bp.pg = b"\0"
        bp.value = int(value)
        return Property(sd.fname(name), sd.fname("ByteProperty"), bp, size=1, index=0, pg=None)

    # -- inventory --
    @property
    def _inv(self):
        c = self.components.get("Inventory")
        if c is None:
            raise SaveFormatError("character has no inventory")
        return c.props

    def items(self):
        return [Item(self, e) for e in self._inv["Items"].value.items]

    def find_item(self, path):
        for it in self.items():
            if it.path == path:
                return it
        return None

    def _next_object_number(self):
        nums = [o.name.number for o in self.sd.objects
                if not o.was_loaded and o.name is not None and o.name.number is not None]
        return (min(nums) - 1) if nums else None

    def add_item(self, path, quantity=None, instance_type="ItemInstanceData"):
        """Add a brand-new inventory entry. For materials use ItemInstanceData + quantity,
        for rings/amulets EquipmentInstanceData without quantity."""
        if self.find_item(path) is not None:
            raise ValueError("item already in inventory")
        if not path.startswith("/Game/") or "." not in path:
            raise ValueError("item path must look like /Game/.../Name.Name_C")
        sd = self.sd
        # ItemBP reference object (reuse if the path is already referenced)
        bp_index = next((o.object_index for o in sd.objects if o.was_loaded and o.path == path), None)
        if bp_index is None:
            o = UObject()
            o.was_loaded = 1
            o.path = path
            bp_index = sd.add_object(o)
        # InstanceData object
        inst = UObject()
        inst.was_loaded = 0
        inst.path = SCRIPT + instance_type
        inst.name = sd.fname(instance_type, self._next_object_number())
        inst.outer_id = 0
        inst.props = PropertyBag(terminator=sd.fname("None"))
        if quantity is not None:
            inst.props.props.append(self.make_int("Quantity", quantity))
        inst.extra = b"\0\0\0\0"
        inst.is_actor = 0
        inst_index = sd.add_object(inst)
        # inventory entry
        inv = self._inv
        items = inv["Items"].value
        idgen = inv.get("IDGen")
        max_id = max([e["ID"].value for e in items.items] or [0])
        new_id = max(max_id, idgen.value if idgen is not None else max_id) + 1
        if idgen is not None:
            idgen.value = new_id
        entry = PropertyBag([
            self.make_int("ID", new_id),
            self.make_ref("ItemBP", bp_index),
            self.make_bool("New", True),
            self.make_bool("Favorited", False),
            self.make_bool("Hidden", False),
            self.make_int("EquipmentSlotIndex", -1),
            self.make_ref("InstanceData", inst_index),
        ], terminator=sd.fname("None"))
        items.items.append(entry)
        return Item(self, entry)

    # Item kinds the editor lets you delete: plain equipment and stackables. Weapons, mods, relics,
    # fragments, archetype items, currencies and quest items carry links the game expects, so they stay.
    DELETABLE_TYPES = ("ring", "amulet", "armor", "mutator", "consumable", "concoction", "material")

    def delete_blockers(self, item):
        """Reasons the item must not be deleted, as (code, detail) pairs; empty list = safe to delete.
        Codes: type, equipped, attached, mods, radial."""
        from .itemdb import db
        out = []
        e = db().by_path.get(item.path.lower())
        kind = e.get("Type") if e else None
        if kind not in self.DELETABLE_TYPES or "/archetypes/" in item.path.lower():
            out.append(("type", kind or "?"))
        slot = item.entry.get("EquipmentSlotIndex")
        if slot is not None and slot.value != -1:
            out.append(("equipped", slot.value))
        att = item._iprop("EquippedModItemID")
        if att is not None and att.value != -1:
            host = next((it for it in self.items() if it.id == att.value), None)
            out.append(("attached", host.name if host else "#%d" % att.value))
        for other in self.items():
            o = other.instance
            if other.entry is item.entry or o is None or o.props is None or o.props.get("Mods") is None:
                continue
            if any(p.name.name == "ModItemID" and p.value == item.id for _, p, _b, _s in walk(o, sd=self.sd)):
                out.append(("attached", other.name))
        if item._iprop("Mods") is not None and any(
                p.name.name == "ModItemID" and p.value != -1 for _, p, _b, _s in walk(item.instance, sd=self.sd)):
            out.append(("mods", ""))
        rs = self.components.get("RadialShortcuts")
        if rs is not None and rs.props is not None:
            for _, p, _b, _s in _walk_bag(rs.props, "", self.sd):
                if p.name.name == "ItemBP" and getattr(p.value, "path", None) == item.path:
                    out.append(("radial", ""))
                    break
        # de-duplicate (a mod can be reported from both sides of the link)
        seen, res = set(), []
        for r in out:
            if r not in seen:
                seen.add(r)
                res.append(r)
        return res

    def remove_item(self, item, force=False):
        """Remove one inventory entry. Raises ValueError when delete_blockers() objects (unless force).
        The entry's InstanceData object stays in the object table unreferenced: removing it would
        renumber every object reference in the save, and the game drops unreferenced objects on its
        next save anyway."""
        if not force:
            why = self.delete_blockers(item)
            if why:
                raise ValueError("cannot delete %s: %s" % (item.name, ", ".join(c for c, _ in why)))
        items = self._inv["Items"].value.items
        for i, e in enumerate(items):
            if e is item.entry:
                del items[i]
                return
        raise ValueError("item is not in this inventory")

    def set_currency(self, path, qty):
        it = self.find_item(path)
        if it is None:
            return self.add_item(path, int(qty), "ItemInstanceData")
        it.set_quantity(qty)
        return it

    # -- traits / archetypes --
    def _trait_entries(self):
        p = self._comp_prop("Traits", "Traits")
        return p.value.items if p is not None else []

    def archetypes(self):
        return [Archetype(self, e) for e in self._trait_entries()
                if "/Archetypes/" in (e["TraitBP"].value.path or "")
                and e["TraitBP"].value.path.rsplit("/", 1)[-1].startswith("Archetype_")]

    def traits(self):
        return [Trait(self, e) for e in self._trait_entries()]

    SPENDABLE_KINDS = ("core", "trait")

    def trait_budget(self):
        """(spent, available) trait points. Spent = levels of core + regular traits (archetype traits and
        perks are free); available = TraitPoints (falls back to TraitRank)."""
        spent = sum(t.level for t in self.traits() if t.kind in self.SPENDABLE_KINDS)
        avail = self.trait_points if self.trait_points is not None else self.trait_rank
        return spent, avail

    def __repr__(self):
        return "Character(%d %s/%s PL%s)" % (self.slot, self.archetype, self.secondary, self.power_level)


class Profile:
    def __init__(self, savefile):
        if not savefile.is_profile:
            raise SaveFormatError("not a profile.sav")
        self.sf = savefile

    @classmethod
    def load(cls, path):
        return cls(SaveFile.load(path))

    @property
    def root(self):
        return self.sf.data.objects[0]

    def characters(self):
        out = []
        chars = self.root.props["Characters"].value.items
        for slot, ref in enumerate(chars):
            if ref.index != -1 and ref.obj is not None:
                out.append(Character(self, slot, ref.obj))
        return out

    @property
    def active_slot(self):
        p = self.root.props.get("ActiveCharacterIndex")
        return p.value if p is not None else 0

    def active_character(self):
        chars = self.characters()
        for c in chars:
            if c.slot == self.active_slot:
                return c
        return chars[0] if chars else None
