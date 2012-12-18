import os
import zlib
from cherrycommon.timeutils import milliseconds

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
                 ports=None, external_address=None, pid=None, crc=None):
        self.process_type = process_type
        self.process_index = process_index
        self.machine_id = machine_id
        self.pid = pid or os.getpid()
        self.ports = ports or {}
        self._crc = crc
        if external_address:
            self.external_address = external_address

    _process_name_pattern = '{process_type}@{machine_id}.{index:02d}'
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

class BasicProcess(object):
    _instance = None
    @classmethod
    def get_instance(cls, *args, **kwargs):
        if cls._instance is None:
            instance = cls.__new__(cls)
            instance.__init__(*args, **kwargs)
        return cls._instance

    def __init__(self, process_type, process_index=0, crc=None, log=True,
                 ports=None, external_address=None, loop=None):
        self.__class__._instance = self
        self.ports = ports or {}
        self.info = ProcessInfo(process_type, process_index=process_index, ports=self.ports,
            external_address=external_address, crc=crc)
        if not crc:
            self.info.init_crc()

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
        pass

    def stop(self):
        pass