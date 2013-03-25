from collections import MutableMapping
from pymongo import Connection
from cherrycommon.dictutils import MappingView, dump_value, Diffed
from cherrycommon.timeutils import seconds

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 27017
DEFAULT_DB_VERSION = 1


class DataProvider(object):
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    version = DEFAULT_DB_VERSION
    _connection = None

    @classmethod
    def _get_connection(cls):
        if cls._connection is None:
            cls._connection = Connection(host=cls.host, port=cls.port)
        return cls._connection

    @classmethod
    def _get_collection(cls, db_name, collection_name):
        db = cls._get_connection()[db_name]
        return db[collection_name]

    _global_cache = {}

    @classmethod
    def _get_cache(cls, db, collection):
        collection_id = '{collection}@{db}'.format(db=db, collection=collection)
        if not cls._global_cache:
            cls._global_cache = {}
        return cls._global_cache.setdefault(collection_id, {})

    _index_ttl = seconds(hours=1)

    def __init__(self, db, collection, use_cache=True, indexes=None):
        self._db_name = db
        self._collection_name = collection
        self._collection = self._get_collection(db, collection)
        if indexes is not None:
            for index_name in indexes:
                self._collection.ensure_index(index_name, ttl=self._index_ttl)

        if use_cache:
            self._cache = self._get_cache(db, collection)
        else:
            self._cache = None

    def _drop_cache_entry(self, pk):
        if self._cache:
            try:
                del self._cache[pk]
            except KeyError:
                pass

    def _prepare_fields(self, include_fields, exclude_fields):
        if self._cache:
            return None
        if include_fields:
            fields = dict.fromkeys(include_fields, 1)
            fields['_version'] = 1
            return fields
        if exclude_fields:
            return dict.fromkeys(exclude_fields, 0)

    @property
    def use_cache(self):
        return self._cache is not None

    def get(self, pk, include_fields=None, exclude_fields=None, force_reload=False):
        """
        Get document from collection by its primary key. 'fields' argument does not matter,
        if DataProvider caches it's data.
        """
        fields = self._prepare_fields(include_fields, exclude_fields)
        if self.use_cache and (not force_reload):
            try:
                return self._cache[pk]
            except KeyError:
                pass
        document = self._collection.find_one(pk, fields=fields)
        if self.use_cache:
            if document:
                self._cache[pk] = document
            else:
                self._drop_cache_entry(pk)
        return document

    @staticmethod
    def _keys_iterator(cursor):
        for document in cursor:
            yield document['_id'], document

    def find(self, *args, **kwargs):
        """
        Searches collection for documents, that matches filters. Cache is ignored for this operation.
        """
        include_fields = kwargs.pop('include_fields', {})
        exclude_fields = kwargs.pop('exclude_fields', {})
        kwargs['fields'] = kwargs.get('fields') or self._prepare_fields(include_fields, exclude_fields)
        keys = kwargs.pop('keys', False)
        cursor = self._collection.find(*args, **kwargs)
        if keys:
            return self._keys_iterator(cursor)
        else:
            return cursor

    def find_and_modify(self, *args, **kwargs):
        return self._collection.find_and_modify(*args, **kwargs)

    def all(self, include_fields=None, exclude_fields=None, keys=False, *args, **kwargs):
        """
        Yields documents in collection, one-by-one.
        """
        return self.find(include_fields=include_fields, exclude_fields=exclude_fields, keys=keys, *args, **kwargs)

    def ids(self):
        """
        List ids of all documents in collection
        """
        return self._collection.distinct('_id')

    def count(self):
        return self._collection.count()

    def dump_all(self, fields=None):
        #TODO: used only in obsolete admin. Remove this method.
        res = {}
        for o in self.all(fields):
            res[o["_id"]] = o
        return res

    def save(self, document, safe=False):
        """
        Saves document to it's collection. Creates one, if not exists yet.
        """
        document['_version'] = self.version
        self._collection.save(document, safe=safe)
        if hasattr(document, '_id'):
            self._drop_cache_entry(document['_id'])

    def insert(self, documents, safe=False):
        if not isinstance(documents, list):
            documents = [documents]
        for document in documents:
            document['_version'] = document.get('_version') or self.version
        self._collection.insert(documents, safe=safe)

    def update(self, query, modify, upsert=False):
        """
        Updates document in collection according to pymongo update specification.
        """
        #TODO: drop document from cache, if necessary
        if isinstance(query, dict):
            multi = True
        elif isinstance(query, (list, set,)):
            multi = True
            query = {'_id': {'$in': query}}
        else:
            multi = False
            query = {'_id': query}
        self._collection.update(query, modify, safe=True, multi=multi, upsert=upsert)

    def remove(self, q=None):
        if q is not None:
            if isinstance(q, basestring):
                self._drop_cache_entry(q)
                q = {'_id': q}
            self._collection.remove(q)
        else:
            self._collection.remove()
            if self.use_cache:
                self._cache.clear()


class Proxy(MappingView):
    db = ''
    collection = ''
    use_cache = True
    include_fields = ()
    exclude_fields = ()
    dump_fields = ()

    _all = []
    _data_provider = None

    def __init__(self, _id=None, data=None):
        if _id is not None:
            data = self.get_document(_id)
        data = data or {}
        super(Proxy, self).__init__(data)

    @classmethod
    def find(cls,*args,**kwargs):
        return cls.get_data_provider().find(*args,**kwargs)

    @classmethod
    def get_data_provider(cls):
        if not cls._data_provider:
            cls._data_provider = DataProvider(cls.db, cls.collection, cls.use_cache)
        return cls._data_provider

    @classmethod
    def get_document(cls, _id):
        document = cls.get_data_provider().get(_id,
                                               include_fields=cls.include_fields,
                                               exclude_fields=cls.exclude_fields)
        if not document:
            raise KeyError('Document "{}" not found'.format(_id))
        return cls.get_data_provider().get(_id)

    @classmethod
    def all(cls):
        for data in cls.get_data_provider().find(
                include_fields=cls.include_fields, exclude_fields=cls.exclude_fields):
            yield cls(data=data)

    @classmethod
    def ids(cls):
        return cls.get_data_provider().ids()

    @classmethod
    def get_names(cls):
        """
        Alias for ids
        """
        return cls.ids()

    _dump = None

    def dump(self):
        fields = (set(self.dump_fields) or set(self)) - set(self.exclude_fields)
        return dict((field, dump_value(self[field])) for field in fields)

    @property
    def id(self):
        return self['_id']


class DiffedProxy(Proxy, MutableMapping):
    def __init__(self, _id=None, data=None, diffs=()):
        super(DiffedProxy, self).__init__(_id=_id, data=data)
        self._data = Diffed(self._data)
        self.add_diff(*diffs)

    @property
    def diffs(self):
        return self._data.diffs

    def add_diff(self, *diffs):
        self._data.add_diff(*diffs)

    def remove_diff(self, *diffs):
        self._data.remove_diff(*diffs)

    def apply_diff(self, *diffs):
        self._data.apply_diff(*diffs)

    def flatten_diff(self, *diffs):
        self._data.flatten_diff(*diffs)

    def flatten(self):
        self._data.flatten()

    def get_current_diff(self):
        return self._data.get_current_diff()

    def dump(self):
        return self._data.dump()

    def dump_diff(self):
        return self._data.dump_diff()

    def __setitem__(self, item, value):
        self._data[item] = value

    def __delitem__(self, key):
        del self._data[key]

    def __getitem__(self, item):
        return self._data[item]
