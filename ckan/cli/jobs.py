# encoding: utf-8

import click

import ckan.lib.jobs as bg_jobs
import ckan.logic as logic
import ckan.plugins as p
from ckan.cli import error_shout


@click.group(name="jobs", short_help="Manage background jobs.")
def jobs():
    pass


@jobs.command(short_help="Start a worker.",)
@click.option("--burst", is_flag=True, help="Start worker in burst mode.")
@click.argument("queues", nargs=-1)
def worker(burst, queues):
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


@jobs.command(name="list", short_help="List jobs.")
@click.argument("queues", nargs=-1)
def list_jobs(queues):
    """List currently enqueued jobs from the given queues. If no queue
    names are given then the jobs from all queues are listed.
    """
    data_dict = {
        "queues": list(queues),
    }
    jobs = p.toolkit.get_action("job_list")({"ignore_auth": True}, data_dict)
    if not jobs:
        return click.secho("There are no pending jobs.", fg="green")
    for job in jobs:
        if job["title"] is None:
            job["title"] = ""
        else:
            job["title"] = '"{}"'.format(job["title"])
        click.secho("{created} {id} {queue} {title}".format(**job))


@jobs.command(short_help="Show details about a specific job.")
@click.argument("id")
def show(id):
    try:
        job = p.toolkit.get_action("job_show")(
            {"ignore_auth": True}, {"id": id}
        )
    except logic.NotFound:
        error_shout('There is no job with ID "{}"'.format(id))
        raise click.Abort()

    click.secho("ID:      {}".format(job["id"]))
    if job["title"] is None:
        title = "None"
    else:
        title = '"{}"'.format(job["title"])
    click.secho("Title:   {}".format(title))
    click.secho("Created: {}".format(job["created"]))
    click.secho("Queue:   {}".format(job["queue"]))


@jobs.command(short_help="Cancel a specific job.")
@click.argument("id")
def cancel(id):
    """Cancel a specific job. Jobs can only be canceled while they are
    enqueued. Once a worker has started executing a job it cannot be
    aborted anymore.

    """
    try:
        p.toolkit.get_action("job_cancel")(
            {"ignore_auth": True}, {"id": id}
        )
    except logic.NotFound:
        error_shout('There is no job with ID "{}"'.format(id))
        raise click.Abort()

    click.secho("Cancelled job {}".format(id), fg="green")


@jobs.command(short_help="Cancel all jobs.")
@click.argument("queues", nargs=-1)
def clear(queues):
    """Cancel all jobs on the given queues. If no queue names are given
    then ALL queues are cleared.

    """
    data_dict = {
        "queues": list(queues),
    }
    queues = p.toolkit.get_action("job_clear")(
        {"ignore_auth": True}, data_dict
    )
    queues = ('"{}"'.format(q) for q in queues)
    click.secho("Cleared queue(s) {}".format(", ".join(queues)), fg="green")


@jobs.command(short_help="Enqueue a test job.")
@click.argument("queues", nargs=-1)
def test(queues):
    """Enqueue a test job. If no queue names are given then the job is
    added to the default queue. If queue names are given then a
    separate test job is added to each of the queues.

    """
    for queue in queues or [bg_jobs.DEFAULT_QUEUE_NAME]:
        job = bg_jobs.enqueue(
            bg_jobs.test_job, ["A test job"], title="A test job", queue=queue
        )
        click.secho(
            'Added test job {} to queue "{}"'.format(job.id, queue),
            fg="green",
        )
