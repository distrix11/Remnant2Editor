"""Edit test on a COPY of profile.sav: apply edits, write, re-read, check values and
that nothing else in the tree changed. usage: edit_test.py profile.sav workdir"""
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from r2save.core import SaveFile  # noqa: E402
from r2save.nav import walk, fmt_value  # noqa: E402
from r2save.profile import Profile, CURRENCIES  # noqa: E402
from r2save.storage import safe_write  # noqa: E402


def snapshot(sf):
    return [(path, p.type.name, fmt_value(p.value)) for path, p, _, _ in walk(sf)]


src, work = sys.argv[1], sys.argv[2]
os.makedirs(work, exist_ok=True)
path = os.path.join(work, "profile_test.sav")
shutil.copy2(src, path)

before = snapshot(SaveFile.load(path))
prof = Profile.load(path)
ch = prof.active_character()
print(ch, "XP", ch.experience, "TP", ch.trait_points)

scrap = ch.find_item(CURRENCIES[0][1])
old_scrap = scrap.quantity
scrap.set_quantity(old_scrap + 1)

missing = [(n, p) for n, p in CURRENCIES if ch.find_item(p) is None]
added = None
if missing:
    added = missing[0]
    ch.set_currency(added[1], 5)
    print("added", added[0])

no_qty = next(i for i in ch.items() if i.instance_type == "ItemInstanceData" and not i.has_quantity_field
              and i.category == "Materials")
no_qty.set_quantity(3)
print("qty field inserted on", no_qty.name)

weapon = next(i for i in ch.items() if i.instance_type == "RangedWeaponInstanceData" and i._iprop("Level") is None)
weapon.set_level(2)
print("level inserted on", weapon.name)

arch = [a for a in ch.archetypes() if a.xp == 0][0]
arch.set_xp(1000)
print("xp on", arch.name)

bak = safe_write(prof.sf, path, check_game=False)
print("backup", bak)

prof2 = Profile.load(path)
ch2 = prof2.active_character()
assert ch2.find_item(CURRENCIES[0][1]).quantity == old_scrap + 1
if added:
    it = ch2.find_item(added[1])
    assert it.quantity == 5 and it.instance_type == "ItemInstanceData", it
assert ch2.find_item(no_qty.path).quantity == 3
assert ch2.find_item(weapon.path).level == 2
assert [a for a in ch2.archetypes() if a.path == arch.path][0].xp == 1000

after = snapshot(prof2.sf)
bset, aset = set(before), set(after)
print("tree lines before %d after %d" % (len(before), len(after)))
print("removed:")
for x in sorted(bset - aset, key=str)[:30]:
    print("  -", x)
print("added:")
for x in sorted(aset - bset, key=str)[:40]:
    print("  +", x)
print("ALL ASSERTS PASSED")
