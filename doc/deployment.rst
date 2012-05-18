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

.. note:: below, we will only be able to give a few example of setups and many
          other ones are possible.

.. _Apache: http://httpd.apache.org/
.. _Nginx: http://wiki.nginx.org/Main

Deploying CKAN on an Ubuntu Server using Apache and modwsgi
===========================================================

These instructions have been tested on Ubuntu 10.04 with CKAN 1.7.

This is the standard way to deploy CKAN.

Install Apache and modwsgi
--------------------------

Install Apache_ (a web server) and modwsgi_ (an Apache module that adds WSGI
support to Apache)::

  sudo aptitude install apache2 libapache2-mod-wsgi

.. _modwsgi: https://code.google.com/p/modwsgi/ 

Install CKAN
------------

The following assumes you have installed to ``/usr/local/demo.ckan.net`` with your virtualenv at ``/usr/local/demo.ckan.net/pyenv``.

Create the WSGI Script File
---------------------------

Create the WSGI script file for your CKAN instance,
``/usr/local/demo.ckan.net/pyenv/bin/demo.ckan.net.py``::

    import os
    instance_dir = '/usr/local/demo.ckan.net'
    config_file = '/usr/local/demo.ckan.net/pyenv/src/ckan/development.ini'
    pyenv_bin_dir = os.path.join(instance_dir, 'pyenv', 'bin')
    activate_this = os.path.join(pyenv_bin_dir, 'activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))
    from paste.deploy import loadapp
    config_filepath = os.path.join(instance_dir, config_file)
    from paste.script.util.logging_config import fileConfig
    fileConfig(config_filepath)
    application = loadapp('config:%s' % config_filepath)

The modwsgi Apache module will redirect requests to your web server to this
WSGI script file. The script file then handles those requests by directing them
on to your CKAN instance (after first configuring the Python environment for
CKAN to run in).

Create the Apache Config File
-----------------------------

Create the Apache config file for your CKAN instance by copying the default
Apache config file:

    cd /etc/apache2/sites-available
    sudo cp default demo.ckan.net

Edit ``/etc/apache2/sites-available/demo.ckan.net``, before the last line
(``</VirtualHost>``) add these lines::

    ServerName demo.ckan.net
    ServerAlias demo.ckan.net
    WSGIScriptAlias / /usr/local/demo.ckan.net/pyenv/bin/demo.ckan.net.py

    # pass authorization info on (needed for rest api)
    WSGIPassAuthorization On
    ErrorLog /var/log/apache2/demo.ckan.net.error.log
    CustomLog /var/log/apache2/demo.ckan.net.custom.log combined

This tells the Apache modwsgi module to redirect any requests to the web server
to the CKAN WSGI script that you created above (``demo.ckan.net.py``). Your
WSGI script in turn directs the requests to your CKAN instance.


Create Directories for CKAN's Temporary Files
---------------------------------------------

Make the data and sstore directories and give them the right permissions::

    cd /usr/local/demo.ckan.net/pyenv/src/ckan/
    mkdir data sstore
    chmod g+w -R data sstore
    sudo chgrp -R www-data data sstore

CKAN Log File
-------------

Edit your CKAN config file (e.g.
``/usr/local/demo.ckan.net/pyenv/src/ckan/development.ini``), find this line::

    args = ("ckan.log", "a", 20000000, 9)

and change it to set the ckan.log file location to somewhere that CKAN can write to, e.g.::

    args = ("/var/log/ckan/demo.ckan.net/ckan.log", "a", 20000000, 9)

Then create that directory and give it the right permissions::

    sudo mkdir -p /var/log/ckan/demo.ckan.net
    sudo chown www-data /var/log/ckan/demo.ckan.net

Enable Your CKAN Site
---------------------

Finally, enable your CKAN site in Apache::

    sudo a2ensite demo.ckan.net   
    sudo /etc/init.d/apache2 restart

You should now be able to visit your server in a web browser and see your new
CKAN instance.

Troubleshooting
---------------

Default Apache Welcome Page
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you see a default Apache welcome page where your CKAN front page should be,
it may be because the default Apache config file is overriding your CKAN config
file (both use port 80), so disable it and restart Apache::

    $ sudo a2dissite default
    $ sudo /etc/init.d/apache2 restart

403 Forbidden and 500 Internal Server Error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you see a 403 Forbidden or 500 Internal Server Error page where your CKAN
front page should be, you may have a problem with your unix file permissions.
The Apache web server needs to have permission to access your WSGI script file
(e.g. ``/usr/local/demo.ckan.net/pyenv/bin/demo.ckan.net.py``) ''and all of its
parent directories''. The permissions of the file should look like
``-rw-r--r--`` and the permissions of each of its parent directories should
look like ``drwxr-xr-x``.

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
for error messages. ``demo.ckan.net.error.log`` should be particularly
interesting.

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

  WSGIScriptAlias /data /home/dread/etc/ckan-pylons.py

CORS
====

**As of CKAN v1.5 CORS is built in to CKAN so for CKAN >= 1.5 no modifications
to your webserver config are needed.**

CORS = Cross Origin Resource Sharing. It is away to allow browsers (and hence
javascript in browsers) make requests to domains other than the one the browser
is currently on.

In Apache you can enable CORS for you CKAN site by setting the following in
your config::

    Header always set Access-Control-Allow-Origin "*"
    Header always set Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
    Header always set Access-Control-Allow-Headers "X-CKAN-API-KEY, Content-Type"

    # Respond to all OPTIONS requests with 200 OK
    # This could be done in the webapp
    # This is need for pre-flighted requests (POSTs/PUTs)
    RewriteEngine On
    RewriteCond %{REQUEST_METHOD} OPTIONS
    RewriteRule ^(.*)$ $1 [R=200,L]

