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

    The background job system is based on RQ_.

    .. _RQ: http://python-rq.org


.. _background jobs writing:

Writing and enqueuing background jobs
=====================================

.. note::

    This section is only relevant for developers working on CKAN or an
    extension.

The core of a background job is a regular Python function. For example, here's
a very simple job function that logs a message::

    import logging

    def log_job(msg, level=logging.INFO, logger='ckan'):
        '''
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

    jobs.enqueue(log_job, ['My log message'])

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

    jobs.enqueue(log_job, ['My log message'], {'logger': 'ckanext.foo'})

You can also give the job a title which can be useful for identifying it when
:ref:`managing the job queue <background jobs management>`::

    jobs.enqueue(log_job, ['My log message'], title='My log job')

A timeout can also be set on a job with the ``timeout`` keyword argument::

    jobs.enqueue(log_job, ['My log message'], rq_kwargs={"timeout": 3600})

The default background job timeout is 180 seconds. This is set in the
ckan config ``.ini`` file under the ``ckan.jobs.timeout`` item.

.. note::

    For advanced queue management like scheduling jobs or managing existing
    jobs access the RQ_ Queue_ and Job_ interfaces with
    :py:func:`ckan.plugins.toolkit.get_job_queue` or
    :py:func:`ckan.plugins.toolkit.job_from_id` functions.
    Use :py:func:`ckan.lib.jobs.get_queue` or
    :py:func:`ckan.lib.jobs.job_from_id` for code in core CKAN.

    .. _Queue: https://python-rq.org/docs/

    .. _Job: https://python-rq.org/docs/jobs/

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

    jobs.enqueue(log_job, ["I'm from a different queue!"],
                 queue='my-own-queue')

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



