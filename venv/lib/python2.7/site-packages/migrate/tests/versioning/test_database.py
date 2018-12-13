from sqlalchemy import select, text
from migrate.tests import fixture

class TestConnect(fixture.DB):
    level=fixture.DB.TXN

    @fixture.usedb()
    def test_connect(self):
        """Connect to the database successfully"""
        # Connection is done in fixture.DB setup; make sure we can do stuff
        self.engine.execute(
            select([text('42')])
        )
