"""Generic tree navigation over a parsed save."""
from .core import (SaveFile, SaveData, UObject, PropertyBag, Property, StructProp,
                   ArrayProp, ArrayStructProp, MapProp, PersistenceContainer, ObjectRef)


def walk(node, path="", sd=None):
    """Yield (path, prop, bag, savedata) for every Property in the tree, depth first."""
    if isinstance(node, SaveFile):
        yield from walk(node.data, "", None)
    elif isinstance(node, SaveData):
        for o in node.objects:
            yield from walk(o, "%s/%d:%s" % (path, o.object_index, _short(o.path)), node)
    elif isinstance(node, UObject):
        if node.props is not None:
            yield from _walk_bag(node.props, path, sd)
        for c in node.components or ():
            if c.props is not None:
                yield from _walk_bag(c.props, "%s/[%s]" % (path, c.key), sd)
    elif isinstance(node, PersistenceContainer):
        for uid, a in node.actors:
            name = a.dynamic[2][1] if a.dynamic else "%x" % uid
            yield from walk(a.archive, "%s/<%s>" % (path, name), a.archive)


def _walk_bag(bag, path, sd):
    for p in bag.props:
        pp = "%s.%s" % (path, p.name.name)
        yield pp, p, bag, sd
        yield from _walk_value(p.value, pp, sd)


def _walk_value(v, path, sd):
    if isinstance(v, StructProp):
        yield from _walk_value(v.value, path, sd)
    elif isinstance(v, PropertyBag):
        yield from _walk_bag(v, path, sd)
    elif isinstance(v, ArrayStructProp):
        for i, it in enumerate(v.items):
            yield from _walk_value(it, "%s[%d]" % (path, i), sd)
    elif isinstance(v, ArrayProp):
        for i, it in enumerate(v.items):
            yield from _walk_value(it, "%s[%d]" % (path, i), sd)
    elif isinstance(v, MapProp):
        for i, (k, val) in enumerate(v.items):
            yield from _walk_value(val, "%s{%d}" % (path, i), sd)
    elif isinstance(v, (SaveData, PersistenceContainer)):
        yield from walk(v, path, v if isinstance(v, SaveData) else sd)


def find(node, name):
    return [(p, bag, sd) for _, p, bag, sd in walk(node) if p.name.name == name]


def _short(path):
    if not path:
        return "?"
    return path.rsplit(".", 1)[-1]


def fmt_value(v):
    if isinstance(v, ObjectRef):
        return "-> %s" % (v.path if v.index != -1 else "null")
    if isinstance(v, (bytes, bytearray)):
        return "<%d bytes>" % len(v)
    return repr(v)
