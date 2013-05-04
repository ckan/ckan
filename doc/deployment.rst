===============
CKAN Deployment
===============

.. note:: If you use the package installation method your site will already
          have been deployed using the Apache and modwsgi route described
          below.

This document covers how to deploy CKAN in a production setup where it is
available on the Internet. This will usually involve connecting the CKAN web
application to a web server such as Apache_ or NGinx_.

As CKAN uses WSGI, a standard interface between web servers and Python web
applications, CKAN can be used with a number of different web server and
deployment configurations including:

* Apache_ with the modwsgi Apache module
* Apache_ with paster and reverse proxy
* Nginx_ with paster and reverse proxy
* Nginx_ with uwsgi

.. _Apache: http://httpd.apache.org/
.. _Nginx: http://wiki.nginx.org/Main


Deploying CKAN on Ubuntu using Apache and modwsgi
=================================================

Once you've installed CKAN on your Ubuntu server by following the instructions
in :doc:`install-from-source`, you can follow these instructions to deploy your
site using Apache and modwsgi.


Install Apache and modwsgi
--------------------------

Install Apache_ (a web server) and modwsgi_ (an Apache module that adds WSGI
support to Apache)::

  sudo aptitude install apache2 libapache2-mod-wsgi

.. _modwsgi: https://code.google.com/p/modwsgi/ 


Create the ``production.ini`` File
----------------------------------

We'll continue with the ``http://masaq.ckanhosted.com`` example from
:doc:`install-from-source`. Create your site's ``production.ini`` file, by
copying the ``development.ini`` file you created in :doc:`install-from-source`
earlier::

   cp /etc/ckan/masaq/development.ini /etc/ckan/masaq/production.ini


Create the WSGI Script File
---------------------------

Create your site's WSGI script file
``/etc/ckan/masaq/apache.wsgi`` with the following contents::

    import os
    activate_this = os.path.join('/usr/lib/ckan/masaq/bin/activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))

    from paste.deploy import loadapp
    config_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'production.ini')
    from paste.script.util.logging_config import fileConfig
    fileConfig(config_filepath)
    application = loadapp('config:%s' % config_filepath)


The modwsgi Apache module will redirect requests to your web server to this
WSGI script file. The script file then handles those requests by directing them
on to your CKAN instance (after first configuring the Python environment for
CKAN to run in).

Create the Apache Config File
-----------------------------

Create your site's Apache config file at
``/etc/apache2/sites-available/masaq``, with the following
contents::

    <VirtualHost 0.0.0.0:8080>
        ServerName masaq.ckanhosted.com
        ServerAlias www.masaq.ckanhosted.com
        WSGIScriptAlias / /etc/ckan/masaq/apache.wsgi

        # Pass authorization info on (needed for rest api).
        WSGIPassAuthorization On

        # Deploy as a daemon (avoids conflicts between CKAN instances).
        WSGIDaemonProcess masaq display-name=masaq processes=2 threads=15

        WSGIProcessGroup masaq

        ErrorLog /var/log/apache2/masaq.error.log
        CustomLog /var/log/apache2/masaq.custom.log combined
    </VirtualHost>

This tells the Apache modwsgi module to redirect any requests to the web server
to the CKAN WSGI script that you created above (``masaq.py``).
Your WSGI script in turn directs the requests to your CKAN instance.


Set the ``data`` and ``sstore`` Directory Permissions
-----------------------------------------------------

Make sure that Apache's user (``www-data`` on Ubuntu) has permission to write to
the site's ``data`` and ``sstore`` directories::

    chmod g+w -R /etc/ckan/masaq/data /etc/ckan/masaq/sstore
    sudo chgrp -R www-data /etc/ckan/masaq/data /etc/ckan/masaq/sstore


Enable Your CKAN Site
---------------------

Finally, enable your CKAN site in Apache::

    sudo a2ensite masaq
    sudo /etc/init.d/apache2 reload

You should now be able to visit your server in a web browser and see your new
CKAN instance.


Troubleshooting
---------------

Default Apache Welcome Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you see a default Apache welcome page where your CKAN front page should be,
it may be because the default Apache config file is overriding your CKAN config
file (both use port 80), so disable it and restart Apache::

    sudo a2dissite default
    sudo /etc/init.d/apache2 reload

403 Forbidden and 500 Internal Server Error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you see a 403 Forbidden or 500 Internal Server Error page where your CKAN
front page should be, you may have a problem with your unix file permissions.
The Apache web server needs to have permission to access your WSGI script file
and all of its parent directories''. The permissions of the file should look
like ``-rw-r--r--`` and the permissions of each of its parent directories
should look like ``drwxr-xr-x``.

IOError: sys.stdout access restricted by mod_wsgi
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're getting 500 Internal Server Error pages and you see ``IOError:
sys.stdout access restricted by mod_wsgi`` in your log files, it means that
something in your WSGI application (e.g. your WSGI script file, your CKAN
instance, or one of your CKAN extensions) is trying to print to stdout, for
example by using standard Python ``print`` statements. WSGI applications are
not allowed to write to stdout. Possible solutions include:

1. Remove the offending print statements. One option is to replace print
   statements with statements like ``print >> sys.stderr, "..."``

2. Redirect all print statements to stderr::

    import sys
    sys.stdout = sys.stderr

3. Allow your application to print to stdout by putting ``WSGIRestrictStdout Off`` in your Apache config file (not recommended).

Also see https://code.google.com/p/modwsgi/wiki/ApplicationIssues

Log Files
~~~~~~~~~

In general, if it's not working look in the log files in ``/var/log/apache2``
for error messages. Your ``*.error.log`` should be particularly interesting.

modwsgi wiki
~~~~~~~~~~~~

Some pages on the modwsgi wiki have some useful information for troubleshooting modwsgi problems:

* https://code.google.com/p/modwsgi/wiki/ApplicationIssues
* http://code.google.com/p/modwsgi/wiki/DebuggingTechniques
* http://code.google.com/p/modwsgi/wiki/QuickConfigurationGuide
* http://code.google.com/p/modwsgi/wiki/ConfigurationGuidelines
* http://code.google.com/p/modwsgi/wiki/FrequentlyAskedQuestions
* http://code.google.com/p/modwsgi/wiki/ConfigurationIssues


Mounting CKAN at a non-root URL
===============================

CKAN (since version 1.6) can run mounted at a 'sub-directory' URL, such as
http://mysite.com/data/. This is achieved by changing the WSGIScriptAlias first
parameter (in the Apache site config). e.g.::

  WSGIScriptAlias /data /etc/ckan/masaq/apache.wsgi
