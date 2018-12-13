#!/usr/bin/env python

# test_green.py - unit test for async wait callback
#
# Copyright (C) 2010-2011 Daniele Varrazzo  <daniele.varrazzo@gmail.com>
#
# psycopg2 is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# In addition, as a special exception, the copyright holders give
# permission to link this program with the OpenSSL library (or with
# modified versions of OpenSSL that use the same license as OpenSSL),
# and distribute linked combinations including the two.
#
# You must obey the GNU Lesser General Public License in all respects for
# all of the code used other than OpenSSL.
#
# psycopg2 is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.

import unittest
import psycopg2
import psycopg2.extensions
import psycopg2.extras

from testutils import ConnectingTestCase, slow


class ConnectionStub(object):
    """A `connection` wrapper allowing analysis of the `poll()` calls."""
    def __init__(self, conn):
        self.conn = conn
        self.polls = []

    def fileno(self):
        return self.conn.fileno()

    def poll(self):
        rv = self.conn.poll()
        self.polls.append(rv)
        return rv


class GreenTestCase(ConnectingTestCase):
    def setUp(self):
        self._cb = psycopg2.extensions.get_wait_callback()
        psycopg2.extensions.set_wait_callback(psycopg2.extras.wait_select)
        ConnectingTestCase.setUp(self)

    def tearDown(self):
        ConnectingTestCase.tearDown(self)
        psycopg2.extensions.set_wait_callback(self._cb)

    def set_stub_wait_callback(self, conn):
        stub = ConnectionStub(conn)
        psycopg2.extensions.set_wait_callback(
            lambda conn: psycopg2.extras.wait_select(stub))
        return stub

    @slow
    def test_flush_on_write(self):
        # a very large query requires a flush loop to be sent to the backend
        conn = self.conn
        stub = self.set_stub_wait_callback(conn)
        curs = conn.cursor()
        for mb in 1, 5, 10, 20, 50:
            size = mb * 1024 * 1024
            del stub.polls[:]
            curs.execute("select %s;", ('x' * size,))
            self.assertEqual(size, len(curs.fetchone()[0]))
            if stub.polls.count(psycopg2.extensions.POLL_WRITE) > 1:
                return

        # This is more a testing glitch than an error: it happens
        # on high load on linux: probably because the kernel has more
        # buffers ready. A warning may be useful during development,
        # but an error is bad during regression testing.
        import warnings
        warnings.warn("sending a large query didn't trigger block on write.")

    def test_error_in_callback(self):
        # behaviour changed after issue #113: if there is an error in the
        # callback for the moment we don't have a way to reset the connection
        # without blocking (ticket #113) so just close it.
        conn = self.conn
        curs = conn.cursor()
        curs.execute("select 1")  # have a BEGIN
        curs.fetchone()

        # now try to do something that will fail in the callback
        psycopg2.extensions.set_wait_callback(lambda conn: 1 // 0)
        self.assertRaises(ZeroDivisionError, curs.execute, "select 2")

        self.assert_(conn.closed)

    def test_dont_freak_out(self):
        # if there is an error in a green query, don't freak out and close
        # the connection
        conn = self.conn
        curs = conn.cursor()
        self.assertRaises(psycopg2.ProgrammingError,
            curs.execute, "select the unselectable")

        # check that the connection is left in an usable state
        self.assert_(not conn.closed)
        conn.rollback()
        curs.execute("select 1")
        self.assertEqual(curs.fetchone()[0], 1)


class CallbackErrorTestCase(ConnectingTestCase):
    def setUp(self):
        self._cb = psycopg2.extensions.get_wait_callback()
        psycopg2.extensions.set_wait_callback(self.crappy_callback)
        ConnectingTestCase.setUp(self)
        self.to_error = None

    def tearDown(self):
        ConnectingTestCase.tearDown(self)
        psycopg2.extensions.set_wait_callback(self._cb)

    def crappy_callback(self, conn):
        """green callback failing after `self.to_error` time it is called"""
        import select
        from psycopg2.extensions import POLL_OK, POLL_READ, POLL_WRITE

        while 1:
            if self.to_error is not None:
                self.to_error -= 1
                if self.to_error <= 0:
                    raise ZeroDivisionError("I accidentally the connection")
            try:
                state = conn.poll()
                if state == POLL_OK:
                    break
                elif state == POLL_READ:
                    select.select([conn.fileno()], [], [])
                elif state == POLL_WRITE:
                    select.select([], [conn.fileno()], [])
                else:
                    raise conn.OperationalError("bad state from poll: %s" % state)
            except KeyboardInterrupt:
                conn.cancel()
                # the loop will be broken by a server error
                continue

    def test_errors_on_connection(self):
        # Test error propagation in the different stages of the connection
        for i in range(100):
            self.to_error = i
            try:
                self.connect()
            except ZeroDivisionError:
                pass
            else:
                # We managed to connect
                return

        self.fail("you should have had a success or an error by now")

    def test_errors_on_query(self):
        for i in range(100):
            self.to_error = None
            cnn = self.connect()
            cur = cnn.cursor()
            self.to_error = i
            try:
                cur.execute("select 1")
                cur.fetchone()
            except ZeroDivisionError:
                pass
            else:
                # The query completed
                return

        self.fail("you should have had a success or an error by now")

    def test_errors_named_cursor(self):
        for i in range(100):
            self.to_error = None
            cnn = self.connect()
            cur = cnn.cursor('foo')
            self.to_error = i
            try:
                cur.execute("select 1")
                cur.fetchone()
            except ZeroDivisionError:
                pass
            else:
                # The query completed
                return

        self.fail("you should have had a success or an error by now")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == "__main__":
    unittest.main()
