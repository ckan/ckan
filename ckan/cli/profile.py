# encoding: utf-8

import re
import traceback

import click
from . import error_shout


@click.command(short_help="Code speed profiler.")
@click.argument("url")
@click.argument("user", required=False, default="visitor")
@click.option('--cold', is_flag=True, default=False, help='measure first call')
@click.option('-b', '--best-of', type=int, default=3, help='best of N calls')
def profile(url: str, user: str, cold: bool, best_of: int):
    """Provide a ckan url and it will make the request and record how
    long each function call took in a file that can be read by
    pstats.Stats (command-line) or SnakeViz (web).

    Usage:
       profile URL [username]

    e.g. profile /data/search

    The result is saved in profile.data.search
    To view the profile in runsnakerun:
       runsnakerun ckan.data.search.profile

    You may need to install python module: cProfile

    """
    from cProfile import Profile
    from ckan.tests.helpers import _get_test_app

    app = _get_test_app()

    def profile_url(url: str):
        try:
            app.get(
                url, status=200, environ_overrides={"REMOTE_USER": str(user)}
            )
        except KeyboardInterrupt:
            raise
        except Exception:
            error_shout(traceback.format_exc())

    if not cold:
        profile_url(url)

    best = None
    for _n in range(best_of):
        with Profile() as pr:
            profile_url(url)
        if best is None or (best.getstats()[0].totaltime
                            > pr.getstats()[0].totaltime):
            best = pr

    if best is None:
        return

    output_filename = "ckan%s.profile" % re.sub(r"[\W]", ".", url)
    best.dump_stats(output_filename)
    import pstats

    stats = pstats.Stats(output_filename)
    stats.sort_stats(u"cumulative")
    stats.print_stats(0.1)  # show only top 10% of lines
    click.secho(u"Only top 10% of lines shown")
    click.secho(u"Written profile to: %s" % output_filename, fg=u"green")
