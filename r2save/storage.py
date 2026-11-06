"""Locating saves, backups and safe writing."""
import glob
import os
import shutil
import subprocess
import sys
import time

from .core import SaveFile, decompress

GAME_EXE = "Remnant2-Win64-Shipping.exe"


def default_save_dirs():
    """All Steam save folders: %USERPROFILE%/Saved Games/Remnant2/Steam/<id>."""
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    base = os.path.join(home, "Saved Games", "Remnant2")
    out = []
    for store in ("Steam", "EOS"):
        out += [d for d in glob.glob(os.path.join(base, store, "*")) if os.path.isdir(d)]
    # Epic / Game Pass layouts differ; the user can always pick the folder manually.
    return sorted(out)


def game_running():
    if sys.platform != "win32":
        return False
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq %s" % GAME_EXE, "/NH"],
                             capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        return GAME_EXE.lower() in out.lower()
    except Exception:
        return False


def backup(path, backup_dir=None):
    """Copy path to <save dir>/_editor_backups/<name>.<timestamp>.sav. Returns the backup path."""
    d = backup_dir or os.path.join(os.path.dirname(os.path.abspath(path)), "_editor_backups")
    os.makedirs(d, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = os.path.splitext(os.path.basename(path))[0]
    dst = os.path.join(d, "%s.%s.sav" % (base, stamp))
    i = 1
    while os.path.exists(dst):
        dst = os.path.join(d, "%s.%s-%d.sav" % (base, stamp, i))
        i += 1
    shutil.copy2(path, dst)
    prune_backups(d, base)
    return dst


def _stamp_key(name):
    """Sort key for 'base.YYYYMMDD-HHMMSS[-n].sav' (creation order, unlike mtime which copy2 preserves)."""
    parts = name.split(".")
    stamp = parts[1] if len(parts) >= 3 else ""
    try:
        return (stamp[:15], int(stamp[16:]) if len(stamp) > 16 else 0)
    except ValueError:
        return (stamp, 0)


def prune_backups(backup_dir, base, keep=None):
    """Keep only the newest `keep` editor backups of one save (base = 'profile' / 'save_0').
    keep=None reads the setting; 0 keeps everything. Returns the removed paths."""
    if keep is None:
        from . import settings
        try:
            keep = int(settings.get("backups_keep"))
        except (TypeError, ValueError):
            keep = 20
    if keep <= 0 or not os.path.isdir(backup_dir):
        return []
    mine = [n for n in os.listdir(backup_dir)
            if n.endswith(".sav") and n.split(".", 1)[0] == base and n.count(".") >= 2]
    mine.sort(key=_stamp_key, reverse=True)
    removed = []
    for n in mine[keep:]:
        p = os.path.join(backup_dir, n)
        try:
            os.remove(p)
            removed.append(p)
        except OSError:
            pass
    return removed


def safe_write(sf, path, make_backup=True, check_game=True):
    """Serialize, verify by re-parsing, back up the original, then atomically replace it.
    Returns the backup path (or None)."""
    if check_game and game_running():
        raise RuntimeError("Remnant 2 is running. Close the game (fully, to the desktop) before saving.")
    buf = sf.to_buffer()
    data = sf.to_bytes()
    # verification: the compressed bytes must decompress to exactly what we serialized,
    # and that must parse again and serialize identically.
    if decompress(data) != buf:
        raise RuntimeError("verification failed: compression round-trip mismatch")
    if SaveFile.from_buffer(buf).to_buffer() != buf:
        raise RuntimeError("verification failed: re-parse mismatch")
    bak = backup(path) if (make_backup and os.path.exists(path)) else None
    tmp = path + ".editor-tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return bak


# ----------------------------------------------------------------------------- backups

BACKUP_DIR = "_editor_backups"


def save_dir_of(path):
    """Save folder for a save, an editor backup or a game .bak file."""
    d = os.path.dirname(os.path.abspath(path))
    return os.path.dirname(d) if os.path.basename(d) == BACKUP_DIR else d


def backup_target(path):
    """'profile.20261105-184220.sav' / 'profile.bak2' / 'save_0.20261105-185600-1.sav' -> 'profile.sav' / 'save_0.sav'."""
    name = os.path.basename(path)
    base = name.split(".", 1)[0]
    if not base or not (base == "profile" or base.startswith("save_")):
        return None
    return base + ".sav"


def list_backups(save_dir):
    """Editor backups and the game's own .bak1-3, newest first.
    Each entry: dict(path, target, source ('editor'|'game'), mtime, size)."""
    out = []
    bdir = os.path.join(save_dir, BACKUP_DIR)
    if os.path.isdir(bdir):
        for n in os.listdir(bdir):
            if n.endswith(".sav") and backup_target(n):
                out.append(("editor", os.path.join(bdir, n)))
    for n in os.listdir(save_dir):
        if ".bak" in n and backup_target(n):
            out.append(("game", os.path.join(save_dir, n)))
    res = []
    for src, p in out:
        try:
            st = os.stat(p)
        except OSError:
            continue
        res.append({"path": p, "target": backup_target(p), "source": src, "mtime": st.st_mtime, "size": st.st_size})
    res.sort(key=lambda e: e["mtime"], reverse=True)
    return res


def restore(backup_path, check_game=True):
    """Replace the matching save with backup_path. The current file is backed up first.
    Returns (target path, backup of the replaced file or None)."""
    if check_game and game_running():
        raise RuntimeError("Remnant 2 is running. Close the game before restoring.")
    target_name = backup_target(backup_path)
    if target_name is None:
        raise ValueError("not a save backup: %s" % backup_path)
    target = os.path.join(save_dir_of(backup_path), target_name)
    SaveFile.load(backup_path)  # must be a valid save
    safety = backup(target) if os.path.exists(target) else None
    tmp = target + ".editor-tmp"
    shutil.copyfile(backup_path, tmp)
    os.replace(tmp, target)
    return target, safety
