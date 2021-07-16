# encoding: utf-8

import click
from six import text_type

import ckan.model as model
from ckan.cli import error_shout
from ckan.cli.user import add_user


@click.group(
    short_help="Gives sysadmin rights to a named user.",
    invoke_without_command=True,
)
@click.pass_context
def sysadmin(ctx):
    """Gives sysadmin rights to a named user.

    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_sysadmins)


@sysadmin.command(name="list", help="List sysadmins.")
def list_sysadmins():
    click.secho("Sysadmins:")
    sysadmins = model.Session.query(model.User).filter_by(
        sysadmin=True, state="active"
    )
    click.secho("count = %i" % sysadmins.count())
    for sysadmin in sysadmins:
        click.secho(
            "%s name=%s email=%s id=%s"
            % (
                sysadmin.__class__.__name__,
                sysadmin.name,
                sysadmin.email,
                sysadmin.id,
            )
        )


@sysadmin.command(help="Convert user into a sysadmin.")
@click.argument("username")
@click.argument("args", nargs=-1)
@click.pass_context
def add(ctx, username, args):
    user = model.User.by_name(text_type(username))
    if not user:
        click.secho('User "%s" not found' % username, fg="red")
        if click.confirm(
            "Create new user: %s?" % username, default=True, abort=True
        ):
            ctx.forward(add_user)
            user = model.User.by_name(text_type(username))

    user.sysadmin = True
    model.Session.add(user)
    model.repo.commit_and_remove()
    click.secho("Added %s as sysadmin" % username, fg="green")


@sysadmin.command(help="Removes user from sysadmins.")
@click.argument("username")
def remove(username):
    user = model.User.by_name(text_type(username))
    if not user:
        return error_shout('Error: user "%s" not found!' % username)
    user.sysadmin = False
    model.repo.commit_and_remove()
    click.secho("Removed %s from sysadmins" % username, fg="green")
