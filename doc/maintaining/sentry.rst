===================
Logging with Sentry
===================

Basic CKAN operation means uncaught exceptions get emailed to the sysadmin and
explicit log.error and log.warning messages go in a log file. This is fine when
starting up a site, since you'll only have a few exception emails and they help
you fix things, and you'll consult the log file to answer questions if
something isn't right. But when you're live, getting thousands of requests,
should PostgreSQL go down, or you deploy some bad code in a CKAN extension for
example, you'll find yourself flooded with WebApp Error emails from CKAN -
perhaps hundreds a minute. And no-one can ever remember to read the log files
to look for underlying issues.

`Sentry <https://github.com/getsentry/sentry>`_ is one of many ways to deal
with this, bringing all these errors and warnings into one interface, to track
them over time, aggregate them and alert you by email according to your
preferences. 

CKAN has a convenient hook to feed these messages to Sentry if you configure
it. Other logging managers are available.

Setup and configuration
=======================

In order to use the Sentry integration you will need to install `Raven
<https://github.com/getsentry/raven-python>`_ the Python client for Sentry.

::

    pip install raven

The minimal configuration which needs to add to your CKAN configuration file is
the DSN of the project you wish to log to. The DSN can be found in the `Client
Configuration` section of the project settings on the Sentry Web site.

::

    sentry.dsn = 'http://public:secret@example.com/1'

More information about other configuration options can be found `here
<http://raven.readthedocs.org/en/latest/config/pylons.html>`_.

Stopping exception emails
=========================

Once you have configured CKAN to log to Sentry you probably won't need the
Error emails anymore. Simply unset the :ref:`email_to` value in your
``production.ini`` file.
