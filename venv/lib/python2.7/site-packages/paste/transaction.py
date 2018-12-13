# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
Middleware related to transactions and database connections.

At this time it is very basic; but will eventually sprout all that
two-phase commit goodness that I don't need.

.. note::

   This is experimental, and will change in the future.
"""
from paste.httpexceptions import HTTPException
from wsgilib import catch_errors

class TransactionManagerMiddleware(object):

    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        environ['paste.transaction_manager'] = manager = Manager()
        # This makes sure nothing else traps unexpected exceptions:
        environ['paste.throw_errors'] = True
        return catch_errors(self.application, environ, start_response,
                            error_callback=manager.error,
                            ok_callback=manager.finish)

class Manager(object):

    def __init__(self):
        self.aborted = False
        self.transactions = []

    def abort(self):
        self.aborted = True

    def error(self, exc_info):
        self.aborted = True
        self.finish()

    def finish(self):
        for trans in self.transactions:
            if self.aborted:
                trans.rollback()
            else:
                trans.commit()


class ConnectionFactory(object):
    """
    Provides a callable interface for connecting to ADBAPI databases in
    a WSGI style (using the environment).  More advanced connection
    factories might use the REMOTE_USER and/or other environment
    variables to make the connection returned depend upon the request.
    """
    def __init__(self, module, *args, **kwargs):
        #assert getattr(module,'threadsaftey',0) > 0
        self.module = module
        self.args = args
        self.kwargs = kwargs

        # deal with database string quoting issues
        self.quote = lambda s: "'%s'" % s.replace("'","''")
        if hasattr(self.module,'PgQuoteString'):
            self.quote = self.module.PgQuoteString

    def __call__(self, environ=None):
        conn = self.module.connect(*self.args, **self.kwargs)
        conn.__dict__['module'] = self.module
        conn.__dict__['quote'] = self.quote
        return conn

def BasicTransactionHandler(application, factory):
    """
    Provides a simple mechanism for starting a transaction based on the
    factory; and for either committing or rolling back the transaction
    depending on the result.  It checks for the response's current
    status code either through the latest call to start_response; or
    through a HTTPException's code.  If it is a 100, 200, or 300; the
    transaction is committed; otherwise it is rolled back.
    """
    def basic_transaction(environ, start_response):
        conn = factory(environ)
        environ['paste.connection'] = conn
        should_commit = [500]
        def finalizer(exc_info=None):
            if exc_info:
                if isinstance(exc_info[1], HTTPException):
                    should_commit.append(exc_info[1].code)
            if should_commit.pop() < 400:
                conn.commit()
            else:
                try:
                    conn.rollback()
                except:
                    # TODO: check if rollback has already happened
                    return
            conn.close()
        def basictrans_start_response(status, headers, exc_info = None):
            should_commit.append(int(status.split(" ")[0]))
            return start_response(status, headers, exc_info)
        return catch_errors(application, environ, basictrans_start_response,
                            finalizer, finalizer)
    return basic_transaction

__all__ = ['ConnectionFactory', 'BasicTransactionHandler']

if '__main__' == __name__ and False:
    from pyPgSQL import PgSQL
    factory = ConnectionFactory(PgSQL, database="testing")
    conn = factory()
    curr = conn.cursor()
    curr.execute("SELECT now(), %s" % conn.quote("B'n\\'gles"))
    (time, bing) = curr.fetchone()
    print bing, time

