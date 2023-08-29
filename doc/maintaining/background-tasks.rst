.. _background jobs:

===============
Background jobs
===============
CKAN allows you to create jobs that run in the 'background', i.e.
asynchronously and without blocking the main application. Such jobs can be
created in :doc:`Extensions </extensions/index>` or in core CKAN.

Background jobs can be essential to providing certain kinds of functionality,
for example:

* Creating web-hooks that notify other services when certain changes occur (for
  example a dataset is updated)

* Performing processing or validation or on data (as done by the Archiver and
  DataStorer Extensions)

Basically, any piece of work that takes too long to perform while the main
application is waiting is a good candidate for a background job.

.. note::

    The current background job system is based on RQ_ and was introduced in
    CKAN 2.7. See :ref:`background jobs migration` for details on how to
    migrate your jobs from the previous system introduced in CKAN 1.5.

    .. _RQ: http://python-rq.org


.. _background jobs writing:

Writing and enqueuing background jobs
=====================================

.. note::

    This section is only relevant for developers working on CKAN or an
    extension.

The core of a background job is a regular Python function. For example, here's
a very simply job function that logs a message::

    import logging

    def log_job(msg, level=logging.INFO, logger=u'ckan'):
        u'''
        Background job to log a message.
        '''
        logger = logging.getLogger(logger)
        logger.log(level, msg)


And that's it. Your job function can use all the usual Python features. Just
keep in mind that your function will be run in a separate process by a
:ref:`worker <background jobs workers>`, so your function should not depend on
the current state of global variables, etc. Ideally your job function should
receive all the information it needs via its arguments.

In addition, the module that contains your job function must be importable by
the worker, which must also be able to get the function from its module. This
means that nested functions, lambdas and instance methods cannot be used as job
functions. While class methods of top-level classes can be used it's best to
stick to ordinary module-level functions.

.. note::

    Background jobs do not support return values (since they run asynchronously
    there is no place to return those values to). If your job function produces
    a result then it needs to store that result, for example in a file or in
    CKAN's database.

Once you have a job function, all you need to do is to use
``ckan.lib.jobs.enqueue`` to create an actual job out of it::

    import ckan.lib.jobs as jobs

    jobs.enqueue(log_job, [u'My log message'])

This will place a job on the :ref:`job queue <background jobs queues>` where it
can be picked up and executed by a worker.

.. note::

    Extensions should use :py:func:`ckan.plugins.toolkit.enqueue_job` instead.
    It's the same function but accessing it via :py:mod:`ckan.plugins.toolkit`
    :ref:`decouples your code from CKAN's internal structure <use the plugins
    toolkit>`.

The first argument to ``enqueue`` is the job function to use. The second is a
list of the arguments which should be passed to the function. You can omit it
in which case no arguments will be passed. You can also pass keyword arguments
in a dict as the third argument::

    jobs.enqueue(log_job, [u'My log message'], {u'logger': u'ckanext.foo'})

You can also give the job a title which can be useful for identifying it when
:ref:`managing the job queue <background jobs management>`::

    jobs.enqueue(log_job, [u'My log message'], title=u'My log job')

A timeout can also be set on a job iwth the ``timeout`` keyword argument::

    jobs.enqueue(log_job, [u'My log message'], rq_kwargs={"timeout": 3600})

The default background job timeout is 180 seconds. This is set in the
ckan config ``.ini`` file under the ``ckan.jobs.timeout`` item.

Accessing the database from background jobs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Code running in a background job can access the CKAN database like any other
CKAN code.

In particular, using the action functions to modify the database from within a
background job is perfectly fine. Just keep in mind that while your job is
running in the background, the CKAN main process or other background jobs may
also modify the database. Hence a single call to an action function is atomic
from your job's view point, but between multiple calls there may be foreign
changes to the database.

Special care has to be taken if your background job needs low-level access to
the database, for example to modify SQLAlchemy model instances directly without
going through an action function. Each background job runs in a separate
process and therefore has its own SQLAlchemy session. Your code has to make
sure that the changes it makes are properly contained in transactions and that
you refresh your view of the database to receive updates where necessary. For
these (and other) reasons it is recommended to :ref:`use the action functions
to interact with the database <always use action functions>`.


.. _background jobs workers:

Running background jobs
=======================
Jobs are placed on the :ref:`job queue <background jobs queues>`, from which
they can be retrieved and executed. Since jobs are designed to run
asynchronously that happens in a separate process called a *worker*.

After it has been started, a worker listens on the queue until a job is
enqueued. The worker then removes the job from the queue and executes it.
Afterwards the worker waits again for the next job to be enqueued.

.. note::

    Executed jobs are discarded. In particular, no information about past jobs
    is kept.

Workers can be started using the :ref:`cli jobs worker` command::

    ckan -c /etc/ckan/default/ckan.ini jobs worker

The worker process will run indefinitely (you can stop it using ``CTRL+C``).

.. note::

    You can run multiple workers if your setup uses many or particularly long
    background jobs.


.. _background jobs supervisor:

Using Supervisor
^^^^^^^^^^^^^^^^
In a production setting, the worker should be run in a more robust way. One
possibility is to use Supervisor_.

.. _Supervisor: http://supervisord.org/

First install Supervisor::

    sudo apt-get install supervisor

Next copy the configuration file template::

    sudo cp /usr/lib/ckan/default/src/ckan/ckan/config/supervisor-ckan-worker.conf /etc/supervisor/conf.d
    
Next make sure the ``/var/log/ckan/`` directory exists, if not then it needs to be created::

    sudo mkdir /var/log/ckan

Open ``/etc/supervisor/conf.d/supervisor-ckan-worker.conf`` in your favourite
text editor and make sure all the settings suit your needs. If you installed
CKAN in a non-default location (somewhere other than ``/usr/lib/ckan/default``)
then you will need to update the paths in the config file (see the comments in
the file for details).

Restart Supervisor::

    sudo service supervisor restart

The worker should now be running. To check its status, use

::

    sudo supervisorctl status

You can restart the worker via

::

    sudo supervisorctl restart ckan-worker:*

To test that background jobs are processed correctly you can enqueue a test job
via

::

    ckan -c |ckan.ini| jobs test

The worker's log files (``/var/log/ckan/ckan-worker.stdout.log`` and/or ``/var/log/ckan/ckan-worker.stderr.log``) 
should then show how the job was processed by the worker.

In case you run into problems, make sure to check the logs of Supervisor and
the worker::

    cat /var/log/supervisor/supervisord.log
    cat /var/log/ckan/ckan-worker.stdout.log
    cat /var/log/ckan/ckan-worker.sterr.log



.. _background jobs management:

Managing background jobs
========================
Once they are enqueued, background jobs can be managed via the
:ref:`ckan command <cli>` and the :ref:`web API <action api>`.

List enqueues jobs
^^^^^^^^^^^^^^^^^^
* :ref:`ckan jobs list <cli jobs list>`
* :py:func:`ckan.logic.action.get.job_list`

Show details about a job
^^^^^^^^^^^^^^^^^^^^^^^^
* :ref:`ckan jobs show <cli jobs show>`
* :py:func:`ckan.logic.action.get.job_show`

Cancel a job
^^^^^^^^^^^^
A job that hasn't been processed yet can be canceled via

* :ref:`ckan jobs cancel <cli jobs cancel>`
* :py:func:`ckan.logic.action.delete.job_cancel`

Clear all enqueued jobs
^^^^^^^^^^^^^^^^^^^^^^^
* :ref:`ckan jobs clear <cli jobs clear>`
* :py:func:`ckan.logic.action.delete.job_clear`

Logging
^^^^^^^
Information about enqueued and processed background jobs is automatically
logged to the CKAN logs. You may need to update your logging configuration to
record messages at the *INFO* level for the messages to be stored.

.. _background jobs queues:

Background job queues
=====================
By default, all functionality related to background jobs uses a single job
queue that is specific to the current CKAN instance. However, in some
situations it is useful to have more than one queue. For example, you might
want to distinguish between short, urgent jobs and longer, less urgent ones.
The urgent jobs should be processed even if a long and less urgent job is
already running.

For such scenarios, the job system supports multiple queues. To use a different
queue, all you have to do is pass the (arbitrary) queue name. For example, to
enqueue a job at a non-default queue::

    jobs.enqueue(log_job, [u"I'm from a different queue!"],
                 queue=u'my-own-queue')

Similarly, to start a worker that only listens to the queue you just posted a
job to::

    ckan -c |ckan.ini| jobs worker my-own-queue

See the documentation of the various functions and commands for details on how
to use non-standard queues.

.. note::

    If you create a custom queue in your extension then you should prefix the
    queue name using your extension's name. See :ref:`avoid name clashes`.

    Queue names are internally automatically prefixed with the CKAN site ID,
    so multiple parallel CKAN instances are not a problem.


.. _background jobs testing:

Testing code that uses background jobs
======================================
Due to the asynchronous nature of background jobs, code that uses them needs
to be handled specially when writing tests.

A common approach is to use the `mock package`_ to replace the
``ckan.plugins.toolkit.enqueue_job`` function with a mock that executes jobs
synchronously instead of asynchronously:

.. code-block:: python

    import unittest.mock as mock

    from ckan.tests import helpers


    def synchronous_enqueue_job(job_func, args=None, kwargs=None, title=None):
        '''
        Synchronous mock for ``ckan.plugins.toolkit.enqueue_job``.
        '''
        args = args or []
        kwargs = kwargs or {}
        job_func(*args, **kwargs)


    class TestSomethingWithBackgroundJobs(helpers.FunctionalTestBase):

        @mock.patch('ckan.plugins.toolkit.enqueue_job',
                    side_effect=synchronous_enqueue_job)
        def test_something(self, enqueue_job_mock):
            some_function_that_enqueues_a_background_job()
            assert something


Depending on how the function under test calls ``enqueue_job`` you might need
to adapt where the mock is installed. See `mock's documentation`_ for details.


.. _mock package: https://pypi.python.org/pypi/mock

.. _mock's documentation: https://docs.python.org/dev/library/unittest.mock.html


.. _background jobs migration:

Migrating from CKAN's previous background job system
====================================================
Before version 2.7 (starting from 1.5), CKAN offered a different background job
system built around Celery_. As of CKAN 2.8, that system is no longer available.
You should therefore update your code to use the new system described above.

.. _Celery: http://celeryproject.org/

Migrating existing job functions is easy. In the old system, a job function
would look like this::

    @celery.task(name=u'my_extension.echofunction')
    def echo(message):
        print message

As :ref:`described above <background jobs writing>`, under the new system the
same function would be simply written as

::

    def echo(message):
        print message

There is no need for a special decorator. In the new system there is also no
need for registering your tasks via ``setup.py``.

Migrating the code that enqueues a task is also easy. Previously it would look
like this::

    celery.send_task(u'my_extension.echofunction', args=[u'Hello World'],
                     task_id=str(uuid.uuid4()))

With the new system, it looks as follows::

    import ckan.lib.jobs as jobs

    jobs.enqueue(ckanext.my_extension.plugin.echo, [u'Hello World'])

As you can see, the new system does not use strings to identify job functions
but uses the functions directly instead. There is also no need for creating a
job ID, that will be done automatically for you.


Supporting both systems at once
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Not all CKAN installations will immediately update to CKAN 2.7. It might
therefore make sense for you to support both the new and the old job system.
That way you are ready when the old system is removed but can continue to
support older CKAN installations.

The easiest way to do that is to use `ckanext-rq
<https://github.com/davidread/ckanext-rq>`_, which provides a back-port of the
new system to older CKAN versions.

If you are unable to use *ckanext-rq* then you will need to write your code in
such a way that it works on both systems. This could looks as follows. First
split your Celery-based job functions into the job itself and its Celery
handler. That is, change

::

    @celery.task(name=u'my_extension.echofunction')
    def echo(message):
        print message

to

::

    def echo(message):
        print message

    @celery.task(name=u'my_extension.echofunction')
    def echo_celery(*args, **kwargs):
      echo(*args, **kwargs)

That way, you can call ``echo`` using the new system and use the name for
Celery.

Then use the new system if it is available and fall back to Celery otherwise::

    def compat_enqueue(name, fn, args=None):
        u'''
        Enqueue a background job using Celery or RQ.
        '''
        try:
            # Try to use RQ
            from ckan.plugins.toolkit import enqueue_job
            enqueue_job(fn, args=args)
        except ImportError:
            # Fallback to Celery
            import uuid
            from ckan.lib.celery_app import celery
            celery.send_task(name, args=args, task_id=str(uuid.uuid4()))

Use that function as follows for enqueuing a job::

    compat_enqueue(u'my_extension.echofunction',
                   ckanext.my_extension.plugin.echo,
                   [u'Hello World'])
