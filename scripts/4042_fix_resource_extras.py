# encoding: utf-8
u'''
This script fixes resource extras affected by a bug introduced in #3425 and
raised in #4042

#3422 (implemented in #3425) introduced a major bug where if a resource was
deleted and the DataStore was active, extras from all resources on the site
where changed. This is now fixed starting from version 2.7.3 but if your
database is already affected you will need to run this script to restore
the extras to their previous state.

Remember, you only need to run this script if all the following are true:

     1. You are currently running CKAN 2.7.0 or 2.7.2, and
     2. You have enabled the DataStore, and
     3. One or more resources with data on the DataStore have been deleted
        (or your suspect they might have been)

If all these are true you can run this script like this:

    python fix_resource_extras.py -c path/to/the/ini/file

As ever when making changes in the database please do a backup before running
this script.

Note that it requires SQLAlchemy, so you should run it with the virtualenv
activated.
'''

import json
from six.moves.configparser import ConfigParser
from argparse import ArgumentParser
from six.moves import input
from sqlalchemy import create_engine
from sqlalchemy.sql import text

config = ConfigParser()
parser = ArgumentParser()
parser.add_argument(
    u'-c', u'--config', help=u'Configuration file', required=True)

SIMPLE_Q = (
    u"SELECT id, r.extras, rr.extras revision "
    u"FROM resource r JOIN resource_revision rr "
    u"USING(id, revision_id) WHERE r.extras != rr.extras"
)
UPDATE_Q = text(u"UPDATE resource SET extras = :extras WHERE id = :id")


def main():
    args = parser.parse_args()
    config.read(args.config)
    engine = create_engine(config.get(u'app:main', u'sqlalchemy.url'))
    records = engine.execute(SIMPLE_Q)

    total = records.rowcount
    print(u'Found {} datasets with inconsistent extras.'.format(total))

    skip_confirmation = False
    i = 0

    while True:
        row = records.fetchone()
        if row is None:
            break

        id, current, rev = row
        current_json = json.loads(current)
        rev_json = json.loads(rev)
        if (dict(current_json, datastore_active=None) ==
                dict(rev_json, datastore_active=None)):
            continue
        i += 1

        print(u'[{:{}}/{}] Resource <{}>'.format(
            i, len(str(total)), total, id))
        print(u'\tCurrent extras state in DB: {}'.format(current))
        print(u'\tAccording to the revision:  {}'.format(rev))
        if not skip_confirmation:
            choice = input(
                u'\tRequired action: '
                u'y - rewrite; n - skip; ! - rewrite all; q - skip all: '
            ).strip().lower()
            if choice == u'q':
                break
            elif choice == u'n':
                continue
            elif choice == u'!':
                skip_confirmation = True
        engine.execute(UPDATE_Q, id=id, extras=rev)
        print(u'\tUpdated')


if __name__ == u'__main__':
    main()
