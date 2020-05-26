==========================
Deploying a source install
==========================

Once you've installed CKAN from source by following the instructions in
:doc:`install-from-source`, you can follow these instructions to deploy
your CKAN site using a rudimentary web server, so that it's available
to the Internet.

Because CKAN uses WSGI, a standard interface between web servers and Python web
applications, CKAN can be used with a number of different web server and
deployment configurations including:

* Nginx_ with uwsgi
* Nginx_ with gunicorn
* Apache_ with the modwsgi Apache module

.. _uwsgi: https://uwsgi-docs.readthedocs.io/en/latest/
.. _gunicorn: https://gunicorn.org/
.. _Apache: http://httpd.apache.org/
.. _Nginx: http://nginx.org/
.. _Supervisor: http://http://supervisord.org/

This guide explains how to deploy CKAN using a WSGI web server and proxied
with Nginx on an Ubuntu server. These instructions have been tested on Ubuntu
18.04.


----------------
1. Install Nginx
----------------

Install Nginx_ (a web server) which will proxy the content from one of the WSGI Servers 
and add a layer of caching::

    sudo apt-get install nginx


.. _create-wsgi-script-file:

------------------------------
2. Create the WSGI script file
------------------------------

Create your site's WSGI script file |wsgi.py| with the following
contents:

.. parsed-literal::

    import os
    from ckan.config.middleware import make_app
    from ckan.cli import CKANConfigLoader
    from logging.config import fileConfig as loggingFileConfig
    config_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ckan.ini')
    abspath = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    loggingFileConfig(config_filepath)
    config = CKANConfigLoader(config_filepath).get_config()
    application = make_app(config)

The WSGI Server (configured next) will redirect requests to this
WSGI script file. The script file then handles those requests by directing them
on to your CKAN instance (after first configuring the Python environment for
CKAN to run in).


-------------------------
3. Create the WSGI Server
-------------------------

There is a choice of 3 different WSGI Servers. We recommend one of the first two options (uwsgi or gunicorn)
Make sure you have activated the Python virtual environment before running these commands:  |activate|


a. uwsgi
---------

Run ``pip install uwsgi``
Create the uwsgi configuration file ``/etc/ckan/default/ckan-uwsgi.ini``

.. parsed-literal::
    [uwsgi]

    http            =  127.0.0.1:8080
    uid             =  www-data
    guid            =  www-data
    wsgi-file       =  /etc/ckan/default/wsgi.py
    virtualenv      =  /usr/lib/ckan/default
    module          =  wsgi:application
    master          =  true
    pidfile         =  /tmp/%n.pid
    harakiri        =  50
    max-requests    =  5000
    vacuum          =  true
    callable        =  application  

Run: ``/usr/lib/ckan/default/bin/uwsgi -i /etc/ckan/default/ckan-uwsgi.ini``    


b. gunicorn
------------

Run ``pip install gunicorn``
Create the gunicorn configuration file ``/etc/ckan/default/ckan-gunicorn.ini``

.. parsed-literal::
    pidfile = '/tmp/gunicorn.pid'
    chdir = '/etc/ckan/default'
    errorlog = '/etc/ckan/default/gunicorn.ERR'
    accesslog = '/etc/ckan/default/gunicorn.OUT'
    loglevel = 'debug'
    bind = '127.0.0.1:8080'
    daemon = True
    workers = 4
    worker_class = 'sync'
    threads = 2
    user = 'www-data'
    group = 'www-data'  

Run: ``/usr/lib/ckan/default/bin/uwsgi -i /etc/ckan/default/ckan-uwsgi.ini``    


c. Apache
----------

Install Apache_ (a web server), modwsgi_ (an Apache module that adds WSGI
support to Apache), and modrpaf_ (an Apache module that sets the right IP
address when there is a proxy forwarding to Apache)::

  sudo apt-get install apache2 libapache2-mod-wsgi-py3 libapache2-mod-rpaf

.. _modwsgi: https://code.google.com/p/modwsgi/
.. _modrpaf: https://github.com/gnif/mod_rpaf

Note: For python 2 change this to:
.. parsed-literal::
   sudo apt-get install apache2 libapache2-mod-wsgi libapache2-mod-rpaf


Create your site's Apache config file at |apache_config_file|, with the
following contents:

.. parsed-literal::

    <VirtualHost 127.0.0.1:8080>
        ServerName default.ckanhosted.com
        ServerAlias www.default.ckanhosted.com
        WSGIScriptAlias / |apache.wsgi|

        # Pass authorization info on (needed for rest api).
        WSGIPassAuthorization On

        # Deploy as a daemon (avoids conflicts between CKAN instances).
        WSGIDaemonProcess ckan_default display-name=ckan_default processes=2 threads=10 python-home=/usr/lib/ckan/default

        WSGIProcessGroup ckan_default

        ErrorLog /var/log/apache2/ckan_default.error.log
        CustomLog /var/log/apache2/ckan_default.custom.log combined

        <IfModule mod_rpaf.c>
            RPAFenable On
            RPAFsethostname On
            RPAFproxy_ips 127.0.0.1
        </IfModule>

        <Directory />
            Require all granted
        </Directory>

    </VirtualHost>

Replace ``default.ckanhosted.com`` and ``www.default.ckanhosted.com`` with the
domain name for your site.

This tells the Apache modwsgi module to redirect any requests to the web server
to the WSGI script that you created above. Your WSGI script in turn directs the
requests to your CKAN instance.

Open ``/etc/apache2/ports.conf``. We need to replace the default port 80 with the 8080 one.


   - On Apache 2.4 (eg Ubuntu 18.04 or RHEL 7):

     Replace this line:

        .. parsed-literal::

            Listen 80

     With this one:

        .. parsed-literal::

            Listen 8080

Finally create a softlink for Apache to the WSGI script  ``ln -s |wsgi.py| |apache.wsgi|``

To prevent conflicts, disable your default nginx and apache sites.  Finally, enable your CKAN site in Apache:

.. parsed-literal::

    sudo a2ensite ckan_default
    sudo a2dissite 000-default
    sudo rm -vi /etc/nginx/sites-enabled/default
    sudo ln -s |nginx_config_file| /etc/nginx/sites-enabled/ckan_default
    |reload_apache|
    |restart_nginx|


-------------------------------------------------------
4. Install Supervisor for the uwsgi or gunicorn servers
-------------------------------------------------------

Install Supervisor_ (a Process Control System) used to control starting, stopping the 
uwsgi or gunicorn servers::

  sudo apt-get install supervisor
  sudo service supervisor restart

a. uwsgi

Create the  ``/etc/supervisor/conf.d/ckan-uwsgi.conf`` file

.. parsed-literal::

    [program:ckan-uwsgi]

    command=/usr/lib/ckan/default/bin/uwsgi -i /etc/ckan/default/ckan-uwsgi.ini

    ; Start just a single worker. Increase this number if you have many or
    ; particularly long running background jobs.
    numprocs=1
    process_name=%(program_name)s-%(process_num)02d

    ; Log files - change this to point to the existing CKAN log files
    stdout_logfile=/etc/ckan/default/uwsgi.OUT
    stderr_logfile=/etc/ckan/default/uwsgi.ERR

    ; Make sure that the worker is started on system start and automatically
    ; restarted if it crashes unexpectedly.
    autostart=true
    autorestart=true

    ; Number of seconds the process has to run before it is considered to have
    ; started successfully.
    startsecs=10

    ; Need to wait for currently executing tasks to finish at shutdown.
    ; Increase this if you have very long running tasks.
    stopwaitsecs = 600

    ; Required for uWSGI as it does not obey SIGTERM.
    stopsignal=QUIT
    
b. gunicorn

Create the  ``/etc/supervisor/conf.d/ckan-uwsgi.conf`` file

.. parsed-literal::

    [program:ckan-uwsgi]

    command=/usr/lib/ckan/default/bin/uwsgi -i /etc/ckan/default/ckan-uwsgi.ini

    ; Start just a single worker. Increase this number if you have many or
    ; particularly long running background jobs.
    numprocs=1
    process_name=%(program_name)s-%(process_num)02d

    ; Log files - change this to point to the existing CKAN log files
    stdout_logfile=/etc/ckan/default/uwsgi.OUT
    stderr_logfile=/etc/ckan/default/uwsgi.ERR

    ; Make sure that the worker is started on system start and automatically
    ; restarted if it crashes unexpectedly.
    autostart=true
    autorestart=true

    ; Number of seconds the process has to run before it is considered to have
    ; started successfully.
    startsecs=10

    ; Need to wait for currently executing tasks to finish at shutdown.
    ; Increase this if you have very long running tasks.
    stopwaitsecs = 600

    ; Required for uWSGI as it does not obey SIGTERM.
    stopsignal=QUIT


--------------------------
5. Install an email server
--------------------------

If one isn't installed already, install an email server to enable CKAN's email
features (such as sending traceback emails to sysadmins when crashes occur, or
sending new activity :doc:`email notifications </maintaining/email-notifications>`
to users). For example, to install the `Postfix <http://www.postfix.org/>`_
email server, do::

    sudo apt-get install postfix

When asked to choose a Postfix configuration, choose *Internet Site* and press
return.



-------------------------------
6. Create the Nginx config file
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
            proxy_set_header X-Forwarded-For $remote_addr;
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

Now restart the nginx server: |restart_nginx|


------------------------
7. Access your CKAN site
------------------------

You should now be able to visit your server in a web browser and see your new
CKAN instance.


--------------------------------------
8. Setup a worker for background jobs
--------------------------------------
CKAN uses asynchronous :ref:`background jobs` for long tasks. These jobs are
executed by a separate process which is called a :ref:`worker <background jobs
workers>`.

To run the worker in a robust way, :ref:`install and configure Supervisor
<background jobs supervisor>`.



.. _deployment-changes-for-ckan-2.9:

-------------------------------
Deployment changes for CKAN 2.9
-------------------------------

This section describes how to update your deployment for CKAN 2.9 or later, if
you have an existing deployment of CKAN 2.8 or earlier. This is necessary,
whether you continue running CKAN on Python 2 or Python 3, because the WSGI
entry point for running CKAN has changed. If your existing deployment is
different to that described in the `official CKAN 2.8 deployment instructions
<https://docs.ckan.org/en/2.8/maintaining/installing/deployment.html>`_
(apache2 + mod_wsgi + nginx) then you'll need to adapt these instructions to
your setup.

1. We now recommend you activate the Python virtual environment in a different
place, compared to earlier CKAN versions. Activation is now done in the WSGI Server 
config file.

(In CKAN 2.8.x and earlier, the virtual environment was activated in the WSGI
script file.)

2. There is now a choice of 3 different WSGI Servers. We recommend one of the first two options 
(uwsgi or gunicorn). Apache is not the prefered option any more.

2. The WSGI script file needs replacing because the WSGI entrypoint for CKAN
has `changed <https://github.com/ckan/ckan/issues/4802>`_. Back-up your
existing |apache.wsgi| file and then replace it with the new version defined
above - see: :ref:`create-wsgi-script-file`

3. For Apache, if/when you are switching from running CKAN with Python 2 to Python 3,
you'll need to switch to the Python 3 version of the Apache WSGI module:

.. parsed-literal::

    sudo apt-get remove libapache2-mod-wsgi
    sudo apt-get install libapache2-mod-wsgi-py3
    |reload_apache|