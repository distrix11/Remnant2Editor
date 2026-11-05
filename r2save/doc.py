"""An open save file with undo history and on-disk change detection."""
import os

from .core import SaveFile
from .storage import safe_write


class StaleFileError(RuntimeError):
    """The file on disk changed after we loaded it (the game saved in the meantime)."""


def file_stamp(path):
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


class Doc:
    def __init__(self, path):
        self.path = path
        self.sf = None
        self.stamp = None
        self.history = []          # [(description, buffer before the change)]
        self.reload()

    @property
    def name(self):
        return os.path.basename(self.path)

    def reload(self):
        self.sf = SaveFile.load(self.path)
        self.stamp = file_stamp(self.path)
        self.history = []

    @property
    def dirty(self):
        return bool(self.history)

    def changed_on_disk(self):
        return file_stamp(self.path) != self.stamp

    def snapshot(self):
        return self.sf.to_buffer()

    def push(self, desc, before):
        self.history.append((desc, before))

    def restore(self, buf):
        self.sf = SaveFile.from_buffer(buf)

    def undo(self):
        desc, buf = self.history.pop()
        self.sf = SaveFile.from_buffer(buf)
        return desc

    def save(self, check_game=True):
        if self.changed_on_disk():
            raise StaleFileError(self.name)
        bak = safe_write(self.sf, self.path, make_backup=True, check_game=check_game)
        self.stamp = file_stamp(self.path)
        self.history = []
        return bak
