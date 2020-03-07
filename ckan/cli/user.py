# encoding: utf-8

import logging
import sys
from pprint import pprint

import six
import click
from six import text_type

import ckan.logic as logic
import ckan.plugins as plugin
from ckan.cli import error_shout

log = logging.getLogger(__name__)


@click.group(name=u'user', short_help=u'Manage user commands')
@click.help_option(u'-h', u'--help')
def user():
    pass


@user.command(u'add', short_help=u'Add new user')
@click.argument(u'username')
@click.argument(u'args', nargs=-1)
@click.pass_context
def add_user(ctx, username, args):
    u'''Add new user if we use ckan sysadmin add
    or ckan user add
    '''
    # parse args into data_dict
    data_dict = {u'name': username}
    for arg in args:
        try:
            field, value = arg.split(u'=', 1)
            data_dict[field] = value
        except ValueError:
            raise ValueError(
                u'Could not parse arg: %r (expected "<option>=<value>)"' % arg
            )

    # Required
    if u'email' not in data_dict:
        data_dict['email'] = click.prompt(u'Email address ').strip()

    if u'password' not in data_dict:
        data_dict['password'] = click.prompt(u'Password ', hide_input=True,
                                             confirmation_prompt=True)

    # Optional
    if u'fullname' in data_dict:
        data_dict['fullname'] = six.ensure_text(data_dict['fullname'])

    # pprint(u'Creating user: %r' % username)

    try:
        import ckan.logic as logic
        import ckan.model as model
        site_user = logic.get_action(u'get_site_user')({
            u'model': model,
            u'ignore_auth': True},
            {}
        )
        context = {
            u'model': model,
            u'session': model.Session,
            u'ignore_auth': True,
            u'user': site_user['name'],
        }
        flask_app = ctx.meta['flask_app']
        # Current user is tested agains sysadmin role during model
        # dictization, thus we need request context
        with flask_app.test_request_context():
            user_dict = logic.get_action(u'user_create')(context, data_dict)
        click.secho(u"Successfully created user: %s" % user_dict['name'],
                    fg=u'green', bold=True)
    except logic.ValidationError as e:
        error_shout(e)
        raise click.Abort()


def get_user_str(user):
    user_str = u'name=%s' % user.name
    if user.name != user.display_name:
        user_str += u' display=%s' % user.display_name
    return user_str


@user.command(u'list', short_help=u'List all users')
def list_users():
    import ckan.model as model
    click.secho(u'Users:')
    users = model.Session.query(model.User).filter_by(state=u'active')
    click.secho(u'count = %i' % users.count())
    for user in users:
        click.secho(get_user_str(user))


@user.command(u'remove', short_help=u'Remove user')
@click.argument(u'username')
@click.pass_context
def remove_user(ctx, username):
    import ckan.model as model
    if not username:
        error_shout(u'Please specify the username to be removed')
        return

    site_user = logic.get_action(u'get_site_user')({u'ignore_auth': True}, {})
    context = {u'user': site_user[u'name']}
    with ctx.meta['flask_app'].test_request_context():
        plugin.toolkit.get_action(u'user_delete')(context, {u'id': username})
        click.secho(u'Deleted user: %s' % username, fg=u'green', bold=True)


@user.command(u'show', short_help=u'Show user')
@click.argument(u'username')
def show_user(username):
    import ckan.model as model
    if not username:
        error_shout(u'Please specify the username for the user')
        return
    user = model.User.get(text_type(username))
    click.secho(u'User: %s' % user)


@user.command(u'setpass', short_help=u'Set password for the user')
@click.argument(u'username')
def set_password(username):
    import ckan.model as model
    if not username:
        error_shout(u'Need name of the user.')
        return
    user = model.User.get(username)
    if not user:
        error_shout(u"User not found!")
        return
    click.secho(u'Editing user: %r' % user.name, fg=u'yellow')

    password = click.prompt(u'Password', hide_input=True,
                            confirmation_prompt=True)
    user.password = password
    model.repo.commit_and_remove()
    click.secho(u'Password updated!', fg=u'green', bold=True)
