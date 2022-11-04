# encoding: utf-8

import logging
import six
import click
from six import text_type
from datetime import datetime

import ckan.logic as logic
import ckan.plugins as plugin
import ckan.model as model
from ckan.cli import error_shout
from ckan.common import json


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


@user.group()
def token():
    u"""Control API Tokens"""
    pass


@token.command(u"add", context_settings=dict(ignore_unknown_options=True))
@click.argument(u"username")
@click.argument(u"token_name")
@click.argument(u"extras", type=click.UNPROCESSED, nargs=-1)
@click.option(
    u"--json",
    metavar=u"EXTRAS",
    type=json.loads,
    default=u"{}",
    help=u"Valid JSON object with additional fields for api_token_create",
)
def add_token(username, token_name, extras, json):
    u"""Create new API Token for the given user.

    Either arbitary numer of arguments in format `key=value` or --json
    option containing encoded JSON object can be passed in order to
    customize behavior of api_token_create action. When both privided,
    `key=value` will have higher precedence and will replace
    corresponding keys from --json object.

    Example::

      ckan user token add john_doe new_token x=y --json '{"prop": "value"}'

    """
    for chunk in extras:
        try:
            key, value = chunk.split(u"=")
        except ValueError:
            error_shout(
                u"Extras must be passed in `key=value` format. Got: {}".format(
                    chunk
                )
            )
            raise click.Abort()
        json[key] = value
    json.update({u"user": username, u"name": token_name})
    try:
        token = plugin.toolkit.get_action(u"api_token_create")(
            {u"ignore_auth": True}, json
        )
    except plugin.toolkit.ObjectNotFound as e:
        error_shout(e)
        raise click.Abort()
    click.secho(u"API Token created:", fg=u"green")
    click.echo(u"\t", nl=False)
    click.echo(token[u"token"])


@token.command(u"revoke")
@click.argument(u"id")
def revoke_token(id):
    u"""Remove API Token with the given ID"""
    if not model.ApiToken.revoke(id):
        error_shout(u"API Token not found")
        raise click.Abort()
    click.secho(u"API Token has been revoked", fg=u"green")


@token.command(u"list")
@click.argument(u"username")
def list_tokens(username):
    u"""List all API Tokens for the given user"""
    try:
        tokens = plugin.toolkit.get_action(u"api_token_list")(
            {u"ignore_auth": True}, {u"user": username}
        )
    except plugin.toolkit.ObjectNotFound as e:
        error_shout(e)
        raise click.Abort()
    if not tokens:
        click.secho(u"No tokens have been created for user yet", fg=u"red")
        return
    click.echo(u"Tokens([id] name - lastAccess):")

    for token in tokens:
        last_access = token[u"last_access"]
        if last_access:
            accessed = plugin.toolkit.h.date_str_to_datetime(last_access)
            if six.PY2:
                """
                Strip out microseconds to force formatting as isoformat doesnt
                have a timespec param on Python 2.
                """
                accessed = datetime(
                    accessed.year,
                    accessed.month,
                    accessed.day,
                    accessed.hour,
                    accessed.minute,
                    accessed.second).isoformat(b" ")
            else:
                accessed = accessed.isoformat(u" ", u"seconds")

        else:
            accessed = u"Never"
        click.echo(
            u"\t[{id}] {name} - {accessed}".format(
                name=token[u"name"], id=token[u"id"], accessed=accessed
            )
        )
