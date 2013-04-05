from copy import deepcopy
import datetime
import time
import stat
import os
import mimetypes
import email
import hashlib
from abc import ABCMeta, abstractmethod
from pymongo.cursor import Cursor
from cherrycommon.db import DataProvider, DEFAULT_HOST, DEFAULT_PORT
from tornado.web import Application, StaticFileHandler, HTTPError, URLSpec, RequestHandler
from tornado.template import BaseLoader, Template

from cherrycommon.dictutils import JSON, AMF, encode_data, decode_data, get_content_type
from cherrycommon.mathutils import random_id
from cherrycommon.pathutils import norm_path, file_path


class CherryURLSpec(URLSpec):
    def __init__(self, pattern, handler_class, kwargs=None, name=None, prefix=''):
        if not prefix.startswith('^'):
            prefix = '^{}'.format(prefix)
        pattern = '{}{}'.format(prefix, pattern)
        name = name or 'ch-{}'.format(random_id(8))
        super(CherryURLSpec, self).__init__(pattern, handler_class, kwargs, name)

    def __eq__(self, other):
        if isinstance(other, basestring):
            return self.name == other
        else:
            return self.name == other.name


class CherryTemplateLoader(BaseLoader):
    """This template loader can load templates from multiple locations on harddrive.
    """

    def __init__(self, path, **kwargs):
        super(CherryTemplateLoader, self).__init__(**kwargs)
        self.path = map(norm_path, path)

    def resolve_path(self, name, parent_path=None):
        return file_path(name, self.path)

    def _create_template(self, name):
        with open(name, 'rb') as f:
            return Template(f.read(), name=name, loader=self)


class CrossDomainHandler(RequestHandler):
    def get(self, *args, **kwargs):
        self.set_header('Content-type', 'text/x-cross-domain-policy')
        self.write(
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE cross-domain-policy SYSTEM "http://www.adobe.com/xml/dtds/cross-domain-policy.dtd">\n'
            '<cross-domain-policy>'
            '<allow-access-from domain="*" secure="false"/>'
            '</cross-domain-policy>')


class CherryRequestHandler(RequestHandler):
    """This handler uses CherryTemplateLoader, so you can load templates from list of locations.
    Just provide iterable with path in handler's template_path named argument.
    """

    def initialize(self, templates_path=(), **kwargs):
        templates_path = list(templates_path)
        try:
            templates_path.insert(0, self.application.settings['template_path'])
        except KeyError:
            pass
        self.templates_path = map(norm_path, templates_path)

    def get_template_path(self):
        return 'ch-template-{}'.format(':'.join(self.templates_path))

    def create_template_loader(self, template_path):
        settings = self.application.settings
        if "template_loader" in settings:
            return settings["template_loader"]

        kwargs = {}
        if "autoescape" in settings:
            # autoescape=None means "no escaping", so we have to be sure
            # to only pass this kwarg if the user asked for it.
            kwargs["autoescape"] = settings["autoescape"]

        return CherryTemplateLoader(self.templates_path, **kwargs)


class CherryStaticHandler(StaticFileHandler):
    """This slightly modified static file handler can host files from multiple locations
    """

    def initialize(self, path=(), default_filename=None):
        if isinstance(path, basestring):
            path = path,
        self.path = map(norm_path, path)

    # TODO: split this copypasted from tornado spaghetti to several methods to simplify subclassing, until they fix it.
    def get(self, path, include_body=True):
        try:
            path = file_path(path, self.path)
        except OSError:
            raise HTTPError(404)

        stat_result = os.stat(path)
        modified = datetime.datetime.fromtimestamp(stat_result[stat.ST_MTIME])

        self.set_header("Last-Modified", modified)

        mime_type, encoding = mimetypes.guess_type(path)
        if mime_type:
            self.set_header("Content-Type", mime_type)

        cache_time = self.get_cache_time(path, modified, mime_type)
        if cache_time > 0:
            self.set_header("Expires", datetime.datetime.utcnow() + datetime.timedelta(seconds=cache_time))
            self.set_header("Cache-Control", "max-age=" + str(cache_time))
        else:
            self.set_header("Cache-Control", "public")

        self.set_extra_headers(path)

        # Check the If-Modified-Since, and don't send the result if the
        # content has not been modified
        ims_value = self.request.headers.get("If-Modified-Since")
        if ims_value is not None:
            date_tuple = email.utils.parsedate(ims_value)
            if_since = datetime.datetime.fromtimestamp(time.mktime(date_tuple))
            if if_since >= modified:
                self.set_status(304)
                return

        with open(path, "rb") as f:
            data = f.read()
            hasher = hashlib.sha1()
            hasher.update(data)
            self.set_header("Etag", '"%s"' % hasher.hexdigest())
            if include_body:
                self.write(data)
            else:
                assert self.request.method == "HEAD"
                self.set_header("Content-Length", len(data))


class DataHandler(RequestHandler):
    # TODO: Documentation
    data_format = AMF

    def encode_data(self, data):
        return encode_data(data, self.data_format)

    def decode_data(self, data):
        return decode_data(data, self.data_format)

    _request_data = None

    def get_request_data(self):
        if self._request_data is None:
            try:
                self._request_data = self.decode_data(self.request.body)
            except (TypeError, ValueError):
                self._request_data = {}
        return self._request_data

    _ARG_DEFAULT = []

    def get_argument(self, name, default=_ARG_DEFAULT, strip=True):
        try:
            return self.get_request_data()[name]
        except KeyError:
            return super(DataHandler, self).get_argument(name, default=default, strip=strip)

    def respond(self, data=None):
        self.set_header('Content-Type', get_content_type(self.data_format))
        self.write(self.encode_data(data))


class JSONPHandler(DataHandler):
    data_format = JSON
    jsonp_template = '{callback}({data});'
    jsonp_callback_argument = 'jsonp_callback'

    def respond(self, data=None):
        callback = self.get_argument(self.jsonp_callback_argument)
        data = self.jsonp_template.format(callback, self.encode_data(data))
        self.set_header('Content-Type', 'text/javascript')
        self.write(data)


# Some abstract handlers here
class AbstractCollectionHandler(DataHandler):
    """Abstract class for handlers which supposed to provide access to collections, stored in the DB or memory.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def query_documents(self, **kwargs):
        """Implement this method with functionality to query documents from database.
        Also query can be populated with some default parameters.
        :param kwargs:
        :return: iterable with documents in collection, matched corresponding query.
        """

    def get_documents(self, **kwargs):
        return self.query_documents(**kwargs)

    @abstractmethod
    def get_ids(self):
        """Implement this method to get all document's ids in collection.
        """

    @abstractmethod
    def get_document(self, _id):
        """Implement this method to get document with provided _id.

        :param _id: Document's id.
        :return: Matched document from collection.
        :raises KeyError: If document with provided id not found in the collection.
        """

    def prepare(self):
        self.set_header('Expires', '0')
        self.set_header('Last-Modified', datetime.datetime.now().strftime('%a, %d %m %Y %H:%M:%S') + ' GMT')
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.set_header('Cache-Control', 'pre-check=0, post-check=0, max-age=0')
        self.set_header('Pragma', 'no-cache')


class CollectionHandler(AbstractCollectionHandler):
    """Mongo collection handler. Provide access to collections, stored in mongodb.
    """

    data_format = JSON

    def initialize(self, db=None, collection=None, host=DEFAULT_HOST, port=DEFAULT_PORT,
                   use_cache=False, data_format=JSON):
        if db is None:
            try:
                db = getattr(self, 'db')
            except AttributeError:
                raise AttributeError('Either set db name in handler arguments or set it as an attribute')
        else:
            self.db = db

        if collection is None:
            try:
                collection = getattr(self, 'collection')
            except AttributeError:
                raise AttributeError('Either set collection name in handler arguments or set it as an attribute')
        else:
            self.collection = collection

        self.data_provider = DataProvider(db, collection, host=host, port=port)
        self.data_format = data_format

    def query_documents(self, **kwargs):
        return self.data_provider.find(**kwargs)

    def get_ids(self):
        return self.data_provider.keys()

    def get_document(self, _id):
        return self.data_provider.get(_id)


class CollectionDumper(CollectionHandler):
    def respond(self, data=None):
        if isinstance(data, Cursor):
            data = list(data)
        super(CollectionDumper, self).respond(data)

    def get(self, *args, **kwargs):
        ids = self.get_arguments('ids')
        if ids:
            self.respond(self.get_documents(spec={'_id': {'$in': ids}}, **kwargs))
            return

        keys = self.get_argument('keys', False)
        if keys:
            self.respond(self.get_ids())
            return

        self.respond(self.get_documents())


class CollectionCRUD(CollectionDumper):
    def generate_document_id(self, document):
        document.setdefault('_id', random_id())
        return document

    def save_document(self, document):
        self.data_provider.save(document)

    def put_document(self, document_id, document):
        self.data_provider.update(document_id, {'$set': document}, upsert=True)

    def delete_document(self, document_id):
        self.data_provider.remove(document_id)

    def post(self, *args, **kwargs):
        document = decode_data(self.request.body, self.data_format)
        document = self.generate_document_id(document)
        self.save_document(document)
        self.respond(document)

    def put(self, *args, **kwargs):
        document = decode_data(self.request.body, self.data_format)
        document_id = document.pop('_id', kwargs['id'])
        self.put_document(document_id, document)
        self.respond(document)

    def delete(self, *args, **kwargs):
        document_id = kwargs['id']
        self.delete_document(document_id)


_DEFAULT_HOST = '.*$'


def add_handler(application, spec, host=_DEFAULT_HOST):
    """Add handler to the tornado application, after it's initialized, i.e. on the fly.
    It's definitely a hack, but whatever...

    :param application: Tornado application where handler should be registered.
    :type application: Application
    :param spec: Specification for handler.
    :type spec: URLSpec or tuple or list or dict
    :return: URLSpec for registered handler.
    """
    if isinstance(spec, (tuple, list)):
        l = len(spec)
        if 2 <= l <= 4:
            spec = CherryURLSpec(*spec)
        else:
            raise AttributeError('Invalid spec')
    elif isinstance(spec, dict):
        spec = deepcopy(spec)
        spec = CherryURLSpec(**spec)
    elif not isinstance(spec, URLSpec):
        raise TypeError('Invalid spec: {}'.format(spec))

    app_handlers = application.handlers

    # Find host, if it exists.
    for current_host, handlers in reversed(app_handlers):
        if current_host == host:
            handlers.append(spec)
            return spec

    # Host is registered in application yet. Prepare, what we about to add.
    adding_handlers = [host, [spec]]

    # If host is default and it's not registered in the application yet, than add it to the end of the handlers list.
    if host == _DEFAULT_HOST:
        app_handlers.append(adding_handlers)
        return spec

    # Host is not found and is not default. Add it at the end of the list, but before default host, if it is exists.
    last_host, last_handlers = app_handlers[-1]
    if last_host == _DEFAULT_HOST:
        app_handlers.insert(-1, adding_handlers)
    else:
        app_handlers.append(adding_handlers)
    return spec