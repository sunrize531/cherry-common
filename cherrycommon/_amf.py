from zlib import compress, decompress
from pyamf import encode, decode, register_class_loader, ClassAlias, CLASS_CACHE

_amf_aliases = {}

"""This is a pyamf adapter for encode_data and decode_data methods. Also one can simply use this methods.
"""


def register_alias(cls, alias, static_attrs=None, exclude_attrs=None, dynamic=True):
    if static_attrs is None and hasattr(cls, '__slots__'):
        static_attrs = cls.__slots__
    class_alias = ClassAlias(cls, alias, static_attrs=static_attrs, exclude_attrs=exclude_attrs, dynamic=dynamic)
    _amf_aliases[alias] = class_alias
    CLASS_CACHE[cls] = class_alias


def _class_loader(alias):
    return _amf_aliases.get(alias)


register_class_loader(_class_loader)


def _keys_to_string(s):
    if isinstance(s, dict):
        re = {}
        for k, v in s.iteritems():
            k = unicode(k)
            if not k:
                continue
            re[k] = _keys_to_string(v)
        return re
    elif isinstance(s, (list, tuple, set)):
        re = []
        for v in s:
            re.append(_keys_to_string(v))
        return re
    else:
        return s


def dumps(s):
    return compress(encode(_keys_to_string(s)).read())


def loads(s):
    for data in decode(decompress(s)):
        return data