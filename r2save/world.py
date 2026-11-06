"""World save (save_N.sav): worlds (campaign / adventure), zones and respawn points.

Teleport = change where the game spawns you on the next load: the active world's
RespawnZoneID / RespawnLinkNameID (+ LastCheckpoint*, where you return after death).
"""
import datetime

from .core import (SaveFile, FName, SaveFormatError, TextProp, StructProp, UObject, PropertyBag, Property,
                   ObjectRef)

_TICKS_PER_SEC = 10_000_000
_EPOCH = datetime.datetime(1, 1, 1)

WORLD_CLASS = "/Game/_Core/Blueprints/Base/BP_RemnantSaveGame"
MAIN_KEY = "/Game/Maps/Main.Main:PersistentLevel"
WARD13_KEY = "/Game/Quest_2_Container.Quest_Container:PersistentLevel"

ADVENTURE_NAMES = {
    "Jungle": "Yaesha", "Fae": "Losomn", "Nerud": "N'Erud",
    "DLC1": "Losomn (The Awakened King)", "DLC2": "Yaesha (The Forgotten Kingdom)",
    "DLC3": "N'Erud (The Dark Horizon)",
}
SAFE_TYPES = ("Waypoint", "Checkpoint")


def _text(v):
    return v.text if isinstance(v, TextProp) else v


class Link:
    def __init__(self, zone, bag):
        self.zone = zone
        self.bag = bag

    def _v(self, k, d=None):
        p = self.bag.get(k)
        return p.value if p is not None else d

    @property
    def name_id(self):
        return self._v("NameID").name

    @property
    def label(self):
        """In-game name stored with the link: world stones carry their own ('Mournful Promenade'),
        checkpoints and transitions just repeat the zone name."""
        v = _text(self._v("Label"))
        return v.strip() if isinstance(v, str) and v.strip() else None

    @property
    def stone_name(self):
        """Travel-menu name of a world stone, None for other link types."""
        return self.label if self.type == "Waypoint" else None

    def discover(self):
        """Activate a world stone so it shows up in the in-game travel menu (IsActive = 1, the flag the
        game sets when you touch the stone). Returns False if it already was active."""
        if self.type != "Waypoint":
            raise ValueError("only world stones can be opened")
        p = self.bag.get("IsActive")
        if p is None:
            raise ValueError("this world stone has no IsActive flag")
        if p.value:
            return False
        p.value = 1
        return True

    @property
    def undiscovered_stone(self):
        """A world stone the player has not activated yet. Mixed results in game: Mournful Promenade (zone
        already visited) gave a black screen on load, The Great Hall (zone not visited yet) worked."""
        return self.type == "Waypoint" and not self.discovered

    @property
    def type(self):
        v = self._v("Type")
        return v.value.name.split("::")[-1] if v is not None else "?"

    @property
    def active(self):
        return bool(self._v("IsActive", 0))

    @property
    def used(self):
        return bool(self._v("Used", 0))

    @property
    def can_respawn(self):
        return bool(self._v("CanBeRespawnLink", 0))

    @property
    def disabled(self):
        return bool(self._v("IsDisabled", 0))

    @property
    def discovered(self):
        return self.active or self.used

    @property
    def safe(self):
        return self.type in SAFE_TYPES

    def __repr__(self):
        return "Link(%s %s %s)" % (self.zone.label, self.type, self.name_id)


class Zone:
    def __init__(self, world, actor):
        self.world = world
        self.actor = actor
        self.props = actor.archive.objects[0].props

    def _v(self, k, d=None):
        p = self.props.get(k)
        return p.value if p is not None else d

    @property
    def id(self):
        return self._v("ID")

    @property
    def label(self):
        return _text(self._v("Label")) or self._v("NameID").name

    @property
    def level(self):
        return self._v("ZoneLevel", self._v("Level"))

    @property
    def visited(self):
        return "ZoneLevelInitialized" in self.props

    def links(self):
        zl = self.props.get("ZoneLinks")
        if zl is None:
            return []
        return [Link(self, b) for b in zl.value.items]

    def __repr__(self):
        return "Zone(%d %s)" % (self.id, self.label)


def ticks_to_dt(t):
    return _EPOCH + datetime.timedelta(microseconds=t // 10)


class BloodMoon:
    """Quest_Event_Bloodmoon_C of one world. The game rolls CurrentChance (%) on a zone load,
    at most about once per hour of real time (LastCheckTime); every miss adds +10%.
    force() only prepares the roll (100% and an old LastCheckTime) - the event itself,
    its duration and the reset afterwards stay the game's business."""

    def __init__(self, world, obj):
        self.world = world
        self.obj = obj
        comp = next((c for c in (obj.components or []) if c.key == "BloodMoon"), None)
        if comp is None or comp.props is None:
            raise SaveFormatError("blood moon component not found")
        self.props = comp.props

    def _dt(self, key):
        p = self.props.get(key)
        if p is None or not isinstance(p.value, StructProp):
            return None
        return p.value

    @property
    def chance(self):
        p = self.props.get("CurrentChance")
        return p.value if p is not None else None

    @property
    def last_check(self):
        v = self._dt("LastCheckTime")
        return ticks_to_dt(v.value) if v is not None else None

    @property
    def last_triggered(self):
        v = self._dt("LastTriggeredTime")
        return ticks_to_dt(v.value) if v is not None else None

    @property
    def stuck(self):
        """True when the event already fired but the chance stayed at 100% (our forced roll)."""
        lc, lt, ch = self.last_check, self.last_triggered, self.chance
        return ch is not None and ch >= 100 and lc is not None and lt is not None and lt >= lc

    def reset(self, chance=5.0):
        p = self.props.get("CurrentChance")
        if p is None:
            raise SaveFormatError("CurrentChance not found")
        p.value = float(chance)

    def force(self, hours_back=24):
        p = self.props.get("CurrentChance")
        if p is None:
            raise SaveFormatError("CurrentChance not found")
        p.value = 100.0
        v = self._dt("LastCheckTime")
        if v is not None:
            v.value = max(0, v.value - int(hours_back * 3600) * _TICKS_PER_SEC)


class QuestItem:
    """An entry of a world's own inventory (RemnantPlayerInventory of the root quest): quest items such as
    keys, Crimson King Coins, Feast Master's Leftovers. They live in save_N.sav, not in the character."""

    def __init__(self, world, entry):
        self.world = world
        self.entry = entry

    @property
    def id(self):
        return self.entry["ID"].value

    @property
    def path(self):
        return self.entry["ItemBP"].value.path

    @property
    def name(self):
        from .itemdb import db
        from .profile import pretty_name
        return db().name_for_path(self.path) or pretty_name(self.path)

    def __repr__(self):
        return "QuestItem(%d %s)" % (self.id, self.name)


# Quest items the editor may duplicate: stack-like counters whose copies are interchangeable.
# Keys and story items are left alone (duplicates could confuse quest scripts).
DUPLICABLE_QUEST_ITEMS = ("Quest_Item_CrimsonKingCoin",)


class World:
    """A root quest: the campaign or one adventure."""

    def __init__(self, save, quest_obj):
        self.save = save
        self.obj = quest_obj
        self.props = quest_obj.props

    def _v(self, k, d=None):
        p = self.props.get(k)
        return p.value if p is not None else d

    @property
    def class_name(self):
        return self.obj.path.rsplit(".", 1)[-1]

    @property
    def is_campaign(self):
        return "Campaign_Main" in self.class_name

    @property
    def name(self):
        if self.is_campaign:
            return "Campaign"
        key = self.class_name.replace("Quest_AdventureMode_", "").replace("_C", "")
        return "Adventure: %s" % ADVENTURE_NAMES.get(key, key)

    @property
    def quest_id(self):
        return self._v("ID")

    @property
    def slot(self):
        return self._v("SlotID")

    @property
    def active(self):
        return self.save.active_slot == self.slot

    @property
    def respawn(self):
        return self._v("RespawnZoneID"), self._v("RespawnLinkNameID").name

    @property
    def last_checkpoint(self):
        return self._v("LastCheckpointZoneID"), self._v("LastCheckpointNameID").name

    def zones(self):
        out = []
        pc = self.save.containers.get("/Game/Quest_%d_Container.Quest_Container:PersistentLevel" % self.quest_id)
        ward = self.save.containers.get(WARD13_KEY)
        for c in (ward, pc):
            if c is None:
                continue
            for _, a in c.actors:
                if a.dynamic and a.dynamic[2][1] == "ZoneActor":
                    out.append(Zone(self, a))
        return out

    def blood_moon(self):
        pc = self.save.containers.get("/Game/Quest_%d_Container.Quest_Container:PersistentLevel" % self.quest_id)
        if pc is None:
            return None
        for _, a in pc.actors:
            o = a.archive.objects[0]
            if o.path and o.path.endswith("Quest_Event_Bloodmoon_C"):
                try:
                    return BloodMoon(self, o)
                except SaveFormatError:
                    return None
        return None

    def quests(self):
        """{quest id: (class name without _C, state or None, zone id or None)} of this world's roll."""
        out = {}
        pc = self.save.containers.get("/Game/Quest_%d_Container.Quest_Container:PersistentLevel" % self.quest_id)
        if pc is None:
            return out
        for _, a in pc.actors:
            o = a.archive.objects[0]
            leaf = (o.path or "").rsplit(".", 1)[-1]
            if not leaf.startswith("Quest_") or o.props is None or "ID" not in o.props:
                continue
            st = o.props.get("QuestState")
            state = st.value.value.name.split("::")[-1] if st is not None else None
            z = o.props.get("ZoneID")
            out[o.props["ID"].value] = (leaf[:-2] if leaf.endswith("_C") else leaf, state, z.value if z else None)
        return out

    def find(self, zone_id, link_name):
        for z in self.zones():
            if z.id == zone_id:
                for l in z.links():
                    if l.name_id == link_name:
                        return z, l
                return z, None
        return None, None

    def describe(self, zone_id, link_name):
        z, l = self.find(zone_id, link_name)
        if z is None:
            return "zone %s / %s" % (zone_id, link_name)
        stone = l.stone_name if l is not None else None
        if stone and stone != z.label:
            return "%s · %s (%s)" % (z.label, stone, link_name)
        return "%s · %s" % (z.label, link_name)

    # -- quest inventory --
    def _quest_inventory(self):
        """(SaveData, PropertyBag) of this world's RemnantPlayerInventory, or (None, None)."""
        comp = next((c for c in self.obj.components or () if c.key == "RemnantPlayerInventory"), None)
        if comp is None or comp.props is None:
            return None, None
        from .nav import walk
        sd = next((s for _, _p, bag, s in walk(self.save.sf) if bag is comp.props), None)
        return sd, comp.props

    def quest_items(self):
        sd, inv = self._quest_inventory()
        if inv is None or inv.get("Items") is None:
            return []
        return [QuestItem(self, e) for e in inv["Items"].value.items]

    def duplicate_quest_item(self, item, copies=1):
        """Add `copies` more entries of the same quest item, each with its own ItemInstanceData object,
        exactly like the one the game wrote. Only DUPLICABLE_QUEST_ITEMS. Returns the new QuestItems."""
        if not any(k in item.path for k in DUPLICABLE_QUEST_ITEMS):
            raise ValueError("only %s can be duplicated" % ", ".join(DUPLICABLE_QUEST_ITEMS))
        sd, inv = self._quest_inventory()
        src_inst = item.entry["InstanceData"].value.obj
        if sd is None or src_inst is None:
            raise ValueError("quest inventory not found")
        items = inv["Items"].value
        idgen = inv.get("IDGen")
        out = []
        for _ in range(int(copies)):
            nums = [o.name.number for o in sd.objects
                    if not o.was_loaded and o.name is not None and o.name.number is not None]
            inst = UObject()
            inst.was_loaded = 0
            inst.path = src_inst.path
            inst.name = sd.fname(src_inst.name.name, (min(nums) - 1) if nums else None)
            inst.outer_id = src_inst.outer_id
            inst.props = PropertyBag(terminator=sd.fname("None"))
            inst.extra = src_inst.extra
            inst.is_actor = src_inst.is_actor
            inst_index = sd.add_object(inst)
            new_id = max([e["ID"].value for e in items.items] + [idgen.value if idgen is not None else 0]) + 1
            if idgen is not None:
                idgen.value = new_id
            props = []
            for p in item.entry.props:
                n = p.name.name
                if n == "ID":
                    v = new_id
                elif n == "InstanceData":
                    v = ObjectRef(inst_index, sd.objects)
                elif n == "New":
                    v = 0
                elif n == "ItemBP":
                    v = ObjectRef(p.value.index, sd.objects)
                else:
                    v = p.value
                props.append(Property(p.name, p.type, v, size=p.size, index=p.index, pg=p.pg))
            entry = PropertyBag(props, terminator=item.entry.terminator)
            items.items.append(entry)
            out.append(QuestItem(self, entry))
        return out

    def stones(self):
        """All world stones of this world (enabled ones)."""
        return [l for z in self.zones() for l in z.links() if l.type == "Waypoint" and not l.disabled]

    def discover_all_stones(self):
        """Open every world stone of this world. Returns the links that were changed."""
        return [l for l in self.stones() if l.discover()]

    def teleport(self, link, set_checkpoint=True, make_active=True):
        if not link.can_respawn:
            raise ValueError("this point can not be used as a spawn point")
        if link.disabled:
            raise ValueError("this point is disabled")
        zid = link.zone.id
        self.props["RespawnZoneID"].value = zid
        self.props["RespawnLinkNameID"].value = FName(link.name_id)
        if set_checkpoint and link.safe:
            self.props["LastCheckpointZoneID"].value = zid
            self.props["LastCheckpointNameID"].value = FName(link.name_id)
        if make_active and not self.active:
            self.save.active_slot = self.slot

    def __repr__(self):
        return "World(%s id=%s slot=%s%s)" % (self.name, self.quest_id, self.slot, " active" if self.active else "")


class WorldSave:
    def __init__(self, savefile):
        cp = savefile.data.class_path
        if cp is None or cp[0] != WORLD_CLASS:
            raise SaveFormatError("not a world save (save_N.sav)")
        self.sf = savefile
        self.root = savefile.data.objects[0].props
        self.containers = {}
        for o in savefile.data.objects[1:]:
            if o.props is not None and "Key" in o.props and "Blob" in o.props:
                self.containers[o.props["Key"].value.name] = o.props["Blob"].value.value

    @classmethod
    def load(cls, path):
        return cls(SaveFile.load(path))

    @property
    def active_slot(self):
        return self.root["LastActiveRootSlot"].value

    @active_slot.setter
    def active_slot(self, v):
        self.root["LastActiveRootSlot"].value = int(v)

    def worlds(self):
        main = self.containers.get(MAIN_KEY)
        if main is None:
            return []
        out = []
        for _, a in main.actors:
            o = a.archive.objects[0]
            if o.props is not None and "RespawnZoneID" in o.props and "SlotID" in o.props:
                out.append(World(self, o))
        out.sort(key=lambda w: w.slot)
        return out

    def active_world(self):
        for w in self.worlds():
            if w.active:
                return w
        return None


def is_world_save(sf):
    cp = sf.data.class_path
    return cp is not None and cp[0] == WORLD_CLASS


_HINT_DROP = {"Checkpoint", "Waypoint", "WP", "Quest", "ZoneLink", "Link"}


def point_hint(name_id):
    """'539_Checkpoint_End' -> ['End'], '528_Zone2_StartWP' -> ['Zone', '2', 'Start'] (English tokens)."""
    import re
    body = re.sub(r"^\d+_", "", name_id)
    words = []
    for part in body.split("_"):
        if part.endswith("WP") and len(part) > 2:
            part = part[:-2]
        for w in re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[0-9])(?=[A-Za-z])", " ", part).split():
            if w not in _HINT_DROP:
                words.append(w)
    return words


def quest_id_of(name_id):
    import re
    m = re.match(r"^(\d+)_", name_id)
    return int(m.group(1)) if m else None
