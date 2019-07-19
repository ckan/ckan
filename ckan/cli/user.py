# encoding: utf-8

import logging
import sys
from pprint import pprint

import click

import ckan.logic as l
import ckan.plugins as p
from ckan.cli import error_shout

log = logging.getLogger(__name__)


@click.group(name=u'user', short_help=u'Manage user commands')
@click.help_option(u'-h', u'--help')
def user():
    pass


@user.command(u'add', short_help=u'Add new user')
@click.argument('username')
@click.argument('args', nargs=-1)
@click.pass_context
def add_user(ctx, username, args):
    '''Add new user if we use ckan sysadmin add
    or ckan user add
    '''
    # parse args into data_dict
    data_dict = {'name': username}
    for arg in args:
        try:
            field, value = arg.split('=', 1)
            data_dict[field] = value
        except ValueError:
            raise ValueError(
                'Could not parse arg: %r (expected "<option>=<value>)"' % arg
            )

    # Required
    while '@' not in data_dict.get('email', ''):
        error_shout('Error: Invalid email address')
        data_dict['email'] = click.prompt('Email address: ').strip()

    if 'password' not in data_dict:
        data_dict['password'] = click.prompt('Password: ', hide_input=True,
                                             confirmation_prompt=True)

    # Optional
    if 'fullname' in data_dict:
        data_dict['fullname'] = data_dict['fullname'].decode(
            sys.getfilesystemencoding()
        )

    pprint('Creating user: %r' % username)

    try:
        import ckan.logic as logic
        import ckan.model as model
        site_user = logic.get_action('get_site_user')({
            'model': model,
            'ignore_auth': True},
            {}
        )
        context = {
            'model': model,
            'session': model.Session,
            'ignore_auth': True,
            'user': site_user['name'],
        }
        flask_app = ctx.obj.app.apps[u'flask_app']._wsgi_app
        with flask_app.test_request_context():
            user_dict = logic.get_action('user_create')(context, data_dict)
            click.secho(user_dict)
    except logic.ValidationError as e:
        error_shout(e)


def get_user_str(user):
        user_str = 'name=%s' % user.name
        if user.name != user.display_name:
            user_str += ' display=%s' % user.display_name
        return user_str


@user.command(u'list', short_help=u'List all users')
def list_users():
    import ckan.model as model
    click.secho('Users:')
    users = model.Session.query(model.User).filter_by(state='active')
    click.secho('count = %i' % users.count())
    for user in users:
        click.secho(get_user_str(user))


@user.command(u'remove', short_help=u'Remove user')
@click.argument('username')
@click.pass_context
def remove_user(ctx, username):
    import ckan.model as model
    if not username:
        error_shout("Please specify the username to be removed")

    flask_app = ctx.obj.app.apps['flask_app']._wsgi_app
    site_user = l.get_action(u'get_site_user')({u'ignore_auth': True}, {})
    context = {u'user': site_user[u'name']}
    with flask_app.test_request_context():
        p.toolkit.get_action('user_delete')(context, {'id': username})
        click.secho('Deleted user: %s' % username, fg=u'green', bold=True)
