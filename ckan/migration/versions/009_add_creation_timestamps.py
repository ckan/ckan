from datetime import datetime

from sqlalchemy import *
from migrate import *
import migrate.changeset

metadata = MetaData(migrate_engine)

domain_obj_names = ['rating', 'group', 'user']

def upgrade():
    # Add the column
    import ckan.model as model
    for domain_obj_name in domain_obj_names:
        user_sql = 'ALTER TABLE "%s" ADD created TIMESTAMP WITHOUT TIME ZONE' % domain_obj_name
        model.Session.execute(user_sql)
    model.repo.commit_and_remove()

    # Initialise existing
    for domain_obj in [model.Rating, model.Group, model.User]:
        for obj in domain_obj.query.all():
            obj.created = datetime.now()
    model.repo.commit_and_remove()

def downgrade():
    raise NotImplementedError()
