import atexit
from logging import getLogger
from signal import SIGTERM
import os
import zlib
import sys
import time
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
                 ports=None, external_address=None):
        self.__class__._instance = self
        self.ports = ports or {}
        self.info = ProcessInfo(process_type, process_index=process_index, ports=self.ports,
            external_address=external_address, crc=crc)
        if not crc:
            self.info.init_crc()
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
    Run process with zmq eventloop.
    """
    def __init__(self, process_type, process_index=0, crc=None, log=True,
        ports=None, external_address=None, loop=None):
        super(IOLoopProcess, self).__init__(process_type, process_index, crc, log, ports, external_address)
        if loop is None:
            install()
            self.loop = IOLoop.instance()
        else:
            self.loop = loop

    def start(self):
        super(IOLoopProcess, self).start()
        self.loop.start()

    def stop(self):
        self.loop.stop()
        super(IOLoopProcess, self).stop()

class DaemonMixin(object):
    """
    Mixin class for turning BasicProcess subclass into unix daemon. Based on Sander Marechal implementation.
    """
    pidfile = None
    stdin = '/dev/null'
    stdout = '/dev/null'
    stderr = '/dev/null'

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("Fork failed: {} ({})\n".format(e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("Fork failed: {} ({})\n".format(e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile, 'w+').write("{}\n".format(pid))

    def delpid(self):
        os.remove(self.pidfile)

    def start_daemon(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile {} already exist. Daemon already running?\n"
            sys.stderr.write(message.format(self.pidfile))
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.start()

    def stop_daemon(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile, 'r')
        except IOError:
            pid = None
        else:
            pid = int(pf.read().strip())
            pf.close()

        if not pid:
            message = 'Pidfile {} does not exist. Daemon not running?\n'
            sys.stderr.write(message.format(self.pidfile))
            return # not an error in a restart

        sys.stdout.write('Stopping daemon with pid {}'.format(pid))

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)
