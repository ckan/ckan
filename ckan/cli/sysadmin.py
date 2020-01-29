# encoding: utf-8

import click
from six import text_type

import ckan.model as model
from ckan.cli import error_shout
from ckan.cli.user import add_user


@click.group(
    short_help=u"Gives sysadmin rights to a named user.",
    invoke_without_command=True,
)
@click.pass_context
def sysadmin(ctx):
    """Gives sysadmin rights to a named user.

    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_sysadmins)


@sysadmin.command(name=u"list", help=u"List sysadmins.")
def list_sysadmins():
    click.secho(u"Sysadmins:")
    sysadmins = model.Session.query(model.User).filter_by(
        sysadmin=True, state=u"active"
    )
    click.secho(u"count = %i" % sysadmins.count())
    for sysadmin in sysadmins:
        click.secho(
            u"%s name=%s email=%s id=%s"
            % (
                sysadmin.__class__.__name__,
                sysadmin.name,
                sysadmin.email,
                sysadmin.id,
            )
        )


@sysadmin.command(help=u"Convert user into a sysadmin.")
@click.argument(u"username")
@click.argument(u"args", nargs=-1)
@click.pass_context
def add(ctx, username, args):
    user = model.User.by_name(text_type(username))
    if not user:
        click.secho(u'User "%s" not found' % username, fg=u"red")
        if click.confirm(
            u"Create new user: %s?" % username, default=True, abort=True
        ):
            ctx.forward(add_user)
            user = model.User.by_name(text_type(username))

    user.sysadmin = True
    model.Session.add(user)
    model.repo.commit_and_remove()
    click.secho(u"Added %s as sysadmin" % username, fg=u"green")


@sysadmin.command(help=u"Removes user from sysadmins.")
@click.argument(u"username")
def remove(username):
    user = model.User.by_name(text_type(username))
    if not user:
        return error_shout(u'Error: user "%s" not found!' % username)
    user.sysadmin = False
    model.repo.commit_and_remove()
    click.secho(u"Removed %s from sysadmins" % username, fg=u"green")
