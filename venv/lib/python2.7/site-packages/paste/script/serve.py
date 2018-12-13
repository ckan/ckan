from __future__ import print_function
# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# @@: This should be moved to paste.deploy
# For discussion of daemonizing:
#   http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/278731
# Code taken also from QP:
#   http://www.mems-exchange.org/software/qp/
#   From lib/site.py
import atexit
import errno
import logging
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from paste.deploy import loadapp, loadserver
from paste.script.command import Command, BadCommand


MAXFD = 1024

jython = sys.platform.startswith('java')

class DaemonizeException(Exception):
    pass


class ServeCommand(Command):

    min_args = 0
    usage = 'CONFIG_FILE [start|stop|restart|status] [var=value]'
    takes_config_file = 1
    summary = "Serve the described application"
    description = """\
    This command serves a web application that uses a paste.deploy
    configuration file for the server and application.

    If start/stop/restart is given, then --daemon is implied, and it will
    start (normal operation), stop (--stop-daemon), or do both.

    You can also include variable assignments like 'http_port=8080'
    and then use %(http_port)s in your config files.
    """

    # used by subclasses that configure apps and servers differently
    requires_config_file = True

    parser = Command.standard_parser(quiet=True)
    parser.add_option('-n', '--app-name',
                      dest='app_name',
                      metavar='NAME',
                      help="Load the named application (default main)")
    parser.add_option('-s', '--server',
                      dest='server',
                      metavar='SERVER_TYPE',
                      help="Use the named server.")
    parser.add_option('--server-name',
                      dest='server_name',
                      metavar='SECTION_NAME',
                      help="Use the named server as defined in the configuration file (default: main)")
    if hasattr(os, 'fork'):
        parser.add_option('--daemon',
                          dest="daemon",
                          action="store_true",
                          help="Run in daemon (background) mode")
    parser.add_option('--pid-file',
                      dest='pid_file',
                      metavar='FILENAME',
                      help="Save PID to file (default to paster.pid if running in daemon mode)")
    parser.add_option('--log-file',
                      dest='log_file',
                      metavar='LOG_FILE',
                      help="Save output to the given log file (redirects stdout)")
    parser.add_option('--reload',
                      dest='reload',
                      action='store_true',
                      help="Use auto-restart file monitor")
    parser.add_option('--reload-interval',
                      dest='reload_interval',
                      default=1,
                      help="Seconds between checking files (low number can cause significant CPU usage)")
    parser.add_option('--monitor-restart',
                      dest='monitor_restart',
                      action='store_true',
                      help="Auto-restart server if it dies")
    parser.add_option('--status',
                      action='store_true',
                      dest='show_status',
                      help="Show the status of the (presumably daemonized) server")


    if hasattr(os, 'setuid'):
        # I don't think these are available on Windows
        parser.add_option('--user',
                          dest='set_user',
                          metavar="USERNAME",
                          help="Set the user (usually only possible when run as root)")
        parser.add_option('--group',
                          dest='set_group',
                          metavar="GROUP",
                          help="Set the group (usually only possible when run as root)")

    parser.add_option('--stop-daemon',
                      dest='stop_daemon',
                      action='store_true',
                      help='Stop a daemonized server (given a PID file, or default paster.pid file)')

    if jython:
        parser.add_option('--disable-jython-reloader',
                          action='store_true',
                          dest='disable_jython_reloader',
                          help="Disable the Jython reloader")


    _scheme_re = re.compile(r'^[a-z][a-z]+:', re.I)

    default_verbosity = 1

    _reloader_environ_key = 'PYTHON_RELOADER_SHOULD_RUN'
    _monitor_environ_key = 'PASTE_MONITOR_SHOULD_RUN'

    possible_subcommands = ('start', 'stop', 'restart', 'status')
    def command(self):
        if self.options.stop_daemon:
            return self.stop_daemon()

        if not hasattr(self.options, 'set_user'):
            # Windows case:
            self.options.set_user = self.options.set_group = None
        # @@: Is this the right stage to set the user at?
        self.change_user_group(
            self.options.set_user, self.options.set_group)

        if self.requires_config_file:
            if not self.args:
                raise BadCommand('You must give a config file')
            app_spec = self.args[0]
            if (len(self.args) > 1
                and self.args[1] in self.possible_subcommands):
                cmd = self.args[1]
                restvars = self.args[2:]
            else:
                cmd = None
                restvars = self.args[1:]
        else:
            app_spec = ""
            if (self.args
                and self.args[0] in self.possible_subcommands):
                cmd = self.args[0]
                restvars = self.args[1:]
            else:
                cmd = None
                restvars = self.args[:]

        if (getattr(self.options, 'daemon', False)
            and getattr(self.options, 'reload', False)):
            raise BadCommand('The --daemon and --reload options may not be used together')

        jython_monitor = False
        if self.options.reload:
            if jython and not self.options.disable_jython_reloader:
                # JythonMonitor raises the special SystemRestart
                # exception that'll cause the Jython interpreter to
                # reload in the existing Java process (avoiding
                # subprocess startup time)
                try:
                    from paste.reloader import JythonMonitor
                except ImportError:
                    pass
                else:
                    jython_monitor = JythonMonitor(poll_interval=int(
                            self.options.reload_interval))
                    if self.requires_config_file:
                        jython_monitor.watch_file(self.args[0])

            if not jython_monitor:
                if os.environ.get(self._reloader_environ_key):
                    from paste import reloader
                    if self.verbose > 1:
                        print('Running reloading file monitor')
                    reloader.install(int(self.options.reload_interval))
                    if self.requires_config_file:
                        reloader.watch_file(self.args[0])
                else:
                    return self.restart_with_reloader()

        if cmd not in (None, 'start', 'stop', 'restart', 'status'):
            raise BadCommand(
                'Error: must give start|stop|restart (not %s)' % cmd)

        if cmd == 'status' or self.options.show_status:
            return self.show_status()

        if cmd == 'restart' or cmd == 'stop':
            result = self.stop_daemon()
            if result:
                if cmd == 'restart':
                    print("Could not stop daemon; aborting")
                else:
                    print("Could not stop daemon")
                return result
            if cmd == 'stop':
                return result
            self.options.daemon = True

        if cmd == 'start':
            self.options.daemon = True

        app_name = self.options.app_name
        vars = self.parse_vars(restvars)
        if not self._scheme_re.search(app_spec):
            app_spec = 'config:' + app_spec
        server_name = self.options.server_name
        if self.options.server:
            server_spec = 'egg:PasteScript'
            assert server_name is None
            server_name = self.options.server
        else:
            server_spec = app_spec
        base = os.getcwd()

        if getattr(self.options, 'daemon', False):
            if not self.options.pid_file:
                self.options.pid_file = 'paster.pid'
            if not self.options.log_file:
                self.options.log_file = 'paster.log'

        # Ensure the log file is writeable
        if self.options.log_file:
            try:
                writeable_log_file = open(self.options.log_file, 'a')
            except IOError as ioe:
                msg = 'Error: Unable to write to log file: %s' % ioe
                raise BadCommand(msg)
            writeable_log_file.close()

        # Ensure the pid file is writeable
        if self.options.pid_file:
            try:
                writeable_pid_file = open(self.options.pid_file, 'a')
            except IOError as ioe:
                msg = 'Error: Unable to write to pid file: %s' % ioe
                raise BadCommand(msg)
            writeable_pid_file.close()

        if getattr(self.options, 'daemon', False):
            try:
                self.daemonize()
            except DaemonizeException as ex:
                if self.verbose > 0:
                    print(str(ex))
                return

        if (self.options.monitor_restart
            and not os.environ.get(self._monitor_environ_key)):
            return self.restart_with_monitor()

        if self.options.pid_file:
            self.record_pid(self.options.pid_file)

        if self.options.log_file:
            stdout_log = LazyWriter(self.options.log_file, 'a')
            sys.stdout = stdout_log
            sys.stderr = stdout_log
            logging.basicConfig(stream=stdout_log)

        log_fn = app_spec
        if log_fn.startswith('config:'):
            log_fn = app_spec[len('config:'):]
        elif log_fn.startswith('egg:'):
            log_fn = None
        if log_fn:
            log_fn = os.path.join(base, log_fn)
            self.logging_file_config(log_fn)

        try:
            server = self.loadserver(server_spec, name=server_name,
                                     relative_to=base, global_conf=vars)
            app = self.loadapp(app_spec, name=app_name,
                               relative_to=base, global_conf=vars)
        except SyntaxError as e:
            if self.options.reload and os.environ.get(self._reloader_environ_key):
                traceback.print_exc()
                reloader.watch_file(e.filename)
                while True:
                    time.sleep(60*60)
            else:
                raise

        if self.verbose > 0:
            if hasattr(os, 'getpid'):
                msg = 'Starting server in PID %i.' % os.getpid()
            else:
                msg = 'Starting server.'
            print(msg)

        def serve():
            try:
                server(app)
            except (SystemExit, KeyboardInterrupt) as e:
                if self.verbose > 1:
                    raise
                if str(e):
                    msg = ' '+str(e)
                else:
                    msg = ''
                print('Exiting%s (-v to see traceback)' % msg)

        if jython_monitor:
            # JythonMonitor has to be ran from the main thread
            threading.Thread(target=serve).start()
            print('Starting Jython file monitor')
            jython_monitor.periodic_reload()
        else:
            serve()

    def loadserver(self, server_spec, name, relative_to, **kw):
            return loadserver(
                server_spec, name=name,
                relative_to=relative_to, **kw)

    def loadapp(self, app_spec, name, relative_to, **kw):
            return loadapp(
                app_spec, name=name, relative_to=relative_to,
                **kw)

    def daemonize(self):
        pid = live_pidfile(self.options.pid_file)
        if pid:
            raise DaemonizeException(
                "Daemon is already running (PID: %s from PID file %s)"
                % (pid, self.options.pid_file))

        if self.verbose > 0:
            print('Entering daemon mode')
        pid = os.fork()
        if pid:
            # The forked process also has a handle on resources, so we
            # *don't* want proper termination of the process, we just
            # want to exit quick (which os._exit() does)
            os._exit(0)
        # Make this the session leader
        os.setsid()
        # Fork again for good measure!
        pid = os.fork()
        if pid:
            os._exit(0)

        # @@: Should we set the umask and cwd now?

        import resource  # Resource usage information.
        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if (maxfd == resource.RLIM_INFINITY):
            maxfd = MAXFD
        # Iterate through and close all file descriptors.
        for fd in range(0, maxfd):
            try:
                os.close(fd)
            except OSError:  # ERROR, fd wasn't open to begin with (ignored)
                pass

        if (hasattr(os, "devnull")):
            REDIRECT_TO = os.devnull
        else:
            REDIRECT_TO = "/dev/null"
        os.open(REDIRECT_TO, os.O_RDWR)  # standard input (0)
        # Duplicate standard input to standard output and standard error.
        os.dup2(0, 1)  # standard output (1)
        os.dup2(0, 2)  # standard error (2)

    def record_pid(self, pid_file):
        pid = os.getpid()
        if self.verbose > 1:
            print('Writing PID %s to %s' % (pid, pid_file))
        f = open(pid_file, 'w')
        f.write(str(pid))
        f.close()
        atexit.register(_remove_pid_file, pid, pid_file, self.verbose)

    def stop_daemon(self):
        pid_file = self.options.pid_file or 'paster.pid'
        if not os.path.exists(pid_file):
            print('No PID file exists in %s' % pid_file)
            return 1
        pid = read_pidfile(pid_file)
        if not pid:
            print("Not a valid PID file in %s" % pid_file)
            return 1
        pid = live_pidfile(pid_file)
        if not pid:
            print("PID in %s is not valid (deleting)" % pid_file)
            try:
                os.unlink(pid_file)
            except (OSError, IOError) as e:
                print("Could not delete: %s" % e)
                return 2
            return 1
        for j in range(10):
            if not live_pidfile(pid_file):
                break
            import signal
            os.kill(pid, signal.SIGINT)
            time.sleep(1)
        for j in range(10):
            if not live_pidfile(pid_file):
                break
            import signal
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
        else:
            print("failed to kill web process %s" % pid)
            return 3
        if os.path.exists(pid_file):
            os.unlink(pid_file)
        return 0

    def show_status(self):
        pid_file = self.options.pid_file or 'paster.pid'
        if not os.path.exists(pid_file):
            print('No PID file %s' % pid_file)
            return 1
        pid = read_pidfile(pid_file)
        if not pid:
            print('No PID in file %s' % pid_file)
            return 1
        pid = live_pidfile(pid_file)
        if not pid:
            print('PID %s in %s is not running' % (pid, pid_file))
            return 1
        print('Server running in PID %s' % pid)
        return 0

    def restart_with_reloader(self):
        self.restart_with_monitor(reloader=True)

    def restart_with_monitor(self, reloader=False):
        if self.verbose > 0:
            if reloader:
                print('Starting subprocess with file monitor')
            else:
                print('Starting subprocess with monitor parent')
        while 1:
            args = [self.quote_first_command_arg(sys.executable)] + sys.argv
            new_environ = os.environ.copy()
            if reloader:
                new_environ[self._reloader_environ_key] = 'true'
            else:
                new_environ[self._monitor_environ_key] = 'true'
            proc = None
            try:
                try:
                    _turn_sigterm_into_systemexit()
                    proc = subprocess.Popen(args, env=new_environ)
                    exit_code = proc.wait()
                    proc = None
                except KeyboardInterrupt:
                    print('^C caught in monitor process')
                    if self.verbose > 1:
                        raise
                    return 1
            finally:
                if (proc is not None
                    and hasattr(os, 'kill')):
                    import signal
                    try:
                        os.kill(proc.pid, signal.SIGTERM)
                    except (OSError, IOError):
                        pass
            if reloader:
                # Reloader always exits with code 3; but if we are
                # a monitor, any exit code will restart
                if exit_code != 3:
                    return exit_code
            if self.verbose > 0:
                print('-'*20, 'Restarting', '-'*20)

    def change_user_group(self, user, group):
        if not user and not group:
            return
        import pwd, grp
        uid = gid = None
        if group:
            try:
                gid = int(group)
                group = grp.getgrgid(gid).gr_name
            except ValueError:
                import grp
                try:
                    entry = grp.getgrnam(group)
                except KeyError:
                    raise BadCommand(
                        "Bad group: %r; no such group exists" % group)
                gid = entry.gr_gid
        try:
            uid = int(user)
            user = pwd.getpwuid(uid).pw_name
        except ValueError:
            try:
                entry = pwd.getpwnam(user)
            except KeyError:
                raise BadCommand(
                    "Bad username: %r; no such user exists" % user)
            if not gid:
                gid = entry.pw_gid
            uid = entry.pw_uid
        if self.verbose > 0:
            print('Changing user to %s:%s (%s:%s)' % (
                user, group or '(unknown)', uid, gid))
        if hasattr(os, 'initgroups'):
            os.initgroups(user, gid)
        else:
            os.setgroups([e.gr_gid for e in grp.getgrall()
                          if user in e.gr_mem] + [gid])
        if gid:
            os.setgid(gid)
        if uid:
            os.setuid(uid)

class LazyWriter(object):

    """
    File-like object that opens a file lazily when it is first written
    to.
    """

    def __init__(self, filename, mode='w'):
        self.filename = filename
        self.fileobj = None
        self.lock = threading.Lock()
        self.mode = mode

    def open(self):
        if self.fileobj is None:
            self.lock.acquire()
            try:
                if self.fileobj is None:
                    self.fileobj = open(self.filename, self.mode)
            finally:
                self.lock.release()
        return self.fileobj

    def write(self, text):
        fileobj = self.open()
        fileobj.write(text)
        fileobj.flush()

    def writelines(self, text):
        fileobj = self.open()
        fileobj.writelines(text)
        fileobj.flush()

    def flush(self):
        self.open().flush()

def live_pidfile(pidfile):
    """(pidfile:str) -> int | None
    Returns an int found in the named file, if there is one,
    and if there is a running process with that process id.
    Return None if no such process exists.
    """
    pid = read_pidfile(pidfile)
    if pid:
        try:
            os.kill(int(pid), 0)
            return pid
        except OSError as e:
            if e.errno == errno.EPERM:
                return pid
    return None

def read_pidfile(filename):
    if os.path.exists(filename):
        try:
            f = open(filename)
            content = f.read()
            f.close()
            return int(content.strip())
        except (ValueError, IOError):
            return None
    else:
        return None

def _remove_pid_file(written_pid, filename, verbosity):
    current_pid = os.getpid()
    if written_pid != current_pid:
        # A forked process must be exiting, not the process that
        # wrote the PID file
        return
    if not os.path.exists(filename):
        return
    f = open(filename)
    content = f.read().strip()
    f.close()
    try:
        pid_in_file = int(content)
    except ValueError:
        pass
    else:
        if pid_in_file != current_pid:
            print("PID file %s contains %s, not expected PID %s" % (
                filename, pid_in_file, current_pid))
            return
    if verbosity > 0:
        print("Removing PID file %s" % filename)
    try:
        os.unlink(filename)
        return
    except OSError as e:
        # Record, but don't give traceback
        print("Cannot remove PID file: %s" % e)
    # well, at least lets not leave the invalid PID around...
    try:
        f = open(filename, 'w')
        f.write('')
        f.close()
    except OSError as e:
        print('Stale PID left in file: %s (%e)' % (filename, e))
    else:
        print('Stale PID removed')


def ensure_port_cleanup(bound_addresses, maxtries=30, sleeptime=2):
    """
    This makes sure any open ports are closed.

    Does this by connecting to them until they give connection
    refused.  Servers should call like::

        import paste.script
        ensure_port_cleanup([80, 443])
    """
    atexit.register(_cleanup_ports, bound_addresses, maxtries=maxtries,
                    sleeptime=sleeptime)

def _cleanup_ports(bound_addresses, maxtries=30, sleeptime=2):
    # Wait for the server to bind to the port.
    import socket
    import errno
    for bound_address in bound_addresses:
        for attempt in range(maxtries):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect(bound_address)
            except socket.error as e:
                if e.args[0] != errno.ECONNREFUSED:
                    raise
                break
            else:
                time.sleep(sleeptime)
        else:
            raise SystemExit('Timeout waiting for port.')
        sock.close()

def _turn_sigterm_into_systemexit():
    """
    Attempts to turn a SIGTERM exception into a SystemExit exception.
    """
    try:
        import signal
    except ImportError:
        return
    def handle_term(signo, frame):
        raise SystemExit
    signal.signal(signal.SIGTERM, handle_term)
