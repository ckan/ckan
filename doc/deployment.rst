==========================
Deploying a source install
==========================

Once you've installed CKAN from source by following the instructions in
:doc:`install-from-source`, you can follow these instructions to deploy
your CKAN site using a production web server (Apache), so that it's available
to the Internet.

.. note::

   If you installed CKAN from package you don't need to follow this section,
   your site is already deployed using Apache and modwsgi as described below.

Because CKAN uses WSGI, a standard interface between web servers and Python web
applications, CKAN can be used with a number of different web server and
deployment configurations including:

* Apache_ with the modwsgi Apache module proxied with Nginx_ for caching
* Apache_ with the modwsgi Apache module
* Apache_ with paster and reverse proxy
* Nginx_ with paster and reverse proxy
* Nginx_ with uwsgi

.. _Apache: http://httpd.apache.org/
.. _Nginx: http://nginx.org/

This guide explains how to deploy CKAN using Apache and modwsgi and proxied
with Nginx on an Ubuntu server. These instructions have been tested on Ubuntu
12.04.

If run into any problems following these instructions, see `Troubleshooting`_
below.

-----------------------------------
1. Create a ``production.ini`` File
-----------------------------------

Create your site's ``production.ini`` file, by copying the ``development.ini``
file you created in :doc:`install-from-source` earlier:

.. parsed-literal::

    cp |development.ini| |production.ini|


-----------------------------
2. Install Apache and modwsgi
-----------------------------

Install Apache_ (a web server) and modwsgi_ (an Apache module that adds WSGI
support to Apache)::

  sudo apt-get install apache2 libapache2-mod-wsgi

.. _modwsgi: https://code.google.com/p/modwsgi/


----------------
3. Install Nginx
----------------

Install Nginx_ (a web server) which will proxy the content from Apache_ and add
a layer of caching::

    sudo apt-get install nginx

--------------------------
4. Install an email server
--------------------------

If one isn't installed already, install an email server to enable CKAN's email
features (such as sending traceback emails to sysadmins when crashes occur, or
sending new activity :doc:`email notifications <email-notifications>` to
users). For example, to install the `Postfix <http://www.postfix.org/>`_ email
server, do::

    sudo apt-get install postfix

When asked to choose a Postfix configuration, choose *Internet Site* and press
return.


------------------------------
5. Create the WSGI script file
------------------------------

Create your site's WSGI script file |apache.wsgi| with the following
contents:

.. parsed-literal::

    import os
    activate_this = os.path.join('|virtualenv|/bin/activate_this.py')
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


--------------------------------
6. Create the Apache config file
--------------------------------

Create your site's Apache config file at |apache_config_file|, with the
following contents:

.. parsed-literal::

    <VirtualHost 0.0.0.0:8080>
        ServerName default.ckanhosted.com
        ServerAlias www.default.ckanhosted.com
        WSGIScriptAlias / |apache.wsgi|

        # Pass authorization info on (needed for rest api).
        WSGIPassAuthorization On

        # Deploy as a daemon (avoids conflicts between CKAN instances).
        WSGIDaemonProcess ckan_default display-name=ckan_default processes=2 threads=15

        WSGIProcessGroup ckan_default

        ErrorLog /var/log/apache2/ckan_default.error.log
        CustomLog /var/log/apache2/ckan_default.custom.log combined
    </VirtualHost>

Replace ``default.ckanhosted.com`` and ``www.default.ckanhosted.com`` with the
domain name for your site.

This tells the Apache modwsgi module to redirect any requests to the web server
to the WSGI script that you created above. Your WSGI script in turn directs the
requests to your CKAN instance.

-------------------------------
7. Create the Nginx config file
-------------------------------

Create your site's Nginx config file at |nginx_config_file|, with the
following contents:

.. parsed-literal::

    proxy_cache_path /tmp/nginx_cache levels=1:2 keys_zone=cache:30m max_size=250m;
    proxy_temp_path /tmp/nginx_proxy 1 2;

    server {
        client_max_body_size 100M;
        location / {
            proxy_pass http://127.0.0.1:8080/;
            proxy_set_header Host $host;
            proxy_cache cache;
            proxy_cache_bypass $cookie_auth_tkt;
            proxy_no_cache $cookie_auth_tkt;
            proxy_cache_valid 30m;
            proxy_cache_key $host$scheme$proxy_host$request_uri;
            # In emergency comment out line to force caching
            # proxy_ignore_headers X-Accel-Expires Expires Cache-Control;
        }

    }


------------------------
8. Enable your CKAN site
------------------------

Finally, enable your CKAN site in Apache:

.. parsed-literal::

    sudo a2ensite ckan_default
    sudo ln -s |nginx_config_file| /etc/nginx/sites-enabled/ckan_default
    |reload_apache|
    |reload_nginx|

You should now be able to visit your server in a web browser and see your new
CKAN instance.


---------------
Troubleshooting
---------------

Default Apache welcome page
===========================

If you see a default Apache welcome page where your CKAN front page should be,
it may be because the default Apache config file is overriding your CKAN config
file (both use port 80), so disable it and restart Apache:

.. parsed-literal::

    sudo a2dissite default
    |reload_apache|

403 Forbidden and 500 Internal Server Error
===========================================

If you see a 403 Forbidden or 500 Internal Server Error page where your CKAN
front page should be, you may have a problem with your unix file permissions.
The Apache web server needs to have permission to access your WSGI script file
and all of its parent directories. The permissions of the file should look
like ``-rw-r--r--`` and the permissions of each of its parent directories
should look like ``drwxr-xr-x``.

IOError: sys.stdout access restricted by mod_wsgi
=================================================

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

Log files
=========

In general, if it's not working look in the log files in ``/var/log/apache2``
for error messages. ``ckan_default.error.log`` should be particularly
interesting.

modwsgi wiki
============

Some pages on the modwsgi wiki have some useful information for troubleshooting modwsgi problems:

* https://code.google.com/p/modwsgi/wiki/ApplicationIssues
* http://code.google.com/p/modwsgi/wiki/DebuggingTechniques
* http://code.google.com/p/modwsgi/wiki/QuickConfigurationGuide
* http://code.google.com/p/modwsgi/wiki/ConfigurationGuidelines
* http://code.google.com/p/modwsgi/wiki/FrequentlyAskedQuestions
* http://code.google.com/p/modwsgi/wiki/ConfigurationIssues
