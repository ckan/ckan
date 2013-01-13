from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
CREATE TABLE subscription
(
    id TEXT PRIMARY KEY,
    definition TEXT NOT NULL,
    name TEXT NOT NULL,
    owner_id TEXT NOT NULL REFERENCES "user" (id) ON UPDATE CASCADE ON DELETE CASCADE,
    last_evaluated TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    last_modified TIMESTAMP WITHOUT TIME ZONE NOT NULL
);

CREATE TABLE subscription_item
(
    id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL REFERENCES "subscription" (id) ON UPDATE CASCADE ON DELETE CASCADE,
    key TEXT NOT NULL,
    data TEXT NOT NULL,
    flag TEXT NOT NULL
);
    '''
    )
