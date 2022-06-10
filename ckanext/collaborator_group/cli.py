import sys
import click

from ckanext.collaborator_group.model import tables_exist, drop_tables, create_tables


@click.group()
def collaborator():
    """Collaborator Organizations commands.
    """
    pass


@collaborator.command(name='init-db', short_help=u"Prepare database tables")
def init_db():
    if tables_exist():
        print(u'Dataset collaborators-group tables already exist')
        sys.exit(0)
    create_tables()
    print(u'Dataset collaborator-group tables created')


@collaborator.command(name='remove-db', short_help=u"Prepare database tables")
def remove_db():
    if not tables_exist():
        print(u'Dataset collaborator-group tables do not exist')
        sys.exit(0)

    drop_tables()
    print(u'Dataset collaborator-group tables removed')


@collaborator.command(name='reset-db', short_help=u"Reset database tables")
def reset_db():
    if not tables_exist():
        print(u'Dataset collaborator-group tables do not exist')
        sys.exit(0)
    else:
        drop_tables()

    create_tables()
    print(u'Dataset collaborator-group tables reset')


def get_commands():
    return [init_db, remove_db, reset_db]