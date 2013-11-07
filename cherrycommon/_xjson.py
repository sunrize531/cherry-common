from zlib import compress, decompress
from json import dumps as _dumps
from json import loads as _loads


def dumps(s):
    return compress(_dumps(s))


def loads(s):
    return decompress(_loads(s))