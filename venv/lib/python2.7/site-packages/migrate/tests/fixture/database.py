#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import sys

import six
from decorator import decorator

from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import create_session
from sqlalchemy.pool import StaticPool

from migrate.changeset.schema import ColumnDelta
from migrate.versioning.util import Memoize

from migrate.tests.fixture.base import Base
from migrate.tests.fixture.pathed import Pathed


log = logging.getLogger(__name__)

@Memoize
def readurls():
    """read URLs from config file return a list"""
    # TODO: remove tmpfile since sqlite can store db in memory
    filename = 'test_db.cfg' if six.PY2 else "test_db_py3.cfg"
    ret = list()
    tmpfile = Pathed.tmp()
    fullpath = os.path.join(os.curdir, filename)

    try:
        fd = open(fullpath)
    except IOError:
        raise IOError("""You must specify the databases to use for testing!
Copy %(filename)s.tmpl to %(filename)s and edit your database URLs.""" % locals())

    for line in fd:
        if line.startswith('#'):
            continue
        line = line.replace('__tmp__', tmpfile).strip()
        ret.append(line)
    fd.close()
    return ret

def is_supported(url, supported, not_supported):
    db = url.split(':', 1)[0]

    if supported is not None:
        if isinstance(supported, six.string_types):
            return supported == db
        else:
            return db in supported
    elif not_supported is not None:
        if isinstance(not_supported, six.string_types):
            return not_supported != db
        else:
            return not (db in not_supported)
    return True


def usedb(supported=None, not_supported=None):
    """Decorates tests to be run with a database connection
    These tests are run once for each available database

    @param supported: run tests for ONLY these databases
    @param not_supported: run tests for all databases EXCEPT these

    If both supported and not_supported are empty, all dbs are assumed
    to be supported
    """
    if supported is not None and not_supported is not None:
        raise AssertionError("Can't specify both supported and not_supported in fixture.db()")

    urls = readurls()
    my_urls = [url for url in urls if is_supported(url, supported, not_supported)]

    @decorator
    def dec(f, self, *a, **kw):
        failed_for = []
        fail = False
        for url in my_urls:
            try:
                log.debug("Running test with engine %s", url)
                try:
                    self._setup(url)
                except sa_exc.OperationalError:
                    log.info('Backend %s is not available, skip it', url)
                    continue
                except Exception as e:
                    raise RuntimeError('Exception during _setup(): %r' % e)

                try:
                    f(self, *a, **kw)
                finally:
                    try:
                        self._teardown()
                    except Exception as e:
                        raise RuntimeError('Exception during _teardown(): %r' % e)
            except Exception:
                failed_for.append(url)
                fail = sys.exc_info()
        for url in failed_for:
            log.error('Failed for %s', url)
        if fail:
            # cause the failure :-)
            six.reraise(*fail)
    return dec


class DB(Base):
    # Constants: connection level
    NONE = 0  # No connection; just set self.url
    CONNECT = 1   # Connect; no transaction
    TXN = 2   # Everything in a transaction

    level = TXN

    def _engineInfo(self, url=None):
        if url is None:
            url = self.url
        return url

    def _setup(self, url):
        self._connect(url)
        # make sure there are no tables lying around
        meta = MetaData(self.engine)
        meta.reflect()
        meta.drop_all()

    def _teardown(self):
        self._disconnect()

    def _connect(self, url):
        self.url = url
        # TODO: seems like 0.5.x branch does not work with engine.dispose and staticpool
        #self.engine = create_engine(url, echo=True, poolclass=StaticPool)
        self.engine = create_engine(url, echo=True)
        # silence the logger added by SA, nose adds its own!
        logging.getLogger('sqlalchemy').handlers=[]
        self.meta = MetaData(bind=self.engine)
        if self.level < self.CONNECT:
            return
        #self.session = create_session(bind=self.engine)
        if self.level < self.TXN:
            return
        #self.txn = self.session.begin()

    def _disconnect(self):
        if hasattr(self, 'txn'):
            self.txn.rollback()
        if hasattr(self, 'session'):
            self.session.close()
        #if hasattr(self,'conn'):
        #    self.conn.close()
        self.engine.dispose()

    def _supported(self, url):
        db = url.split(':',1)[0]
        func = getattr(self, self._TestCase__testMethodName)
        if hasattr(func, 'supported'):
            return db in func.supported
        if hasattr(func, 'not_supported'):
            return not (db in func.not_supported)
        # Neither list assigned; assume all are supported
        return True

    def _not_supported(self, url):
        return not self._supported(url)

    def _select_row(self):
        """Select rows, used in multiple tests"""
        return self.table.select().execution_options(
            autocommit=True).execute().fetchone()

    def refresh_table(self, name=None):
        """Reload the table from the database
        Assumes we're working with only a single table, self.table, and
        metadata self.meta

        Working w/ multiple tables is not possible, as tables can only be
        reloaded with meta.clear()
        """
        if name is None:
            name = self.table.name
        self.meta.clear()
        self.table = Table(name, self.meta, autoload=True)

    def compare_columns_equal(self, columns1, columns2, ignore=None):
        """Loop through all columns and compare them"""
        def key(column):
            return column.name
        for c1, c2 in zip(sorted(columns1, key=key), sorted(columns2, key=key)):
            diffs = ColumnDelta(c1, c2).diffs
            if ignore:
                for key in ignore:
                    diffs.pop(key, None)
            if diffs:
                self.fail("Comparing %s to %s failed: %s" % (columns1, columns2, diffs))

# TODO: document engine.dispose and write tests
