"""What is in a rolled world and which of its loot the character already owns."""
from .itemdb import db, localized

SKIP_PREFIXES = ("Quest_Global", "Quest_GlobalDream", "Quest_Campaign", "Quest_AdventureMode", "Quest_Ward13")

KIND_ORDER = {"boss": 0, "miniboss": 1, "dungeon": 2, "overworld POI": 3, "injectable": 4, "location": 5,
              "item": 6, "event": 7, "story": 8, "trait": 9}


class Loot:
    __slots__ = ("name", "type", "path", "owned")

    def __init__(self, name, type, path, owned):
        self.name, self.type, self.path, self.owned = name, type, path, owned


class Entry:
    """One thing in the roll: a boss, a dungeon, an event, a lone item pickup..."""
    __slots__ = ("quest_id", "quest", "name", "kind", "where", "where_key", "zone_id", "state", "loot")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))
        if self.loot is None:
            self.loot = []
        if self.where_key is None:
            self.where_key = self.where
        if self.where:
            self.where = localized(self.where, self.where)

    @property
    def done(self):
        return self.state == "Complete"

    @property
    def missing(self):
        return [l for l in self.loot if not l.owned]


def analyze(world, owned_paths):
    d = db()
    zones = {z.id: z for z in world.zones()}
    owned = {p.lower() for p in owned_paths if p}
    out = []
    seen_items = set()

    def loot_for(ref):
        res = []
        for e in d.drops.get(ref, []):
            p = e["ProfileId"]
            if p in seen_items and ref.startswith("Quest_Event_"):
                continue
            res.append(Loot(d.item_name(e), e["Type"], p, p.lower() in owned))
        return res

    for qid, (quest, state, zone_id) in sorted(world.quests().items()):
        if quest.startswith(SKIP_PREFIXES):
            continue
        zone = zones.get(zone_id)
        where = zone.label if zone is not None else ""
        ev = d.event(quest)
        if quest.startswith("Quest_Story_"):
            kind, name = "story", localized(quest, (ev.get("Name") if ev else None) or quest[len("Quest_Story_"):])
            out.append(Entry(quest_id=qid, quest=quest, name=name, kind=kind, where=where, zone_id=zone_id,
                             state=state, loot=loot_for(quest)))
            continue
        if quest.startswith("Quest_Event_TraitBook"):
            out.append(Entry(quest_id=qid, quest=quest, name="Trait Book", kind="trait", where=where,
                             zone_id=zone_id, state=state))
            continue
        if ev is None and quest.startswith("Quest_Event_"):
            item_id = quest[len("Quest_Event_"):]
            ie = d.by_id_ci(item_id)
            if ie is not None and ie.get("ProfileId"):
                p = ie["ProfileId"]
                seen_items.add(p)
                out.append(Entry(quest_id=qid, quest=quest, name=d.item_name(ie), kind="item", where=where,
                                 zone_id=zone_id, state=state,
                                 loot=[Loot(d.item_name(ie), ie["Type"], p, p.lower() in owned)]))
            else:
                name = item_id.replace("_", " ")
                if name.lower() == "bloodmoon":
                    name = "Blood Moon"
                out.append(Entry(quest_id=qid, quest=quest, name=name, kind="event", where=where,
                                 zone_id=zone_id, state=state, loot=loot_for(quest)))
            continue
        kind = (ev.get("Subtype") if ev else None) or "event"
        name = (ev.get("Name") if ev else None) or (ev.get("EventLocation") if ev else None) or quest
        name = localized(quest, None) or localized(name, name)
        if ev and ev.get("EventLocation") and kind in ("dungeon", "boss", "miniboss"):
            where = ev["EventLocation"]
        out.append(Entry(quest_id=qid, quest=quest, name=name, kind=kind, where=where, zone_id=zone_id,
                         state=state, loot=loot_for(quest)))

    # items that drop in a specific zone of this world
    labels = {z.label for z in zones.values() if z.id != 1}  # Ward 13 is not part of the roll
    by_loc = {}
    for e in d.entries:
        if e.get("DropType") == "Location" and e.get("DropReference") in labels and e.get("ProfileId") \
                and e.get("Type") in ("ring", "amulet", "armor", "relic", "mutator", "weapon", "mod", "engram"):
            by_loc.setdefault(e["DropReference"], []).append(
                Loot(d.item_name(e), e["Type"], e["ProfileId"], e["ProfileId"].lower() in owned))
    for label, loot in sorted(by_loc.items()):
        out.append(Entry(name=localized(label, label), kind="location", where=label, loot=loot))

    out.sort(key=lambda x: (KIND_ORDER.get(x.kind, 99), x.where or "", x.name or ""))
    return out
