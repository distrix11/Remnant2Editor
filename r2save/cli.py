"""Command line interface.  python -m r2save <command> ...   (python -m r2save -h)"""
import argparse
import os
import shutil
import sys

from .core import SaveFile, decompress
from .nav import walk, fmt_value
from .profile import Profile, CURRENCIES, ARCHETYPE_MAX_XP
from .storage import default_save_dirs, safe_write, backup, game_running
from .world import WorldSave


def _profile_path(args):
    if args.file:
        return args.file
    for d in default_save_dirs():
        p = os.path.join(d, "profile.sav")
        if os.path.exists(p):
            return p
    sys.exit("profile.sav not found, pass --file")


def _match(items, query, key=lambda x: x.name, path=lambda x: x.path):
    q = query.lower()
    exact = [i for i in items if path(i) == query or key(i).lower() == q]
    if exact:
        return exact[0]
    found = [i for i in items if q in key(i).lower() or q in (path(i) or "").lower()]
    if not found:
        sys.exit("nothing matches %r" % query)
    if len(found) > 1:
        print("ambiguous %r, candidates:" % query)
        for i in found[:30]:
            print("  %s   %s" % (key(i), path(i)))
        sys.exit(1)
    return found[0]


def _char(prof, args):
    chars = prof.characters()
    if args.slot is None:
        return prof.active_character()
    for c in chars:
        if c.slot == args.slot:
            return c
    sys.exit("no character in slot %d" % args.slot)


def _save(prof, path, args):
    bak = safe_write(prof.sf, path, make_backup=True, check_game=not args.force)
    print("saved %s (backup: %s)" % (path, bak))


def cmd_info(args):
    path = _profile_path(args)
    prof = Profile.load(path)
    print("file:", path)
    for c in prof.characters():
        mark = "*" if c.slot == prof.active_slot else " "
        print("%s slot %d: %s / %s  power %s  item level %s  trait rank %s  XP %s  trait points %s" % (
            mark, c.slot, c.archetype, c.secondary, c.power_level, c.item_level, c.trait_rank,
            c.experience, c.trait_points))
        for a in c.archetypes():
            print("     %-12s level %2d  xp %6d%s" % (a.name, a.level, a.xp, "  (equipped %d)" % a.slot if a.slot >= 0 else ""))


def cmd_items(args):
    prof = Profile.load(_profile_path(args))
    ch = _char(prof, args)
    for it in sorted(ch.items(), key=lambda i: (i.category, i.name)):
        if args.filter and args.filter.lower() not in (it.name + " " + it.path + " " + it.category).lower():
            continue
        q = it.quantity
        lv = it.level
        print("%5d  %-16s %-34s %8s %6s  %s" % (it.id, it.category, it.name[:34],
                                              "" if q is None else "x%d" % q,
                                              "" if lv is None else "+%d" % lv,
                                              it.path if args.paths else ""))


def cmd_currency(args):
    path = _profile_path(args)
    prof = Profile.load(path)
    ch = _char(prof, args)
    if args.name is None:
        for n, p in CURRENCIES:
            it = ch.find_item(p)
            print("%-28s %s" % (n, it.quantity if it else "-"))
        return
    name, ipath = _match(CURRENCIES, args.name, key=lambda x: x[0], path=lambda x: x[1])
    it = ch.find_item(ipath)
    old = it.quantity if it else None
    ch.set_currency(ipath, args.amount)
    print("%s: %s -> %d" % (name, old, args.amount))
    _save(prof, path, args)


def cmd_set_qty(args):
    path = _profile_path(args)
    prof = Profile.load(path)
    ch = _char(prof, args)
    it = _match(ch.items(), args.item)
    old = it.quantity
    it.set_quantity(args.amount)
    print("%s: %s -> %d" % (it.name, old, args.amount))
    _save(prof, path, args)


def cmd_set_level(args):
    path = _profile_path(args)
    prof = Profile.load(path)
    ch = _char(prof, args)
    it = _match([i for i in ch.items() if i.levelable], args.item)
    old = it.level
    it.set_level(args.level)
    print("%s: +%s -> +%d" % (it.name, old, args.level))
    _save(prof, path, args)


def cmd_archetype(args):
    path = _profile_path(args)
    prof = Profile.load(path)
    ch = _char(prof, args)
    a = _match(ch.archetypes(), args.name)
    xp = ARCHETYPE_MAX_XP if args.xp == "max" else int(args.xp)
    old = a.xp
    a.set_xp(xp)
    print("%s: xp %d -> %d (level is recalculated by the game after the next kill)" % (a.name, old, xp))
    _save(prof, path, args)


def cmd_add_item(args):
    path = _profile_path(args)
    prof = Profile.load(path)
    ch = _char(prof, args)
    t = "EquipmentInstanceData" if args.equipment else "ItemInstanceData"
    it = ch.add_item(args.path, None if args.equipment else args.quantity, t)
    print("added", it)
    _save(prof, path, args)


def cmd_dump(args):
    sf = SaveFile.load(args.sav)
    for p, prop, _, _ in walk(sf):
        if args.filter and args.filter not in p:
            continue
        print("%s [%s] %s" % (p, prop.type.name, fmt_value(prop.value)))


def cmd_verify(args):
    ok = True
    for f in args.sav:
        with open(f, "rb") as fh:
            buf = decompress(fh.read())
        same = SaveFile.from_buffer(buf).to_buffer() == buf
        ok &= same
        print("%s  %s" % ("OK  " if same else "FAIL", f))
    sys.exit(0 if ok else 1)


def cmd_backup(args):
    print(backup(_profile_path(args)))


def cmd_restore(args):
    from .storage import restore
    target, safety = restore(args.backup, check_game=not args.force)
    print("current file backed up to", safety)
    print("restored", args.backup, "->", target)


def cmd_backups(args):
    from .storage import list_backups, save_dir_of
    for b in list_backups(save_dir_of(_profile_path(args))):
        import datetime
        print("%-12s %-7s %s  %s" % (b["target"], b["source"],
              datetime.datetime.fromtimestamp(b["mtime"]).strftime("%Y-%m-%d %H:%M:%S"), b["path"]))


def _world_path(args):
    if args.world:
        return args.world
    prof = _profile_path(args)
    slot = args.slot
    if slot is None:
        slot = Profile.load(prof).active_slot
    p = os.path.join(os.path.dirname(prof), "save_%d.sav" % slot)
    if not os.path.exists(p):
        sys.exit("%s not found, pass --world" % p)
    return p


def cmd_worlds(args):
    path = _world_path(args)
    ws = WorldSave.load(path)
    print("file:", path)
    for w in ws.worlds():
        print("%s slot %d  %s  loads: %s  | after death: %s" % ("*" if w.active else " ", w.slot, w.name,
              w.describe(*w.respawn), w.describe(*w.last_checkpoint)))
        if not (args.all or w.active):
            continue
        for z in w.zones():
            if not z.visited and not args.unvisited:
                continue
            for l in z.links():
                if not l.can_respawn or l.disabled or (not l.safe and not args.links):
                    continue
                if not l.discovered and not args.unvisited:
                    continue
                print("     %4d  %-26s %-11s %-32s %s" % (z.id, z.label[:26], l.type, l.name_id,
                                                         "" if l.discovered else "(not discovered)"))


def cmd_teleport(args):
    path = _world_path(args)
    ws = WorldSave.load(path)
    worlds = ws.worlds()
    w = ws.active_world() if args.world_slot is None else next((x for x in worlds if x.slot == args.world_slot), None)
    if w is None:
        sys.exit("world not found")
    z, l = w.find(args.zone, args.point)
    if l is None:
        sys.exit("point %s not found in zone %s (see: python -m r2save worlds)" % (args.point, args.zone))
    old = w.describe(*w.respawn)
    w.teleport(l)
    print("%s: %s -> %s" % (w.name, old, w.describe(*w.respawn)))
    bak = safe_write(ws.sf, path, make_backup=True, check_game=not args.force)
    print("saved %s (backup: %s)" % (path, bak))


def cmd_bloodmoon(args):
    path = _world_path(args)
    ws = WorldSave.load(path)
    worlds = ws.worlds()
    w = ws.active_world() if args.world_slot is None else next((x for x in worlds if x.slot == args.world_slot), None)
    bmo = w.blood_moon() if w is not None else None
    if bmo is None:
        sys.exit("no Blood Moon event in this world")
    print("%s: chance %s%%, last check %s UTC, last occurred %s UTC" % (w.name, bmo.chance, bmo.last_check, bmo.last_triggered))
    if not args.force_event:
        return
    bmo.force()
    print("prepared: chance %s%%, last check %s UTC" % (bmo.chance, bmo.last_check))
    bak = safe_write(ws.sf, path, make_backup=True, check_game=not args.force)
    print("saved %s (backup: %s)" % (path, bak))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="r2save", description="Remnant 2 save editor (CLI)")
    from . import __version__
    ap.add_argument("--version", action="version", version="%(prog)s " + __version__)
    ap.add_argument("--file", help="path to profile.sav (default: auto-detect)")
    ap.add_argument("--slot", type=int, help="character slot (default: active character)")
    ap.add_argument("--force", action="store_true", help="do not check whether the game is running")
    ap.add_argument("--world", help="path to save_N.sav (default: next to profile.sav)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info", help="characters and archetypes").set_defaults(fn=cmd_info)
    s = sub.add_parser("items", help="list inventory")
    s.add_argument("filter", nargs="?")
    s.add_argument("--paths", action="store_true")
    s.set_defaults(fn=cmd_items)
    s = sub.add_parser("currency", help="show or set a currency/material (adds it if missing)")
    s.add_argument("name", nargs="?")
    s.add_argument("amount", nargs="?", type=int)
    s.set_defaults(fn=cmd_currency)
    s = sub.add_parser("set-qty", help="set quantity of an inventory item")
    s.add_argument("item")
    s.add_argument("amount", type=int)
    s.set_defaults(fn=cmd_set_qty)
    s = sub.add_parser("set-level", help="set upgrade level of a weapon / mutator / relic fragment")
    s.add_argument("item")
    s.add_argument("level", type=int)
    s.set_defaults(fn=cmd_set_level)
    s = sub.add_parser("archetype", help="set archetype XP (number or 'max')")
    s.add_argument("name")
    s.add_argument("xp")
    s.set_defaults(fn=cmd_archetype)
    s = sub.add_parser("add-item", help="add a new item by blueprint path")
    s.add_argument("path")
    s.add_argument("--quantity", type=int, default=1)
    s.add_argument("--equipment", action="store_true", help="ring/amulet/armor (no quantity)")
    s.set_defaults(fn=cmd_add_item)
    s = sub.add_parser("dump", help="print every property of any .sav")
    s.add_argument("sav")
    s.add_argument("filter", nargs="?")
    s.set_defaults(fn=cmd_dump)
    s = sub.add_parser("verify", help="byte-exact parse/write check")
    s.add_argument("sav", nargs="+")
    s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("worlds", help="worlds, zones and spawn points (save_N.sav)")
    s.add_argument("--all", action="store_true", help="list points of every world, not only the active one")
    s.add_argument("--unvisited", action="store_true", help="include unexplored zones / undiscovered points")
    s.add_argument("--links", action="store_true", help="include zone transitions (risky)")
    s.set_defaults(fn=cmd_worlds)
    s = sub.add_parser("teleport", help="set where the game spawns you on the next load")
    s.add_argument("zone", type=int)
    s.add_argument("point")
    s.add_argument("--world-slot", type=int, help="world slot (default: active world)")
    s.set_defaults(fn=cmd_teleport)
    s = sub.add_parser("bloodmoon", help="show Blood Moon state; --now makes the game roll 100%% on the next zone load")
    s.add_argument("--now", dest="force_event", action="store_true")
    s.add_argument("--world-slot", type=int)
    s.set_defaults(fn=cmd_bloodmoon)
    sub.add_parser("backup", help="make a backup of profile.sav").set_defaults(fn=cmd_backup)
    sub.add_parser("backups", help="list editor and game backups").set_defaults(fn=cmd_backups)
    s = sub.add_parser("restore", help="restore profile.sav / save_N.sav from a backup file")
    s.add_argument("backup")
    s.set_defaults(fn=cmd_restore)

    args = ap.parse_args(argv)
    if args.cmd == "currency" and args.name is not None and args.amount is None:
        ap.error("currency: amount required")
    args.fn(args)


if __name__ == "__main__":
    main()
