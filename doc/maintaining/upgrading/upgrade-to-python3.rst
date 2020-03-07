==================================================
Upgrading a CKAN install from Python 2 to Python 3
==================================================

These instructions describe how to upgrade a source install of CKAN 2.9 from
Python 2 to Python 3, which is necessary because Python 2 is end of life, as of
January 1st, 2020.

Preparation
-----------

* Backup your CKAN source, virtualenv and databases, just in case.
* Upgrade to CKAN 2.9, if you've not done already.

Upgrade
-------

You'll probably need to deactivate your existing virtual environment::

    deactivate

The existing setup has the virtual environment here: |virtualenv|
and the CKAN source code underneath in `/usr/lib/ckan/default/src`. We'll move
that aside in case we need to roll-back:

   .. parsed-literal::

    sudo mv |virtualenv| /usr/lib/ckan/py2

From this doc: :doc:`/maintaining/installing/install-from-source` you need to
do these sections:

* 1. Install the required packages
* 2. Install CKAN into a Python virtual environment
* 6. Link to who.ini

Deployment
----------

For full details of the recommended deployment (Apache, mod_wsgi, nginx) see:
:doc:`deployment`. Here we detail the changes from the previous instructions.

1. Now we should activate your Python virtual environment in your Apache mod_wsgi
config. Edit |apache_config_file| and change the WSGIDaemonProcess to include
the ``python-home``::

    WSGIDaemonProcess ckan_default display-name=ckan_default processes=2 threads=15 python-home=/usr/lib/ckan/default

(The virtual environment was previously activated in the WSGI script file,
however it used the activate_this.py script provided by virtualenv, however now
we use 'venv' which is bundled with python3.)

2. The WSGI script file needs replacing. Copy the new |apache.wsgi| defined in
the deployment doc: :ref:`create-wsgi-script-file`
