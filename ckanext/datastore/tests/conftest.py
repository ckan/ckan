# -*- coding: utf-8 -*-

import pytest
import ckanext.datastore.tests.helpers as test_helpers


@pytest.fixture
def clean_datastore(reset_db, reset_index):
    reset_db()
    reset_index()
    engine = test_helpers.db.get_write_engine()
    test_helpers.rebuild_all_dbs(
        test_helpers.orm.scoped_session(
            test_helpers.orm.sessionmaker(bind=engine)))
