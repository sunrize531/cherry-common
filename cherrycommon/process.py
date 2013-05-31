from copy import copy
import imp
from logging import getLogger
from multiprocessing import Process
from threading import Thread
import os
from types import ModuleType
import zlib
from cherrycommon.dictutils import decode_data, YAML, dump_value
from cherrycommon.mathutils import random_id
from cherrycommon.pathutils import norm_path
from cherrycommon.timeutils import milliseconds
from zmq.eventloop.ioloop import IOLoop, install


class ProcessException(Exception):
    def __init__(self, process, description):
        Exception.__init__(self, description)
        self.process_id = str(process.info)
        self.description = description

    PATTERN = '{process_id} - {description}'

    def __str__(self):
        return self.PATTERN.format(process_id=self.process_id, description=self.description)


class ProcessInfo(object):
    def __init__(self, process_type='', process_index=0, machine_id=None,
                 ports=None, sockets=None, external_address=None, pid=None, crc=None):
        self.process_type = process_type
        self.process_index = process_index
        self.machine_id = machine_id
        self.pid = pid or os.getpid()
        self.ports = ports or {}
        self.sockets = sockets or {}
        self._crc = crc
        if external_address:
            self.external_address = external_address

    _process_name_pattern = '{process_type}@{machine_id}.{index:03d}'

    @classmethod
    def get_process_name(cls, process_type, machine_id, index):
        return cls._process_name_pattern.format(process_type=process_type, machine_id=machine_id, index=int(index))

    _process_crc_pattern = '{name}.{time:.0f}'

    @classmethod
    def get_process_crc(cls, process_name):
        return zlib.crc32(cls._process_crc_pattern.format(name=process_name, time=milliseconds())) & 0xfff

    _name = None

    @property
    def name(self):
        if self._name is None:
            self._name = self.get_process_name(self.process_type, self.machine_id, self.process_index)
        return self._name

    def init_crc(self):
        self._crc = self.get_process_crc(self.name)
        return self._crc

    _crc = None

    @property
    def crc(self):
        if self._crc is None:
            self.init_crc()
        return self._crc

    _id = None

    @property
    def id(self):
        if self._id is None:
            self._id = '{name}.{hash}'.format(name=self.name, hash=self.crc)
        return self._id

    def __str__(self):
        return self.id

    def __repr__(self):
        return '<ProcessInfo: {}>'.format(self.id)

DEFAULT_MACHINE_ID = 'cherry'
_process_instance = None


class BasicProcess(object):
    @classmethod
    def get_instance(cls, *args, **kwargs):
        """Just singleton implementation.

        :return: Process instance for current application.
        :rtype: BasicProcess
        """
        global _process_instance
        if _process_instance is None:
            _process_instance = cls.__new__(cls)
            _process_instance.__init__(*args, **kwargs)
        return _process_instance

    @classmethod
    def _init_instance(cls, instance):
        cls._instance = instance

    def __init__(self, process_type, process_index=0, machine_id=DEFAULT_MACHINE_ID, crc=None, log=True,
                 ports=None, sockets=None, external_address=None):
        global _process_instance
        _process_instance = self
        self.ports = ports or {}
        self.sockets = sockets or {}
        self.info = ProcessInfo(process_type, process_index=process_index, machine_id=machine_id,
                                ports=self.ports, sockets=self.sockets,
                                external_address=external_address, crc=crc)
        if not crc:
            self.info.init_crc()

        if log:
            self.configure_logger()

    def configure_logger(self):
        self.logger = getLogger('process')

    @property
    def crc(self):
        return self.info.crc

    @property
    def name(self):
        return self.info.name

    @property
    def external_address(self):
        return self.info.external_address

    @property
    def process_index(self):
        return self.info.process_index

    def start(self):
        self.logger.info('Process started: {!s}'.format(self.info))

    def stop(self):
        self.logger.info('Process stopped: {!s}'.format(self.info))


class IOLoopProcess(BasicProcess):
    """
    Run process with zmq eventloop. Please, implement loop initialization in ther start method if you about to run this
    process as daemon.
    """

    def __init__(self, process_type, process_index=0, machine_id=DEFAULT_MACHINE_ID, crc=None, log=True,
                 ports=None, sockets=None, external_address=None, loop=None):
        super(IOLoopProcess, self).__init__(process_type, process_index=process_index, machine_id=machine_id,
                                            crc=crc, log=log, ports=ports, sockets=sockets,
                                            external_address=external_address)
        self._loop = loop

    @property
    def loop(self):
        if self._loop is None:
            install()
            self._loop = IOLoop.instance()
        return self._loop

    def start(self):
        super(IOLoopProcess, self).start()
        self.loop.start()

    def stop(self):
        self.loop.stop()
        super(IOLoopProcess, self).stop()


class IOLoopMixin():
    """Add IOLoop getter to object. Use it if you need separate instance of zmq eventloop in subprocess or thread.
    """
    _loop = None

    @property
    def loop(self):
        if self._loop is None:
            install()
            self._loop = IOLoop()
        return self._loop


class IOLoopThread(Thread, IOLoopMixin):
    pass


class IOLoopSubprocess(Process, IOLoopMixin):
    pass


class Settings(object):
    """Container to store and provide access for application settings.
    """

    properties = set()
    required_properties = set()
    private_properties = set()

    def __init__(self, settings=None, properties=(), required_properties=(), **kwargs):
        """
        :param settings:            Object where look for properties. If properties attribute is set, than only listed
                                    properties will be copied. You can provide dict or module as an argument.
                                    If required_properties is set, and settings does not contains any of
                                    listed properties, LookupError will be raised.
        :type settings:             dict or module.
        :param properties:          List of properties which should be copied to this container instance,
                                    during initialization, import or update. Also you can define properties as
                                    subclass' attribute.
        :type properties:           list or tuple or set.
        :param required_properties: List of properties which are required for this container instance. Also you can
                                    define required_properties as subclass' attribute.
        :type required_properties:  list or tuple or set.
        :param kwargs:              Provide additional properties through kwargs.
        """
        self._settings = {}
        if properties:
            self.properties = set(properties)
        if required_properties:
            self.required_properties = set(required_properties)
        if settings:
            self.update(settings)

    def __getattr__(self, item):
        return self._settings[item]

    def __getitem__(self, item):
        return self._settings[item]

    def parse_file(self, file_name):
        """Load settings from json or yaml file.

        :param file_name: path of the file to parse. path will be normalized, before loading.
        :type file_name: basestring
        :return:
        """
        with open(norm_path(file_name), 'rb') as f:
            settings = f.read()
        self.update(decode_data(settings, YAML))

    def import_file(self, file_name):
        """Load settings from python module.
        """
        settings = imp.load_source('_settings_importing', norm_path(file_name))
        self.update(settings)

    def filter_props(self, props):
        props = set(props)
        valid_props = self.properties | self.required_properties
        if valid_props:
            for prop in props:
                if prop in valid_props:
                    yield prop
        else:
            for prop in props:
                if not prop.startswith('_'):
                    yield prop

    def update(self, settings):
        """Copy properties to container from dict or module. If properties attribute set, only listed properties
        will be copied. If required_properties attribute set, and after update operation not all of listed properties
        set, LookupError will be raised.

        :param settings: object, where to look for properties.
        :type settings: dict or module
        :return: Settings container instance.
        :rtype Settings:
        :raise LookupError:
        """
        if isinstance(settings, ModuleType):
            for prop in self.filter_props(dir(settings)):
                self._settings[prop] = getattr(settings, prop)
        elif isinstance(settings, dict):
            for prop in self.filter_props(settings.keys()):
                self._settings[prop] = settings[prop]
        else:
            raise TypeError('dict or module required.')

        if self.required_properties:
            unset_but_required = self.required_properties - set(self._settings)
            if unset_but_required:
                raise LookupError('Not all of required properties set: {}'.format(unset_but_required))
        return self

    @property
    def dict(self):
        return self._settings

    def dump(self):
        d = dump_value(self._settings)
        for prop in d.keys():
            if prop in self.private_properties:
                del d[prop]
        return d


class CallbackWrapper(object):
    """Something similar to functools.partial, but also added a property to mark callback as executed.
    Note, that if you've provided args to both callback and wrapper, wrapper's args will be added at
    the end of callback args.
    """

    def __init__(self, handler, *args, **kwargs):
        self.done = False
        self.handler = handler
        self.args = args
        self.kwargs = kwargs
        self._hash = random_id()

    def __call__(self, *args, **kwargs):
        args = list(args) + list(self.args)
        kw = copy(self.kwargs)
        kw.update(kwargs)
        self.done = True
        self.handler(*args, **kwargs)

    def __hash__(self):
        return self._hash


def wrap_callback(handler, *args, **kwargs):
    """Decorate handler with this function to turn function or method to CallbackWrapper
    """
    return CallbackWrapper(handler, *args, **kwargs)