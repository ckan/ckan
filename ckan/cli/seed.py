# encoding: utf-8

import logging

import click

from ckan.lib.create_test_data import CreateTestData

log = logging.getLogger(__name__)


@click.group(short_help=u'Create test data in the database.')
def seed():
    u'''Create test data in the database.

    Tests can also delete the created objects easily with the delete() method.
    '''
    pass


@seed.command(short_help=u'Annakarenina and warandpeace.')
@click.pass_context
def basic(ctx):
    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        CreateTestData.create_basic_test_data()


@seed.command(short_help=u'Realistic data to test search.')
@click.pass_context
def search(ctx):
    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        CreateTestData.create_search_test_data()


@seed.command(short_help=u'Government style data.')
@click.pass_context
def gov(ctx):
    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        CreateTestData.create_gov_test_data()


@seed.command(short_help=u'Package relationships data.')
@click.pass_context
def family(ctx):
    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        CreateTestData.create_family_test_data()


@seed.command(short_help=u'Create a user "tester" with api key "tester".')
@click.pass_context
def user(ctx):
    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        CreateTestData.create_test_user()
    click.echo(
        u'Created user {0} with password {0} and apikey {0}'.format(u'tester')
    )


@seed.command(short_help=u'Test translations of terms.')
@click.pass_context
def translations(ctx):
    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        CreateTestData.create_translations_test_data()


@seed.command(short_help=u'Some test vocabularies.')
@click.pass_context
def vocabs(ctx):
    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        CreateTestData.create_vocabs_test_data()


@seed.command(short_help=u'Hierarchy of groups.')
@click.pass_context
def hierarchy(ctx):
    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        CreateTestData.create_group_hierarchy_test_data()
