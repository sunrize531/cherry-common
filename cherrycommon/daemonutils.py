from daemon import DaemonContext
from daemon.pidfile import PIDLockFile
from lockfile import LockFailed
import sys

__author__ = 'sunrize'

def start_daemon(pidfile, process, **kwargs):
    if pidfile:
        pidfile = PIDLockFile(pidfile)
        try:
            pidfile.acquire(timeout=1.0)
            pidfile.release()
        except LockFailed:
            raise
    else:
        pidfile = None

    with DaemonContext(pidfile=pidfile, stdout=sys.stdout, stderr=sys.stderr, **kwargs):
        process.start()

def stop_daemon(pidfile):
    context = DaemonContext(pidfile=PIDLockFile(pidfile))
    context.close()