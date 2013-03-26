import datetime
import time
import stat
import os
import mimetypes
import email
import hashlib
from tornado.web import StaticFileHandler, HTTPError, URLSpec, RequestHandler
from tornado.template import BaseLoader, Template

from cherrycommon.dictutils import JSON, AMF, encode_data, decode_data, get_content_type
from cherrycommon.mathutils import random_id
from cherrycommon.pathutils import norm_path, file_path


class CherryURLSpec(URLSpec):
    def __init__(self, pattern, handler_class, kwargs=None, prefix=''):
        if not prefix.startswith('^'):
            prefix = '^{}'.format(prefix)
        pattern = '{}{}'.format(prefix, pattern)
        name = 'ch-{}'.format(random_id(8))
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


class DataHandler(RequestHandler):
    data_format = AMF

    def encode_data(self, data):
        return encode_data(data, self.data_format)

    def decode_data(self, data):
        return decode_data(data, self.data_format)

    _request_data = None

    def get_request_data(self):
        if self._request_data is None:
            self._request_data = self.decode_data(self.request.body)
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


class CrossDomainHandler(RequestHandler):
    def get(self, *args, **kwargs):
        self.set_header('Content-type', 'text/x-cross-domain-policy')
        self.write(
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE cross-domain-policy SYSTEM "http://www.adobe.com/xml/dtds/cross-domain-policy.dtd">\n'
            '<cross-domain-policy>'
            '<allow-access-from domain="*" secure="false"/>'
            '</cross-domain-policy>')


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
