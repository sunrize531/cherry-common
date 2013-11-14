from daemon import DaemonContext
from daemon.pidfile import PIDLockFile
from lockfile import LockFailed
from lockfile.pidlockfile import read_pid_from_pidfile
import sys
import os
import signal


def start_daemon(pidfile, process, stdout=None, stderr=None, **kwargs):
    if pidfile:
        pidfile = PIDLockFile(pidfile)
        try:
            pidfile.acquire(timeout=1.0)
            pidfile.release()
        except LockFailed:
            raise
    else:
        pidfile = None

    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    with DaemonContext(pidfile=pidfile, stdout=stdout, stderr=stderr, **kwargs):
        process.start()


def stop_daemon(pidfile):
    pid = read_pid_from_pidfile(pidfile)
    os.kill(pid, signal.SIGKILL)
    os.unlink(pidfile)