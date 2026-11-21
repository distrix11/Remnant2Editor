"""Update check: one HTTPS request to the GitHub releases API, at most once a day. It only *tells* you about a newer
release (and opens the releases page on request): it never downloads or replaces anything.

Sent to GitHub: a normal HTTPS GET (your IP address and the user agent "Remnant2SaveEditor/<version>"), nothing else.
Switch it off in the About window (settings.json: "check_updates": false).
"""
import json
import re
import time
import urllib.request

from . import __version__, REPO_URL, settings

API = "https://api.github.com/repos/distrix11/Remnant2Editor/releases/latest"
INTERVAL = 24 * 3600
RELEASES_URL = REPO_URL + "/releases/latest"   # always this fixed page, never a URL taken from the response


def parse_version(s):
    m = re.search(r"(\d+(?:\.\d+)*)", s or "")
    return tuple(int(x) for x in m.group(1).split(".")) if m else None


def is_newer(latest, current=__version__):
    a, b = parse_version(latest), parse_version(current)
    if a is None or b is None:
        return False
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


def fetch_latest(timeout=6):
    """Latest published (non-draft, non-prerelease) release tag, e.g. "v1.5.1". Raises on network / format errors."""
    req = urllib.request.Request(API, headers={"User-Agent": "Remnant2SaveEditor/%s" % __version__,
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    tag = data.get("tag_name") if isinstance(data, dict) else None
    if not isinstance(tag, str) or parse_version(tag) is None:
        raise ValueError("unexpected response from GitHub")
    return tag


def enabled():
    return bool(settings.get("check_updates"))


def due(now=None):
    if not enabled():
        return False
    try:
        last = float(settings.get("last_update_check") or 0)
    except (TypeError, ValueError):
        last = 0.0
    return (now or time.time()) - last >= INTERVAL


def mark_checked(now=None):
    settings.set("last_update_check", now or time.time())
