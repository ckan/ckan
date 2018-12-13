# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
from cStringIO import StringIO
import traceback
import threading
import pdb
import sys

exec_lock = threading.Lock()

class EvalContext(object):

    """
    Class that represents a interactive interface.  It has its own
    namespace.  Use eval_context.exec_expr(expr) to run commands; the
    output of those commands is returned, as are print statements.

    This is essentially what doctest does, and is taken directly from
    doctest.
    """

    def __init__(self, namespace, globs):
        self.namespace = namespace
        self.globs = globs

    def exec_expr(self, s):
        out = StringIO()
        exec_lock.acquire()
        save_stdout = sys.stdout
        try:
            debugger = _OutputRedirectingPdb(save_stdout)
            debugger.reset()
            pdb.set_trace = debugger.set_trace
            sys.stdout = out
            try:
                code = compile(s, '<web>', "single", 0, 1)
                exec code in self.namespace, self.globs
                debugger.set_continue()
            except KeyboardInterrupt:
                raise
            except:
                traceback.print_exc(file=out)
                debugger.set_continue()
        finally:
            sys.stdout = save_stdout
            exec_lock.release()
        return out.getvalue()

# From doctest
class _OutputRedirectingPdb(pdb.Pdb):
    """
    A specialized version of the python debugger that redirects stdout
    to a given stream when interacting with the user.  Stdout is *not*
    redirected when traced code is executed.
    """
    def __init__(self, out):
        self.__out = out
        pdb.Pdb.__init__(self)

    def trace_dispatch(self, *args):
        # Redirect stdout to the given stream.
        save_stdout = sys.stdout
        sys.stdout = self.__out
        # Call Pdb's trace dispatch method.
        try:
            return pdb.Pdb.trace_dispatch(self, *args)
        finally:
            sys.stdout = save_stdout
