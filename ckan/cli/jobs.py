# encoding: utf-8
from __future__ import annotations

import click

import ckan.lib.jobs as bg_jobs
import ckan.logic as logic
from ckan.cli import error_shout


@click.group(name=u"jobs", short_help=u"Manage background jobs.")
def jobs():
    pass


@jobs.command(short_help=u"Start a worker.",)
@click.option(u"--burst", is_flag=True, help=u"Start worker in burst mode.")
@click.argument(u"queues", nargs=-1)
def worker(burst: bool, queues: list[str]):
    """Start a worker that fetches jobs from queues and executes them. If
    no queue names are given then the worker listens to the default
    queue, this is equivalent to

        paster jobs worker default

    If queue names are given then the worker listens to those queues
    and only those:

        paster jobs worker my-custom-queue

    Hence, if you want the worker to listen to the default queue and
    some others then you must list the default queue explicitly:

        paster jobs worker default my-custom-queue

    If the `--burst` option is given then the worker will exit as soon
    as all its queues are empty.
    """
    bg_jobs.Worker(queues).work(burst=burst)


@jobs.command(name=u"list", short_help=u"List jobs.")
@click.argument(u"queues", nargs=-1)
def list_jobs(queues: list[str]):
    """List currently enqueued jobs from the given queues. If no queue
    names are given then the jobs from all queues are listed.
    """
    data_dict = {
        u"queues": list(queues),
    }
    jobs = logic.get_action(u"job_list")({u"ignore_auth": True}, data_dict)
    if not jobs:
        return click.secho(u"There are no pending jobs.", fg=u"green")
    for job in jobs:
        if job[u"title"] is None:
            job[u"title"] = u""
        else:
            job[u"title"] = f'"{job[u"title"]}"'
        click.secho(
            f"{job['created']} {job['id']} {job['queue']} {job['title']}")


@jobs.command(short_help=u"Show details about a specific job.")
@click.argument(u"id")
def show(id: str):
    try:
        job = logic.get_action(u"job_show")(
            {u"ignore_auth": True}, {u"id": id}
        )
    except logic.NotFound:
        error_shout(f'There is no job with ID "{id}"')
        raise click.Abort()

    click.secho(f"ID:      {job['id']}")
    if job[u"title"] is None:
        title = u"None"
    else:
        title = f'"{job[u"title"]}"'
    click.secho(f"Title:   {title}")
    click.secho(f"Created: {job['created']}")
    click.secho(f"Queue:   {job['queue']}")


@jobs.command(short_help=u"Cancel a specific job.")
@click.argument(u"id")
def cancel(id: str):
    """Cancel a specific job. Jobs can only be canceled while they are
    enqueued. Once a worker has started executing a job it cannot be
    aborted anymore.

    """
    try:
        logic.get_action(u"job_cancel")(
            {u"ignore_auth": True}, {u"id": id}
        )
    except logic.NotFound:
        error_shout(f'There is no job with ID "{id}"')
        raise click.Abort()

    click.secho(f"Cancelled job {id}", fg=u"green")


@jobs.command(short_help=u"Cancel all jobs.")
@click.argument(u"queues", nargs=-1)
def clear(queues: list[str]):
    """Cancel all jobs on the given queues. If no queue names are given
    then ALL queues are cleared.

    """
    data_dict = {
        u"queues": list(queues),
    }
    queues = logic.get_action(u"job_clear")(
        {u"ignore_auth": True}, data_dict
    )
    queues = [u'"{}"'.format(q) for q in queues]
    click.secho(f'Cleared queue(s) {", ".join(queues)}', fg=u"green")


@jobs.command(short_help=u"Enqueue a test job.")
@click.argument(u"queues", nargs=-1)
def test(queues: list[str]):
    """Enqueue a test job. If no queue names are given then the job is
    added to the default queue. If queue names are given then a
    separate test job is added to each of the queues.

    """
    for queue in queues or [bg_jobs.DEFAULT_QUEUE_NAME]:
        job = bg_jobs.enqueue(
            bg_jobs.test_job, [u"A test job"], title=u"A test job", queue=queue
        )
        click.secho(f'Added test job {job.id} to queue "{queue}"', fg=u"green")
