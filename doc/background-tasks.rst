================
Background tasks
================

.. version-added: 1.5.1

CKAN allows you to create tasks that run in the 'background', that is
asynchronously and without blocking the main application (these tasks can also
be automatically retried in the case of transient failures). Such tasks can be
created in :doc:`Extensions <extensions/index>` or in core CKAN.

Background tasks can be essential to providing certain kinds of functionality,
for example:

* Creating webhooks that notify other services when certain changes occur (for
  example a dataset is updated)
* Performing processing or validation or on data (as done by the Archiver and
  DataStorer Extensions)


Enabling background tasks
=========================

To manage and run background tasks requires a job queue and CKAN uses celery_
(plus the CKAN database) for this purpose. Thus, to use background tasks you
need to install and run celery_. As of CKAN 1.7, celery is a required library
and will be already installed after a default CKAN install.

Installation of celery_ will normally be taken care of by whichever component
or extension utilizes it so we skip that here.

.. _celery: http://celeryproject.org/

To run the celery daemon you have two options:

1. In development setup you can just use paster. This can be done as simply
   as::

     paster celeryd

   This only works if you have a ``development.ini`` file in ckan root.

2. In production, the daemon should be run with a different ini file and be run
   as an init script. The simplest way to do this is to install supervisor::

     apt-get install supervisor

   Using this file as a template and copy to ``/etc/supservisor/conf.d``::

     https://github.com/ckan/ckan/blob/master/ckan/config/celery-supervisor.conf

   Alternatively, you can run::

     paster celeryd --config=/path/to/file.ini


Writing background tasks
==========================

These instructions should show you how to write an background task and how to
call it from inside CKAN or another extension using celery.

Examples
--------

Here are some existing real examples of writing CKAN tasks:

* https://github.com/ckan/ckanext-archiver
* https://github.com/ckan/ckanext-qa
* https://github.com/ckan/ckanext-datastorer

Setup
-----

An entry point is required inside the ``setup.py`` for your extension, and so
you should add something resembling the following that points to a function in
a module. In this case the function is called task_imports in the
``ckanext.NAME.celery_import`` module::

  entry_points = """
    [ckan.celery_task]
    tasks = ckanext.NAME.celery_import:task_imports
  """

The function, in this case ``task_imports`` should be a function that returns
fully qualified module paths to modules that contain the defined task (see the
next section).  In this case we will put all of our tasks in a file called
``tasks.py`` and so ``task_imports`` should be in a file called
``ckanext/NAME/celery_import.py``::

  def task_imports():
    return ['ckanext.NAME.tasks']

This returns an iterable of all of the places to look to find tasks, in this
example we are only putting them in one place.


Implementing the tasks
----------------------

The most straightforward way of defining tasks in our ``tasks.py`` module, is
to use the decorators provided by celery. These decorators make it easy to just
define a function and then give it a name and make it accessible to celery.
Make sure you import celery from ckan.lib.celery_app::

  from ckan.lib.celery_app import celery

Implement your function, specifying the arguments you wish it to take. For our
sample we will use a simple echo task that will print out its argument to the
console::

  def echo( message ):
    print message

Next it is important to decorate your function with the celery task decorator.
You should give the task a name, which is used later on when calling the task::

  @celery.task(name = "NAME.echofunction")
  def echo( message ):
    print message

That's it, your function is ready to be run asynchronously outside of the main
execution of the CKAN app.  Next you should make sure you run ``python setup.py
develop`` in your extensions folder and then go to your CKAN installation
folder (normally pyenv/src/ckan/) to run the following command::

  paster celeryd

Once you have done this your task name ``NAME.echofunction`` should appear in
the list of tasks loaded. If it is there then you are all set and ready to go.
If not then you should try the following to try and resolve the problem:

1. Make sure the entry point is defined correctly in your ``setup.py`` and that
   you have executed ``python setup.py develop``
2. Check that your task_imports function returns an iterable with valid module
   names in
3. Ensure that the decorator marks the functions (if there is more than one
   decorator, make sure the celery.task is the first one - which means it will
   execute last).
4. If none of the above helps, go into #ckan on irc.freenode.net where there
   should be people who can help you resolve your issue.

Calling the task
----------------

Now that the task is defined, and has been loaded by celery it is ready to be
called.  To call a background task you need to know only the name of the task,
and the arguments that it expects as well as providing it a task id.::

  import uuid
  from ckan.lib.celery_app import celery
  celery.send_task("NAME.echofunction", args=["Hello World"], task_id=str(uuid.uuid4()))

After executing this code you should see the message printed in the console
where you ran ``paster celeryd``.


Retrying on errors
------------------

Should your task fail to complete because of a transient error, it is possible
to ask celery to retry the task, after some period of time.  The default wait
before retrying is three minutes, but you can optionally specify this in the
call to retry via the countdown parameter, and you can also specify the
exception that triggered the failure.  For our example the call to retry would
look like the following - note that it calls the function name, not the task
name given in the decorator::

  try:
    ... some work that may fail, http request?
  except Exception, e:
    # Retry again in 2 minutes
    echo.retry(args=(message), exc=e, countdown=120, max_retries=10)

If you don't want to wait a period of time you can use the eta datetime
parameter to specify an explicit time to run the task (i.e. 9AM tomorrow)
