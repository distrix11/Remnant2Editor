"""
Remnant 2 save format: reader/writer.

Python port of lib.remnant2.saves by AndrewSav (MIT License)
https://github.com/AndrewSav/lib.remnant2.saves

Design goal: parse -> write must reproduce the decompressed stream byte-for-byte.
Everything we do not understand is kept as raw bytes.
"""
import struct
import zlib

__all__ = [
    "SaveFile", "SaveData", "UObject", "Component", "PropertyBag", "Property",
    "FName", "ObjectRef", "StructProp", "ArrayProp", "ArrayStructProp", "MapProp",
    "ByteProp", "EnumProp", "TextProp", "Variables", "Variable",
    "PersistenceContainer", "Actor", "decompress", "compress", "SaveFormatError", "KNOWN_FILE_VERSIONS", "peek_header",
]

PROFILE_CLASS = "/Game/_Core/Blueprints/Base/BP_RemnantSaveGameProfile"

CHUNK_TAG = 0x222222229E2A83C1
CHUNK_SIZE = 0x20000
COMPRESSOR_ZLIB = 3


# File format version of every save the editor was tested on (header field; the game build number changes
# with patches and is only reported).
KNOWN_FILE_VERSIONS = (9,)


def peek_header(path):
    """(file format version, game build) read straight from the file, or (None, None)."""
    try:
        with open(path, "rb") as f:
            head = f.read(12)
        version = struct.unpack_from("<I", head, 8)[0] if len(head) >= 12 else None
        build = None
        try:
            buf = decompress(open(path, "rb").read())
            build = struct.unpack_from("<i", buf, 12)[0]
        except Exception:
            pass
        return version, build
    except OSError:
        return None, None


class SaveFormatError(Exception):
    pass


# ----------------------------------------------------------------------------
# Compression
# ----------------------------------------------------------------------------

_CHUNK_HDR = struct.Struct("<QQBQQQQ")  # 49 bytes


def decompress(data):
    """Compressed .sav -> full decompressed buffer (FileHeader + SaveData)."""
    if len(data) < 12:
        raise SaveFormatError("file too small")
    crc, decomp_size, version = struct.unpack_from("<IiI", data, 0)
    out = bytearray(8)
    p = 12
    n = 0
    while p < len(data):
        if p + _CHUNK_HDR.size > len(data):
            raise SaveFormatError("truncated chunk header at %d" % p)
        tag, csize, comp, c1, d1, c2, d2 = _CHUNK_HDR.unpack_from(data, p)
        if tag != CHUNK_TAG:
            raise SaveFormatError("bad chunk tag at %d" % p)
        if comp != COMPRESSOR_ZLIB:
            raise SaveFormatError("unknown compressor %d" % comp)
        p += _CHUNK_HDR.size
        try:
            raw = zlib.decompress(data[p:p + c1])
        except zlib.error as e:
            raise SaveFormatError("file is corrupted: chunk %d does not decompress (%s)" % (n, e))
        if len(raw) != d1:
            raise SaveFormatError("chunk %d: size mismatch" % n)
        out += raw
        p += c1
        n += 1
    save_size = struct.unpack_from("<i", out, 8)[0]
    if save_size + 12 != decomp_size:
        raise SaveFormatError("size mismatch: %d + 12 != %d" % (save_size, decomp_size))
    struct.pack_into("<IiI", out, 0, crc, decomp_size, version)
    if zlib.crc32(memoryview(out)[4:]) & 0xFFFFFFFF != crc:
        raise SaveFormatError("crc32 mismatch - file is corrupted")
    return bytes(out)


def compress(buf, level=6):
    """Full decompressed buffer -> compressed .sav bytes."""
    buf = bytearray(buf)
    crc, decomp_size, version = struct.unpack_from("<IiI", buf, 0)
    out = bytearray(struct.pack("<IiI", crc, decomp_size, version))
    struct.pack_into("<i", buf, 8, decomp_size - 12)
    mv = memoryview(buf)
    cur = 8
    while cur < len(buf):
        part = mv[cur:cur + CHUNK_SIZE]
        comp = zlib.compress(part, level)
        out += _CHUNK_HDR.pack(CHUNK_TAG, CHUNK_SIZE, COMPRESSOR_ZLIB,
                               len(comp), len(part), len(comp), len(part))
        out += comp
        cur += len(part)
    return bytes(out)


# ----------------------------------------------------------------------------
# Low level IO
# ----------------------------------------------------------------------------

class WStr(str):
    """A string that was stored as UTF-16 (kept so we write it back the same way)."""
    __slots__ = ()


class LStr(str):
    """A 'narrow' string containing non-ASCII bytes (kept as latin-1)."""
    __slots__ = ()


_S = {k: struct.Struct("<" + k) for k in "bBhHiIqQfd"}


class Reader:
    __slots__ = ("b", "pos")

    def __init__(self, b, pos=0):
        self.b = b
        self.pos = pos

    def _u(self, k):
        s = _S[k]
        v = s.unpack_from(self.b, self.pos)[0]
        self.pos += s.size
        return v

    def u8(self): return self._u("B")
    def u16(self): return self._u("H")
    def i16(self): return self._u("h")
    def i32(self): return self._u("i")
    def u32(self): return self._u("I")
    def i64(self): return self._u("q")
    def u64(self): return self._u("Q")
    def f32(self): return self._u("f")
    def f64(self): return self._u("d")

    def raw(self, n):
        if n < 0 or self.pos + n > len(self.b):
            raise SaveFormatError("read past end (%d+%d > %d)" % (self.pos, n, len(self.b)))
        v = bytes(self.b[self.pos:self.pos + n])
        self.pos += n
        return v

    def fstring(self):
        n = self.i32()
        if n == 0:
            return None
        if n < 0:
            data = self.raw((-n) * 2)
            if data[-2:] != b"\0\0":
                raise SaveFormatError("bad UTF-16 string terminator at %d" % self.pos)
            return WStr(data[:-2].decode("utf-16-le"))
        if self.pos + n > len(self.b):
            raise SaveFormatError("FString too long at %d" % self.pos)
        data = self.raw(n)
        if data[-1] != 0:
            raise SaveFormatError("bad string terminator at %d" % self.pos)
        try:
            return data[:-1].decode("ascii")
        except UnicodeDecodeError:
            return LStr(data[:-1].decode("latin-1"))


class Writer:
    __slots__ = ("b",)

    def __init__(self):
        self.b = bytearray()

    @property
    def pos(self):
        return len(self.b)

    def _p(self, k, v): self.b += _S[k].pack(v)
    def u8(self, v): self._p("B", v)
    def u16(self, v): self._p("H", v)
    def i16(self, v): self._p("h", v)
    def i32(self, v): self._p("i", v)
    def u32(self, v): self._p("I", v)
    def i64(self, v): self._p("q", v)
    def u64(self, v): self._p("Q", v)
    def f32(self, v): self._p("f", v)
    def f64(self, v): self._p("d", v)
    def raw(self, v): self.b += v

    def patch(self, pos, k, v):
        _S[k].pack_into(self.b, pos, v)

    def fstring(self, s):
        if s is None:
            self.i32(0)
            return
        if isinstance(s, WStr):
            enc = None
        elif isinstance(s, LStr):
            enc = s.encode("latin-1")
        else:
            try:
                enc = s.encode("ascii")
            except UnicodeEncodeError:
                enc = None
        if enc is not None:
            self.i32(len(enc) + 1)
            self.b += enc
            self.b += b"\0"
        else:
            data = s.encode("utf-16-le")
            self.i32(-(len(data) // 2 + 1))
            self.b += data
            self.b += b"\0\0"


# ----------------------------------------------------------------------------
# Context
# ----------------------------------------------------------------------------

class Ctx:
    """Per-SaveData serialization context (names table, objects, class path)."""
    __slots__ = ("names", "objects", "class_path", "_idx")

    def __init__(self, names, class_path, objects=None):
        self.names = names
        self.class_path = class_path
        self.objects = objects
        self._idx = None

    def name_index(self, name, hint=None):
        if hint is not None and hint < len(self.names) and self.names[hint] == name:
            return hint
        if self._idx is None:
            self._idx = {}
            for i, n in enumerate(self.names):
                self._idx.setdefault(n, i)
        i = self._idx.get(name)
        if i is None:
            i = len(self.names)
            self.names.append(name)
            self._idx[name] = i
        return i


# ----------------------------------------------------------------------------
# Basic parts
# ----------------------------------------------------------------------------

class FName:
    __slots__ = ("name", "number", "index")

    def __init__(self, name, number=None, index=None):
        self.name = name
        self.number = number
        self.index = index

    @classmethod
    def read(cls, r, ctx):
        i = r.u16()
        num = None
        if i & 0x8000:
            i &= 0x7FFF
            num = r.i32()
        if i >= len(ctx.names):
            raise SaveFormatError("invalid name index %d at %d" % (i, r.pos))
        return cls(ctx.names[i], num, i)

    def write(self, w, ctx):
        i = ctx.name_index(self.name, self.index)
        if self.number is not None:
            w.u16(i | 0x8000)
            w.i32(self.number)
        else:
            w.u16(i)

    @property
    def wlen(self):
        return 2 if self.number is None else 6

    def __eq__(self, o):
        if isinstance(o, FName):
            return self.name == o.name and self.number == o.number
        if isinstance(o, str):
            return self.name == o
        return NotImplemented

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "FName(%r)" % self.name if self.number is None else "FName(%r,%d)" % (self.name, self.number)

    def __str__(self):
        return self.name


def _read_pg(r):
    """Property guid section: u8 flag [+16 bytes guid]. Returned as raw bytes."""
    flag = r.u8()
    if flag == 0:
        return b"\0"
    return bytes([flag]) + r.raw(16)


class ObjectRef:
    __slots__ = ("index", "_objects")

    def __init__(self, index, objects=None):
        self.index = index
        self._objects = objects

    @property
    def obj(self):
        if self.index == -1 or self._objects is None:
            return None
        return self._objects[self.index]

    @property
    def path(self):
        o = self.obj
        return o.path if o is not None else None

    def __repr__(self):
        return "ObjectRef(%d -> %s)" % (self.index, self.path)


# ----------------------------------------------------------------------------
# Property values
# ----------------------------------------------------------------------------

_NUMERIC = {
    "IntProperty": "i", "Int16Property": "h", "Int64Property": "q",
    "UInt64Property": "Q", "FloatProperty": "f", "DoubleProperty": "d",
    "UInt16Property": "H", "UInt32Property": "I",
}
_STRINGS = ("StrProperty", "SoftClassPath", "SoftObjectProperty")


def read_value(r, ctx, typ, raw):
    """Returns (pg, value). pg is None for untagged (raw) values or types that
    carry their guid internally."""
    k = _NUMERIC.get(typ)
    if k is not None:
        pg = None if raw else _read_pg(r)
        return pg, r._u(k)
    if typ in _STRINGS:
        pg = None if raw else _read_pg(r)
        return pg, r.fstring()
    if typ == "BoolProperty":
        v = r.u8()
        pg = None if raw else _read_pg(r)
        return pg, v
    if typ == "NameProperty":
        pg = None if raw else _read_pg(r)
        return pg, FName.read(r, ctx)
    if typ == "ByteProperty":
        return None, (r.u8() if raw else ByteProp.read(r, ctx))
    if typ == "StructProperty":
        return None, (r.raw(16) if raw else StructProp.read(r, ctx))
    if typ == "ObjectProperty":
        pg = None if raw else _read_pg(r)
        return pg, ObjectRef(r.i32(), ctx.objects)
    if typ == "EnumProperty":
        return None, EnumProp.read(r, ctx)
    if typ == "MapProperty":
        return None, MapProp.read(r, ctx)
    if typ == "TextProperty":
        pg = None if raw else _read_pg(r)
        return pg, TextProp.read(r, ctx)
    if typ == "ArrayProperty":
        return None, _read_array(r, ctx)
    raise SaveFormatError("unknown property type %r at %d" % (typ, r.pos))


def write_value(w, ctx, typ, value, pg=None):
    k = _NUMERIC.get(typ)
    if k is not None:
        if pg is not None:
            w.raw(pg)
        w._p(k, value)
        return
    if typ in _STRINGS:
        if pg is not None:
            w.raw(pg)
        w.fstring(value)
        return
    if typ == "BoolProperty":
        w.u8(int(value))
        if pg is not None:
            w.raw(pg)
        return
    if typ == "NameProperty":
        if pg is not None:
            w.raw(pg)
        value.write(w, ctx)
        return
    if typ == "ByteProperty":
        if isinstance(value, ByteProp):
            value.write(w, ctx)
        else:
            w.u8(value)
        return
    if typ == "StructProperty":
        if isinstance(value, StructProp):
            value.write(w, ctx)
        else:
            w.raw(value)
        return
    if typ == "ObjectProperty":
        if pg is not None:
            w.raw(pg)
        w.i32(value.index if isinstance(value, ObjectRef) else int(value))
        return
    if typ in ("EnumProperty", "MapProperty", "ArrayProperty"):
        value.write(w, ctx)
        return
    if typ == "TextProperty":
        if pg is not None:
            w.raw(pg)
        value.write(w, ctx)
        return
    raise SaveFormatError("unknown property type %r" % typ)


class ByteProp:
    __slots__ = ("enum_name", "pg", "value")

    @classmethod
    def read(cls, r, ctx):
        s = cls()
        s.enum_name = FName.read(r, ctx)
        s.pg = _read_pg(r)
        s.value = r.u8() if s.enum_name.name == "None" else FName.read(r, ctx)
        return s

    def write(self, w, ctx):
        self.enum_name.write(w, ctx)
        w.raw(self.pg)
        if self.enum_name.name == "None":
            w.u8(self.value)
        else:
            self.value.write(w, ctx)

    def __repr__(self):
        return "Byte(%s=%r)" % (self.enum_name, self.value)


class EnumProp:
    __slots__ = ("enum_type", "pg", "value")

    @classmethod
    def read(cls, r, ctx):
        s = cls()
        s.enum_type = FName.read(r, ctx)
        s.pg = _read_pg(r)
        s.value = FName.read(r, ctx)
        return s

    def write(self, w, ctx):
        self.enum_type.write(w, ctx)
        w.raw(self.pg)
        self.value.write(w, ctx)

    def __repr__(self):
        return "Enum(%s)" % self.value


class TextProp:
    __slots__ = ("flags", "history", "data")

    @classmethod
    def read(cls, r, ctx):
        s = cls()
        s.flags = r.u32()
        s.history = r.u8()
        if s.history == 0:
            s.data = (r.fstring(), r.fstring(), r.fstring())  # namespace, key, source
        elif s.history == 255:
            flag = r.u32()
            s.data = (flag, r.fstring() if flag else None)
        else:
            raise SaveFormatError("unsupported text history type %d" % s.history)
        return s

    def write(self, w, ctx):
        w.u32(self.flags)
        w.u8(self.history)
        if self.history == 0:
            for x in self.data:
                w.fstring(x)
        else:
            w.u32(self.data[0])
            if self.data[0]:
                w.fstring(self.data[1])

    @property
    def text(self):
        return self.data[2] if self.history == 0 else self.data[1]

    def __repr__(self):
        return "Text(%r)" % self.text


class MapProp:
    __slots__ = ("key_type", "value_type", "pg", "remove", "items")

    @classmethod
    def read(cls, r, ctx):
        s = cls()
        s.key_type = FName.read(r, ctx)
        s.value_type = FName.read(r, ctx)
        s.pg = _read_pg(r)
        kt, vt = s.key_type.name, s.value_type.name
        s.remove = [read_value(r, ctx, kt, True)[1] for _ in range(r.i32())]
        n = r.i32()
        s.items = []
        for _ in range(n):
            k = read_value(r, ctx, kt, True)[1]
            v = read_value(r, ctx, vt, True)[1]
            s.items.append([k, v])
        return s

    def write(self, w, ctx):
        self.key_type.write(w, ctx)
        self.value_type.write(w, ctx)
        w.raw(self.pg)
        kt, vt = self.key_type.name, self.value_type.name
        w.i32(len(self.remove))
        for k in self.remove:
            write_value(w, ctx, kt, k)
        w.i32(len(self.items))
        for k, v in self.items:
            write_value(w, ctx, kt, k)
            write_value(w, ctx, vt, v)

    def __repr__(self):
        return "Map(%s->%s, %d)" % (self.key_type, self.value_type, len(self.items))


def _read_array(r, ctx):
    elem = FName.read(r, ctx)
    pg = _read_pg(r)
    count = r.u32()
    if elem.name == "StructProperty":
        return ArrayStructProp.read_body(r, ctx, elem, pg, count)
    a = ArrayProp()
    a.elem_type = elem
    a.pg = pg
    t = elem.name
    a.items = [read_value(r, ctx, t, True)[1] for _ in range(count)]
    return a


class ArrayProp:
    __slots__ = ("elem_type", "pg", "items")

    def write(self, w, ctx):
        self.elem_type.write(w, ctx)
        w.raw(self.pg)
        w.u32(len(self.items))
        t = self.elem_type.name
        for it in self.items:
            write_value(w, ctx, t, it)

    def __repr__(self):
        return "Array(%s, %d)" % (self.elem_type, len(self.items))


class ArrayStructProp:
    __slots__ = ("outer_type", "pg", "name_index", "type_index", "size", "index",
                 "struct_type", "guid", "inner_pg", "items")

    @classmethod
    def read_body(cls, r, ctx, outer, pg, count):
        s = cls()
        s.outer_type = outer
        s.pg = pg
        s.name_index = r.u16()
        s.type_index = r.u16()
        s.size = r.u32()
        s.index = r.u32()
        s.struct_type = FName.read(r, ctx)
        s.guid = r.raw(16)
        s.inner_pg = _read_pg(r)
        t = s.struct_type.name
        s.items = [read_struct_value(r, ctx, t) for _ in range(count)]
        return s

    def write(self, w, ctx):
        self.outer_type.write(w, ctx)
        w.raw(self.pg)
        w.u32(len(self.items))
        w.u16(self.name_index)
        w.u16(self.type_index)
        size_pos = w.pos
        w.u32(0)
        w.u32(self.index)
        self.struct_type.write(w, ctx)
        w.raw(self.guid)
        w.raw(self.inner_pg)
        start = w.pos
        t = self.struct_type.name
        for it in self.items:
            write_struct_value(w, ctx, t, it)
        self.size = w.pos - start
        w.patch(size_pos, "I", self.size)

    def __repr__(self):
        return "StructArray(%s, %d)" % (self.struct_type, len(self.items))


_FIXED_STRUCTS = {"Timespan": 8, "DateTime": 8, "Guid": 16, "Vector": 24, "Rotator": 24}


def read_struct_value(r, ctx, typ):
    if typ in ("SoftClassPath", "SoftObjectPath"):
        return r.fstring()
    n = _FIXED_STRUCTS.get(typ)
    if n is not None:
        if typ in ("Timespan", "DateTime"):
            return r.i64()
        return r.raw(n)
    if typ == "PersistenceBlob":
        size = r.i32()
        blob = r.raw(size)
        if ctx.class_path == PROFILE_CLASS:
            br = Reader(blob)
            sd = SaveData.read(br, has_pv=True, has_path=False)
            if br.pos < len(blob):
                sd.extra = blob[br.pos:]
            return sd
        return PersistenceContainer.read(blob, ctx)
    return PropertyBag.read(r, ctx)


def write_struct_value(w, ctx, typ, value):
    if typ in ("SoftClassPath", "SoftObjectPath"):
        w.fstring(value)
    elif typ in ("Timespan", "DateTime"):
        w.i64(value)
    elif typ in _FIXED_STRUCTS:
        w.raw(value)
    elif typ == "PersistenceBlob":
        if isinstance(value, SaveData):
            sub = Writer()
            value.write(sub)
            data = sub.b
        else:
            data = value.to_bytes()
        w.i32(len(data))
        w.raw(data)
    else:
        value.write(w, ctx)


class StructProp:
    __slots__ = ("type", "guid", "pg", "value")

    @classmethod
    def read(cls, r, ctx):
        s = cls()
        s.type = FName.read(r, ctx)
        s.guid = r.raw(16)
        s.pg = _read_pg(r)
        s.value = read_struct_value(r, ctx, s.type.name)
        return s

    def write(self, w, ctx):
        self.type.write(w, ctx)
        w.raw(self.guid)
        w.raw(self.pg)
        write_struct_value(w, ctx, self.type.name, self.value)

    def __repr__(self):
        return "Struct(%s)" % self.type


# ----------------------------------------------------------------------------
# Property / PropertyBag
# ----------------------------------------------------------------------------

class Property:
    __slots__ = ("name", "type", "size", "index", "pg", "value")

    def __init__(self, name=None, type=None, value=None, size=0, index=0, pg=None):
        self.name = name
        self.type = type
        self.value = value
        self.size = size
        self.index = index
        self.pg = pg

    @classmethod
    def read(cls, r, ctx, name):
        p = cls()
        p.name = name
        p.type = FName.read(r, ctx)
        p.size = r.u32()
        p.index = r.u32()
        if name.name == "FowVisitedCoordinates":
            p.value = r.raw(p.size + 19)
            p.pg = None
        else:
            p.pg, p.value = read_value(r, ctx, p.type.name, False)
        return p

    def write(self, w, ctx):
        self.name.write(w, ctx)
        self.type.write(w, ctx)
        size_pos = w.pos
        w.u32(self.size)
        w.u32(self.index)
        start = w.pos
        t = self.type.name
        if self.name.name == "FowVisitedCoordinates" and isinstance(self.value, (bytes, bytearray)):
            w.raw(self.value)
            overhead = 19
        else:
            write_value(w, ctx, t, self.value, self.pg)
            overhead = self._overhead()
        size = w.pos - start - overhead
        if size < 0:
            raise SaveFormatError("negative size for %s" % self.name)
        if size != self.size:
            self.size = size
            w.patch(size_pos, "I", size)

    def _overhead(self):
        v = self.value
        t = self.type.name
        gl = len(self.pg) if self.pg is not None else 1
        if t == "ArrayProperty":
            return (v.outer_type.wlen if isinstance(v, ArrayStructProp) else v.elem_type.wlen) + len(v.pg)
        if t == "BoolProperty":
            return 1 + gl
        if t == "ByteProperty":
            return v.enum_name.wlen + len(v.pg)
        if t == "EnumProperty":
            return v.enum_type.wlen + len(v.pg)
        if t == "MapProperty":
            return v.key_type.wlen + v.value_type.wlen + len(v.pg)
        if t == "StructProperty":
            return v.type.wlen + 16 + len(v.pg)
        return gl

    @property
    def key(self):
        return self.name.name

    def __repr__(self):
        return "%s(%s)=%r" % (self.name, self.type, self.value)


class PropertyBag:
    __slots__ = ("props", "terminator")

    def __init__(self, props=None, terminator=None):
        self.props = props if props is not None else []
        self.terminator = terminator

    @classmethod
    def read(cls, r, ctx):
        b = cls()
        while True:
            name = FName.read(r, ctx)
            if name.name == "None":
                b.terminator = name
                break
            b.props.append(Property.read(r, ctx, name))
        return b

    def write(self, w, ctx):
        for p in self.props:
            p.write(w, ctx)
        (self.terminator or FName("None")).write(w, ctx)

    def get(self, key, default=None):
        for p in self.props:
            if p.name.name == key:
                return p
        return default

    def __getitem__(self, key):
        p = self.get(key)
        if p is None:
            raise KeyError(key)
        return p

    def __contains__(self, key):
        return self.get(key) is not None

    def __iter__(self):
        return iter(self.props)

    def __len__(self):
        return len(self.props)

    def __repr__(self):
        return "Bag[%s]" % ", ".join(p.name.name for p in self.props)


# ----------------------------------------------------------------------------
# Variables (component data)
# ----------------------------------------------------------------------------

_VAR_TYPES = ["None", "BoolProperty", "IntProperty", "FloatProperty", "NameProperty"]
_VAR_COMPONENTS = {"GlobalVariables", "Variables", "Variable", "PersistenceKeys",
                   "PersistanceKeys1", "PersistenceKeys1"}


class Variable:
    __slots__ = ("name", "type", "value")

    @classmethod
    def read(cls, r, ctx):
        v = cls()
        v.name = FName.read(r, ctx)
        if v.name.name == "None":
            raise SaveFormatError("unexpected None in variable")
        t = r.u8()
        if t >= len(_VAR_TYPES):
            raise SaveFormatError("unknown variable type %d" % t)
        v.type = _VAR_TYPES[t]
        if v.type in ("BoolProperty", "IntProperty"):
            v.value = r.u32()
        elif v.type == "FloatProperty":
            v.value = r.f32()
        elif v.type == "NameProperty":
            v.value = FName.read(r, ctx)
        else:
            v.value = None
        return v

    def write(self, w, ctx):
        self.name.write(w, ctx)
        w.u8(_VAR_TYPES.index(self.type))
        if self.type in ("BoolProperty", "IntProperty"):
            w.u32(self.value)
        elif self.type == "FloatProperty":
            w.f32(self.value)
        elif self.type == "NameProperty":
            self.value.write(w, ctx)

    def __repr__(self):
        return "Var(%s:%s=%r)" % (self.name, self.type, self.value)


class Variables:
    __slots__ = ("name", "unknown", "items")

    @classmethod
    def read(cls, r, ctx):
        v = cls()
        v.name = FName.read(r, ctx)
        v.unknown = r.u64()
        v.items = [Variable.read(r, ctx) for _ in range(r.i32())]
        return v

    def write(self, w, ctx):
        self.name.write(w, ctx)
        w.u64(self.unknown)
        w.i32(len(self.items))
        for it in self.items:
            it.write(w, ctx)


# ----------------------------------------------------------------------------
# UObject / Component
# ----------------------------------------------------------------------------

class Component:
    __slots__ = ("key", "props", "variables", "extra")

    def __init__(self, key=None):
        self.key = key
        self.props = None
        self.variables = None
        self.extra = None

    def __repr__(self):
        return "Component(%s)" % self.key


class UObject:
    __slots__ = ("was_loaded", "path", "name", "outer_id", "object_index",
                 "props", "extra", "is_actor", "components", "_path_omitted")

    def __init__(self):
        self.was_loaded = 1
        self.path = None
        self.name = None
        self.outer_id = 0
        self.object_index = 0
        self.props = None
        self.extra = None
        self.is_actor = 0
        self.components = None
        self._path_omitted = False

    @classmethod
    def read_entry(cls, r, ctx, index):
        o = cls()
        o.was_loaded = r.u8()
        if o.was_loaded and index == 0 and ctx.class_path is not None:
            o.path = ctx.class_path
            o._path_omitted = True
        else:
            o.path = r.fstring()
        if not o.was_loaded:
            o.name = FName.read(r, ctx)
            o.outer_id = r.u32()
        return o

    def write_entry(self, w, ctx, index):
        w.u8(self.was_loaded)
        if not (self.was_loaded and index == 0 and ctx.class_path is not None):
            w.fstring(self.path)
        if not self.was_loaded:
            self.name.write(w, ctx)
            w.u32(self.outer_id)

    def read_data(self, r, ctx):
        self.object_index = r.i32()
        n = r.u32()
        start = r.pos
        if n > 0:
            self.props = PropertyBag.read(r, ctx)
            if r.pos > start + n:
                raise SaveFormatError("object %d properties overrun" % self.object_index)
            if r.pos < start + n:
                self.extra = r.raw(start + n - r.pos)
        self.is_actor = r.u8()
        if self.is_actor:
            self.components = []
            for _ in range(r.u32()):
                c = Component(r.fstring())
                ln = r.i32()
                cs = r.pos
                if c.key in _VAR_COMPONENTS:
                    c.variables = Variables.read(r, ctx)
                else:
                    c.props = PropertyBag.read(r, ctx)
                if r.pos > cs + ln:
                    raise SaveFormatError("component %s overrun" % c.key)
                if r.pos < cs + ln:
                    c.extra = r.raw(cs + ln - r.pos)
                self.components.append(c)

    def write_data(self, w, ctx):
        w.i32(self.object_index)
        lp = w.pos
        w.u32(0)
        if self.props is not None:
            s = w.pos
            self.props.write(w, ctx)
            if self.extra:
                w.raw(self.extra)
            w.patch(lp, "I", w.pos - s)
        w.u8(self.is_actor)
        if self.is_actor:
            w.u32(len(self.components))
            for c in self.components:
                w.fstring(c.key)
                lp = w.pos
                w.i32(0)
                s = w.pos
                if c.variables is not None:
                    c.variables.write(w, ctx)
                else:
                    c.props.write(w, ctx)
                if c.extra:
                    w.raw(c.extra)
                w.patch(lp, "i", w.pos - s)

    def __repr__(self):
        return "UObject#%d(%s)" % (self.object_index, self.path)


# ----------------------------------------------------------------------------
# SaveData
# ----------------------------------------------------------------------------

class SaveData:
    __slots__ = ("pv", "class_path", "version", "objects", "names", "extra", "ctx")

    @classmethod
    def read(cls, r, has_pv=True, has_path=True):
        sd = cls()
        sd.pv = r.raw(8) if has_pv else None
        sd.class_path = (r.fstring(), r.fstring()) if has_path else None
        names_off = r.i64()
        sd.version = r.u32()
        objects_off = r.i64()
        data_off = r.pos
        maxpos = r.pos

        r.pos = names_off
        sd.names = [r.fstring() for _ in range(r.i32())]
        if any(n is None for n in sd.names):
            raise SaveFormatError("null entry in names table")
        maxpos = max(maxpos, r.pos)
        ctx = Ctx(sd.names, sd.class_path[0] if sd.class_path else None)

        r.pos = objects_off
        n = r.i32()
        sd.objects = [UObject.read_entry(r, ctx, i) for i in range(n)]
        ctx.objects = sd.objects
        maxpos = max(maxpos, r.pos)

        r.pos = data_off
        for o in sd.objects:
            o.read_data(r, ctx)
        maxpos = max(maxpos, r.pos)
        r.pos = maxpos
        sd.extra = None
        sd.ctx = ctx
        return sd

    def write(self, w):
        if self.pv is not None:
            w.raw(self.pv)
        if self.class_path is not None:
            w.fstring(self.class_path[0])
            w.fstring(self.class_path[1])
        off_pos = w.pos
        w.i64(0)
        w.u32(self.version)
        w.i64(0)
        ctx = Ctx(self.names, self.class_path[0] if self.class_path else None, self.objects)
        for o in self.objects:
            o.write_data(w, ctx)
        objects_off = w.pos
        w.i32(len(self.objects))
        for i, o in enumerate(self.objects):
            o.write_entry(w, ctx, i)
        names_off = w.pos
        w.i32(len(self.names))
        for n in self.names:
            w.fstring(n)
        if self.extra:
            w.raw(self.extra)
        w.patch(off_pos, "q", names_off)
        w.patch(off_pos + 12, "q", objects_off)

    # -- helpers for building new objects --
    def fname(self, name, number=None):
        if name not in self.names:
            self.names.append(name)
        return FName(name, number, self.names.index(name))

    def add_object(self, obj):
        self.objects.append(obj)
        obj.object_index = len(self.objects) - 1
        return obj.object_index

    def __repr__(self):
        return "SaveData(%s, %d objects)" % (self.class_path[0] if self.class_path else "-", len(self.objects))


# ----------------------------------------------------------------------------
# World save persistence container
# ----------------------------------------------------------------------------

class Actor:
    __slots__ = ("has_transform", "transform", "archive", "dynamic")

    def __repr__(self):
        cls = self.dynamic[2][1] if self.dynamic else None
        return "Actor(%s)" % cls


class PersistenceContainer:
    __slots__ = ("version", "destroyed", "actors")

    @classmethod
    def read(cls, blob, ctx):
        r = Reader(blob)
        pc = cls()
        pc.version = r.u32()
        index_off = r.i32()
        dynamic_off = r.i32()
        r.pos = index_off
        infos = [(r.u64(), r.i32(), r.i32()) for _ in range(r.u32())]
        pc.destroyed = [r.u64() for _ in range(r.u32())]
        pc.actors = []
        by_id = {}
        for uid, off, size in infos:
            ar = Reader(blob[off:off + size])
            a = Actor()
            a.has_transform = ar.u32()
            a.transform = ar.raw(80) if a.has_transform else None
            a.archive = SaveData.read(ar, has_pv=False, has_path=False)
            if ar.pos != size:
                raise SaveFormatError("actor %x: %d unread bytes" % (uid, size - ar.pos))
            a.dynamic = None
            pc.actors.append([uid, a])
            by_id[uid] = a
        r.pos = dynamic_off
        for _ in range(r.u32()):
            uid = r.u64()
            tr = r.raw(80)
            cp = (r.fstring(), r.fstring())
            by_id[uid].dynamic = (uid, tr, cp)
        return pc

    def to_bytes(self):
        w = Writer()
        w.u32(self.version)
        w.i32(0)
        w.i32(0)
        infos = []
        for uid, a in self.actors:
            aw = Writer()
            aw.u32(a.has_transform)
            if a.has_transform:
                aw.raw(a.transform)
            a.archive.write(aw)
            infos.append((uid, w.pos, len(aw.b)))
            w.raw(aw.b)
        dynamic_off = w.pos
        dyn = [a.dynamic for _, a in self.actors if a.dynamic is not None]
        w.u32(len(dyn))
        for uid, tr, cp in dyn:
            w.u64(uid)
            w.raw(tr)
            w.fstring(cp[0])
            w.fstring(cp[1])
        index_off = w.pos
        w.u32(len(infos))
        for uid, off, size in infos:
            w.u64(uid)
            w.i32(off)
            w.i32(size)
        w.u32(len(self.destroyed))
        for d in self.destroyed:
            w.u64(d)
        w.patch(4, "i", index_off)
        w.patch(8, "i", dynamic_off)
        return bytes(w.b)


# ----------------------------------------------------------------------------
# SaveFile
# ----------------------------------------------------------------------------

class SaveFile:
    __slots__ = ("crc", "decomp_size", "version", "build", "data", "trailing")

    @classmethod
    def from_buffer(cls, buf):
        r = Reader(buf)
        sf = cls()
        sf.crc = r.u32()
        sf.decomp_size = r.i32()
        sf.version = r.i32()
        sf.build = r.i32()
        sf.data = SaveData.read(r, True, True)
        sf.trailing = buf[r.pos:] if r.pos < len(buf) else b""
        return sf

    @classmethod
    def load(cls, path):
        with open(path, "rb") as f:
            return cls.from_buffer(decompress(f.read()))

    @classmethod
    def load_checked(cls, path):
        """Load and test that the parser understands the whole file: writing it back unchanged must give the
        same bytes. Returns (SaveFile, exact). exact=False means an unknown format detail (e.g. after a game
        patch); such a file must not be saved."""
        with open(path, "rb") as f:
            buf = decompress(f.read())
        sf = cls.from_buffer(buf)
        try:
            exact = sf.to_buffer() == buf
        except Exception:
            exact = False
        return sf, exact

    def to_buffer(self):
        w = Writer()
        w.u32(0)
        w.i32(0)
        w.i32(self.version)
        w.i32(self.build)
        self.data.write(w)
        if self.trailing:
            w.raw(self.trailing)
        w.patch(4, "i", len(w.b))
        crc = zlib.crc32(memoryview(w.b)[4:]) & 0xFFFFFFFF
        w.patch(0, "I", crc)
        return bytes(w.b)

    def to_bytes(self, level=6):
        return compress(self.to_buffer(), level)

    @property
    def is_profile(self):
        return self.data.class_path is not None and self.data.class_path[0] == PROFILE_CLASS
