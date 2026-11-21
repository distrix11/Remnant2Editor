"""Update check logic with fake data (no network)."""
import io, json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from r2save import updates, settings

assert updates.parse_version("v1.5.1") == (1, 5, 1)
assert updates.parse_version("junk") is None
assert updates.is_newer("v1.5.2", "1.5.1") and updates.is_newer("1.10.0", "1.9.9")
assert not updates.is_newer("v1.5.1", "1.5.1") and not updates.is_newer("v1.4.0", "1.5.1")
assert not updates.is_newer("garbage", "1.5.1") and not updates.is_newer("v1.5", "1.5.0")

class R(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): pass
def fake(body):
    updates.urllib.request.urlopen = lambda req, timeout=0: R(json.dumps(body).encode())
fake({"tag_name": "v1.6.0"}); assert updates.fetch_latest() == "v1.6.0"
for bad in ({"tag_name": 5}, {}, [], {"tag_name": "x"}):
    fake(bad)
    try: updates.fetch_latest(); raise SystemExit("accepted %r" % (bad,))
    except ValueError: pass

settings.PATH = os.path.join(tempfile.mkdtemp(), "settings.json")
assert updates.enabled() and updates.due()
updates.mark_checked(1000.0)
assert not updates.due(1000.0 + 3600) and updates.due(1000.0 + 90000)
settings.set("check_updates", False); assert not updates.due(10**10)
print("updates OK")
