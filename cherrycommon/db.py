from collections import MutableMapping
from pymongo import MongoClient, Connection
from collections import Mapping
from cherrycommon.dictutils import MappingView, dump_value, Diffed
from cherrycommon.timeutils import seconds

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 27017
DEFAULT_DB_VERSION = 1

_mongo_clients = {}


def get_mongo_client(host=DEFAULT_HOST, port=DEFAULT_PORT, **kwargs):
    """Return (cached) MongoClient instance for provided URL.

    :param host: Host to connect.
    :type host: basestring
    :param port: Port to connect.
    :type port: int
    :rtype: MongoClient
    :return: Instance of MongoClient for provided host - port pair.
    """
    url = '{}:{}'.format(host, port)
    try:
        return _mongo_clients[(host, port)]
    except KeyError:
        client = _mongo_clients[(host, port)] = MongoClient(host, port, **kwargs)
        return client


class DataProvider(Mapping):
    def _get_collection(self, host, port, db, collection):
        try:
            return self._collection
        except AttributeError:
            self._collection = get_mongo_client(host, port)[db][collection]
            return self._collection

    @property
    def collection(self):
        return self._collection

    _global_cache = {}

    @classmethod
    def _get_cache(cls, db, collection):
        return cls._global_cache.setdefault((db, collection), {})

    _index_ttl = seconds(hours=1)

    def __init__(self, db, collection, use_cache=False, indexes=None, host=DEFAULT_HOST, port=DEFAULT_PORT):
        self._db_name = db
        self._collection_name = collection
        self._host = host
        self._port = port
        self._collection = self._get_collection(host, port, db, collection)

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
            return fields
        if exclude_fields:
            return dict.fromkeys(exclude_fields, 0)

    @property
    def use_cache(self):
        return self._cache is not None

    def get(self, _id, include_fields=None, exclude_fields=None, force_reload=False):
        """
        Get document from collection by its primary key. 'fields' argument does not matter,
        if DataProvider caches it's data.
        """
        fields = self._prepare_fields(include_fields, exclude_fields)
        if self.use_cache and (not force_reload):
            try:
                return self._cache[_id]
            except KeyError:
                pass
        document = self._collection.find_one(_id, fields=fields)
        if self.use_cache:
            if document:
                self._cache[_id] = document
            else:
                self._drop_cache_entry(_id)
        return document

    @staticmethod
    def _keys_iterator(cursor):
        for document in cursor:
            yield document['_id'], document

    def find(self, *args, **kwargs):
        """Searches collection for documents, that matches filters. Cache is ignored for this operation.
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
        """Executes find and modify against the collection.
        """
        return self._collection.find_and_modify(*args, **kwargs)

    def find_one(self, spec, *args, **kwargs):
        include_fields = kwargs.pop('include_fields', {})
        exclude_fields = kwargs.pop('exclude_fields', {})
        kwargs['fields'] = kwargs.get('fields') or self._prepare_fields(include_fields, exclude_fields)
        if not isinstance(spec, dict):
            spec = {'_id': spec}
        return self._collection.find_one(spec, *args, **kwargs)

    def all(self, include_fields=None, exclude_fields=None, keys=False, *args, **kwargs):
        """Return cursor with all documents in collection.

        :rtype: Cursor
        """
        return self.find(include_fields=include_fields, exclude_fields=exclude_fields, keys=keys, *args, **kwargs)

    def ids(self):
        """List ids of all documents in collection
        """
        return self._collection.distinct('_id')

    def save(self, document, safe=False):
        """Saves document in collection. Creates one, if not exists yet.
        """
        self._collection.save(document, safe=safe)
        if hasattr(document, '_id'):
            self._drop_cache_entry(document['_id'])

    def insert(self, documents, **kwargs):
        """Stores documents into the collection.

        :param documents: document or list of documents to store.
        """
        if not isinstance(documents, list):
            documents = [documents]
        self._collection.insert(documents, **kwargs)

    def update(self, spec, update, **kwargs):
        """Updates documents in collection.
        You can also pass named args, supported by pymongo.Collection.update method.
        Warning! Update with query will reset all cached documents for this collection.

        :param spec: id, list of ids or query for documents to update.
        :type spec: dict or list of basestring or tuple of basestring or basestring or bson.ObjectID
        :param update: update specification
        :type update: dict
        """
        #TODO: drop document from cache, if necessary
        if isinstance(spec, dict):
            multi = True
        elif isinstance(spec, (list, set,)):
            multi = True
            spec = {'_id': {'$in': spec}}
        elif isinstance(spec, basestring):
            spec = {'_id': spec}
            multi = False
        else:
            raise TypeError('Invalid query: {}'.format(spec))
        kwargs.setdefault('multi', multi)
        self._collection.update(spec, update, safe=True, **kwargs)

    def remove(self, spec=None):
        if spec is not None:
            if isinstance(spec, basestring):
                self._drop_cache_entry(spec)
                spec = {'_id': spec}
            self._collection.remove(spec)
        else:
            self._collection.remove()
            if self.use_cache:
                self._cache.clear()

    # Mapping implementation
    def __getitem__(self, item):
        return self.get(item)

    def __len__(self):
        return self._collection.count()

    def __iter__(self):
        return self.all()

    def keys(self):
        return self.ids()


class PaymentProvider(DataProvider):
    def get_price_for(self, _id, platform_id=None, include_fields=None, exclude_fields=None, force_reload=False):
        """Get payment option by id and use platform specific price. If there's no platform specific price for selected
        option, it will return default ``price``

        :param _id:
        :param platform_id:
        :param include_fields:
        :param exclude_fields:
        :param force_reload:
        :return:
        """
        option = super(PaymentProvider, self).get(
            _id,
            include_fields=include_fields,
            exclude_fields=exclude_fields,
            force_reload=force_reload
        )

        lookup_key = 'price_{}'.format(platform_id or 'default')
        try:
            price = option[lookup_key]
        except KeyError:
            price = option['price']
        if price == 0:
            price = option['price']
        return price

    def all_by_platform(self, platform_id=None, include_fields=None, exclude_fields=None, keys=False, *args, **kwargs):
        """Modifies and return existing payment config for selected platform using ``platform_id``.

        This method will override ``price`` field with provided platform specific value, selected
        from ``price_*platform_id*`` column, but if there's no such column in database it will use default ``price``
        column and return payment config.

        :param platform_id:
        :param include_fields:
        :param exclude_fields:
        :param keys:
        :param args:
        :param kwargs:
        """
        products = super(PaymentProvider, self).all(
            include_fields=include_fields,
            exclude_fields=exclude_fields,
            keys=keys,
            *args,
            **kwargs)

        lookup_key = 'price_{}'.format(platform_id)
        products = list(products)

        if keys:
            for key, config in products:
                if lookup_key in config and not config[lookup_key] == 0:
                    config['price'] = config[lookup_key]
        else:
            for config in products:
                if lookup_key in config and not config[lookup_key] == 0:
                    config['price'] = config[lookup_key]

        return products


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
    def find(cls, *args, **kwargs):
        return cls.get_data_provider().find(*args, **kwargs)

    @classmethod
    def get_data_provider(cls):
        if cls._data_provider is None:
            cls._data_provider = DataProvider(cls.db, cls.collection, cls.use_cache)
        return cls._data_provider

    @classmethod
    def get_document(cls, _id):
        document = cls.get_data_provider().get(
            _id, include_fields=cls.include_fields, exclude_fields=cls.exclude_fields)
        if not document:
            raise KeyError('Document "{}" not found'.format(_id))
        return document

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

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
        return self[key]

