# encoding: utf-8

import re
import traceback

import click

from ckan.cli import error_shout


@click.group(
    short_help=u"Code speed profiler.", invoke_without_command=True,
)
@click.pass_context
def profile(ctx):
    """Provide a ckan url and it will make the request and record how
    long each function call took in a file that can be read by
    pstats.Stats (command-line) or runsnakerun (gui).

    Usage:
       profile URL [username]

    e.g. profile /data/search

    The result is saved in profile.data.search
    To view the profile in runsnakerun:
       runsnakerun ckan.data.search.profile

    You may need to install python module: cProfile

    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(profile)


@profile.command(short_help=u"Code speed profiler.",)
@click.argument(u"url")
@click.argument(u"user", required=False, default=u"visitor")
def profile(url, user):
    import cProfile
    from ckan.tests.helpers import _get_test_app

    app = _get_test_app()

    def profile_url(url):
        try:
            res = app.get(
                url, status=[200], extra_environ={u"REMOTE_USER": str(user)}
            )
        except KeyboardInterrupt:
            raise
        except Exception:
            error_shout(traceback.format_exc())

    output_filename = u"ckan%s.profile" % re.sub(
        u"[/?]", u".", url.replace(u"/", u".")
    )
    profile_command = u"profile_url('%s')" % url
    cProfile.runctx(
        profile_command, globals(), locals(), filename=output_filename
    )
    import pstats

    stats = pstats.Stats(output_filename)
    stats.sort_stats(u"cumulative")
    stats.print_stats(0.1)  # show only top 10% of lines
    click.secho(u"Only top 10% of lines shown")
    click.secho(u"Written profile to: %s" % output_filename, fg=u"green")
