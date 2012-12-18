from collections import Mapping, Sequence, MutableMapping
import re
from types import NoneType

def dump_value(value):
    if hasattr(value, 'dump'):
        return value.dump()
    if isinstance(value, basestring):
        return unicode(value)
    elif isinstance(value, (tuple, list, set)):
        return map(dump_value, value)
    elif isinstance(value, dict):
        #TODO: Raise an exception if key is empty string or None.
        return dict((key, dump_value(value)) for key, value in value.iteritems()
            if key is not None or key!='')
    elif isinstance(value, int) and value > 0xffffffff:
        return long(value)
    return value

def flatten_value(value):
    if isinstance(value, (dict, DictView)):
        return dict((k, flatten_value(v)) for k, v in value.iteritems())
    elif isinstance(value, (list, ListView)):
        return map(flatten_value, value)
    elif isinstance(value, basestring):
        value = unicode(value)
        try:
            value = float(value)
        except ValueError:
            return value
    if isinstance(value, float):
        int_value = int(value)
        if int_value == value:
            return int_value
    return value

def is_empty(value):
    if isinstance(value, dict):
        if not len(value):
            return True
        for k, v in value.iteritems():
            if not is_empty(v):
                return False
        return True
    else:
        return False

def merge(target, source, keep_none=False, skip_empty=True):
    if source is None:
        return None
    for key, source_value in source.items():
        if source_value is None:
            if keep_none:
                target[key] = None
            else:
                target.pop(key, None)
            continue
        if skip_empty and is_empty(source_value):
            continue
        if isinstance(source_value, dict):
            target_value = target.get(key, {})
            if isinstance(target_value, MappingView):
                target_value = target_value.dump()
            elif not isinstance(target_value, dict):
                target_value = {}
            merge(target_value, source_value, keep_none=keep_none, skip_empty=skip_empty)
            target[key] = target_value
        else:
            target[key] = dump_value(source_value)
    return target

def view_value(value):
    if isinstance(value, str):
        return unicode(value)
    elif isinstance(value, (dict, MappingView)):
        return DictView(value)
    elif isinstance(value, (list, set, tuple, ListView)):
        return ListView(value)
    else:
        return value

_default = object()
_field_pattern = re.compile('(([^\.\[\]]+)(\[(\d+)\])?)+')
def split_field(field):
    match = _field_pattern.match(field)
    if not match:
        raise ValueError('Invalid field: {}'.format(field))
    full_match, nested_field, _, index = match.groups()
    if index is not None:
        index = int(index)
    return full_match, nested_field, index

def get_value(document, field, default=_default, flatten=True):
    """This function will try to get value from a document by the field name. Nested fields supported.
    For nested lists you can provide indexes in the form `nested_list[0]`.

    Examples:
        >>> document = {'nested_dict':{'a': 1, 'b': 2}, 'nested_list': [0, 1, {'a':1}]}
        >>> get_value(document, 'nested_dict.a')
        1L
        >>> get_value(document, 'nested_list[0]')
        0L
        >>> get_value(document, 'nested_list[2].a')
        1L

    :param document: Object to lookup field in
    :type document: dict or MappingView
    :param field: dot separated field name
    :type field: basestring
    :param default: Default value to return, if field not found in the document. If default is None -
     KeyError will be raised.
    :return: if the field found in document, it's value will be converted to most simple format available.
     i.e. all dumpable values will be dumped, also the function will try to convert value to number.
    """
    if not isinstance(document, (dict, MappingView)):
        raise TypeError('Only mapping type supported as a document')

    full_match, nested_field, index = split_field(field)
    try:
        value = document[nested_field]
    except KeyError:
        if default is not _default:
            return default
        raise KeyError('Field not found: {}'.format(field))

    if index is not None:
        if not isinstance(value, (tuple, list, ListView)):
            raise TypeError('Nested value is not a list')
        try:
            value = value[int(index)]
        except IndexError:
            if default is not _default:
                return default
            raise

    if full_match != field:
        field = field[len(full_match)+1:]
        return get_value(value, field, default, flatten)

    if not flatten:
        return dump_value(value)
    else:
        return flatten_value(value)

def set_value(document, field, value):
    if not isinstance(document, (dict, MutableMapping)):
        raise TypeError('Only dict or MutableMapping type supported as a document.')

    full_match, nested_field, index = split_field(field)
    if full_match == field:
        if index is not None:
            try:
                nested_value = document[nested_field]
            except KeyError:
                nested_value = [None] * (index + 1)
                document[nested_field] = nested_value
            else:
                if isinstance(nested_value, list):
                    l = len(nested_value)
                    if l <= index:
                        nested_value += [None] * (index + 1 - l)
                else:
                    raise ValueError('Value should be list')
            nested_value[index] = value
        else:
            document[nested_field] = value
    else:
        nested_value = document.setdefault(nested_field, {})
        if index is not None:
            if isinstance(nested_value, list):
                nested_value = nested_value[index]
            else:
                raise ValueError('Value should be list')
        field = field[len(full_match)+1:]
        set_value(nested_value, field, value)

def get_schema(documents, skip_nested=False, keep_none=False):
    if isinstance(documents, (dict, DictView)):
        documents = [documents]
    documents_union = {}
    for document in documents:
        merge(documents_union, document, keep_none)
    schema = []
    queue = sorted([(field, value, 0) for field, value in documents_union.iteritems()])
    while queue:
        field, value, level = queue.pop(0)
        if isinstance(value, dict):
            if not skip_nested:
                schema.append(field)
            nested = sorted([
                ('{}.{}'.format(field, nested_field), nested_value, level+1)
                for nested_field, nested_value in value.iteritems()
            ])
            for nested_tuple in nested:
                queue.insert(0, nested_tuple)
        else:
            schema.append(field)
    return schema


class ListView(Sequence):
    def __init__(self, sequence):
        self._data = sequence

    def __getitem__(self, index):
        return view_value(self._data[index])

    def __len__(self):
        return len(self._data)

    def __contains__(self, item):
        return item in self._data

    def __iter__(self):
        return iter(self._data)

    def dump(self):
        return map(dump_value, self)

    def __str__(self):
        return 'ListView({})'.format(self.dump())

    def __unicode__(self):
        self.__str__()

class MappingView(Mapping):
    def __init__(self, data=None):
        if data is None:
            data = {}
        self._data = data

    def __len__(self):
        return len(self._data)

    def __getitem__(self, item):
        return self.view_value(self._data[item])

    def __contains__(self, item):
        return self._data.__contains__(item)

    def keys(self):
        return self._data.keys()

    def __iter__(self):
        return iter(self.keys())

    def dump(self):
        return dict((key, dump_value(value)) for key, value in self.iteritems())

    def __str__(self):
        return 'MappingView({})'.format(self.dump())

    def __unicode__(self):
        self.__str__()


    @staticmethod
    def view_value(value):
        return view_value(value)

class DictView(MappingView):
    pass

class BaseDiffed(MappingView, MutableMapping):
    pass


class Diffed(MappingView, MutableMapping):
    def __init__(self, data=None, diffs=None):
        if data is None:
            data = {}
        elif not isinstance(data, dict):
            raise TypeError('Only dicts supported. {object!s} given.'.format(object=data))
        super(Diffed, self).__init__(data)
        self._diffs = []
        if isinstance(diffs, dict):
            self.add_diff(diffs)
        elif isinstance(diffs, (tuple, list,)):
            self.add_diff(*diffs)
        else:
            self._diffs = []

    def get_effective_item(self, item):
        """
        Returns "effective" item, i.e. item found in rightmost of applied diffs or in data.
        """
        for lookup in self.lookup():
            try:
                value = lookup[item]
            except KeyError:
                continue
            else:
                return value
        else:
            raise KeyError('{} not found'.format(item))

    def view_effective_item(self, item):
        """
        Returns view for "effective" item, i.e. the value for item from last diff applied.
        """
        return view_value(self.get_effective_item(item))

    def lookup(self):
        """
        Yields applied diffs in reversed order and the data.
        """
        try:
            diff = self._diffs[-1]
        except IndexError:
            yield self._data
        else:
            if diff is None:
                raise LookupError('Object is deleted')
            else:
                yield diff
            for diff in reversed(self._diffs[:-1]):
                if diff is None:
                    break
                elif isinstance(diff, DictView):
                    yield diff
                    break
                else:
                    yield diff
            else:
                yield self._data

    def get_current_diff(self):
        """
        Returns the last applied diff, aka "effective"
        """
        return self.lookup().next()


    def __getitem__(self, item):
        if not self._diffs:
            value = self._data[item]
            if value is None:
                raise KeyError('{} not found'.format(item))
            elif isinstance(value, dict):
                return Diffed(value)
            else:
                return view_value(value)

        last_diff = self._diffs[-1]
        try:
            last_value = last_diff[item]
        except KeyError:
            #If item is not diffed in the last diff we need to gather values from previous diffs
            diffs = []
            for diff in reversed(self._diffs[:-1]):
                try:
                    value = diff[item]
                except KeyError:
                    continue
                except TypeError:
                    value = None

                if isinstance(value, dict):
                    diffs.append(value)
                elif diffs or isinstance(value, DictView):
                    diffs.append(value)
                    break
                else:
                    return view_value(value)

            diffs.reverse()
            value = self._data.get(item)
            try:
                effective_value = diffs[-1]
            except IndexError:
                effective_value = value

            if diffs or isinstance(effective_value, (dict, DictView)):
                last_value = {}
                last_diff[item] = last_value
                diffs.append(last_value)
                return Diffed(value, diffs)
            elif value is None:
                raise KeyError('{} not found'.format(item))
            elif isinstance(value, dict):
                return Diffed(value)
            else:
                return view_value(value)
        else:
            #Return Diffed if last value is dict and value were not deleted in one of the previous diffs.
            if isinstance(last_value, dict):
                re = Diffed(self._data.get(item))
                for diff in self._diffs[:-1]:
                    try:
                        re.add_diff(diff[item])
                    except KeyError:
                        pass
                    except TypeError:
                        re.add_diff(None)
                re.add_diff(last_value)
                return re
            elif last_value is None:
                raise KeyError('{} not found'.format(item))
            else:
                return view_value(last_value)

    def __contains__(self, item):
        for container in self.lookup():
            try:
                value = container[item]
            except KeyError:
                pass
            else:
                return value is not None
        return False


    def keys(self):
        keys = set()
        lookup = list(self.lookup())
        for container in reversed(lookup):
            for key, value in container.iteritems():
                if value is None:
                    keys.discard(key)
                else:
                    keys.add(key)
        return list(keys)

    def effective_keys(self):
        """
        Yields all keys for this this object including deleted ones.
        """
        keys = set()
        for diff in self.lookup():
            keys |= set(diff)
        return list(keys)

    def __len__(self):
        return len(self.keys())

    def __iter__(self):
        for key in self.keys():
            yield key

    @property
    def diffs(self):
        return self._diffs

    def add_diff(self, *diffs):
        for diff in diffs:
            if not isinstance(diff, (dict, DictView, NoneType)):
                raise TypeError('Only dicts, DictViews and Nones accepted. Got {} - {}'.format(diff.__class__.__name__, diff))
            self._diffs.append(diff)

    def remove_diff(self, *diffs):
        for diff in diffs:
            self._diffs.remove(diff)

    def apply_diff(self, *diffs):
        for diff in diffs:
            merge(self._data, diff)

    def flatten_diff(self, *diffs):
        self.apply_diff(*diffs)
        self.remove_diff(*diffs)

    def flatten(self):
        self.flatten_diff(*self.diffs)

    def __setitem__(self, item, value):
        if not self._diffs:
            raise RuntimeError('Assign at least a one diff to Diffed in order to set value.')
        diff = self.get_current_diff()
        if diff is None:
            diff = {}
            self._diffs[-1] = diff
        if isinstance(value, (NoneType, int, long, float, str, unicode, list, tuple, dict, DictView)):
            diff[item] = value
        else:
            raise ValueError('Type not supported: {value_type}'.format(value_type=type(value)))

    def __delitem__(self, item):
        if not self._diffs:
            raise RuntimeError('Assign at least a one diff to Diffed in order to remove value.')
        diff = self.get_current_diff()
        diff[item] = None

    def reset(self, other):
        for key, value in other.iteritems():
            self[key] = value
        for key in set(self.keys()) - set(other):
            self[key] = None

    def dump_item(self, item):
        values = []
        for lookup in self.lookup():
            try:
                value = lookup[item]
            except KeyError:
                pass
            else:
                if isinstance(value, dict):
                    values.insert(0, value)
                elif not values:
                    return dump_value(value)
                else:
                    break
        if not values:
            raise KeyError('{} not found'.format(item))
        else:
            dump = {}
            for value in values:
                dump = merge(dump, value)
            return dump


    def dump(self):
        dump = {}
        for key in self.iterkeys():
            dump[key] = self.dump_item(key)
        return dump

    @staticmethod
    def _dump_diff(diff):
        return merge({}, diff)

    def dump_diff(self):
        return self._dump_diff(self._diffs[-1])

