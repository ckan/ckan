Upgrade
=======

Ideally production deployments should be upgraded with fabric, but here are the manual instructions.

1. Activate the virtual environment for your install::

   $ cd ~/var/srvc/demo.ckan.net
   $ . pyenv/bin/activate

2. It's probably wise to backup your database::

   $ paster --plugin=ckan db dump demo_ckan_backup.pg_dump --config=demo.ckan.net.ini

3. Get a version of pip-requirements.txt for the new version you want to install (see info on finding a suitable tag name above)::

   $ wget https://bitbucket.org/okfn/ckan/raw/ckan-1.4/pip-requirements.txt

4. Update all the modules::

   $ pip -E pyenv install -r pip-requirements.txt

5. Upgrade the database::

   $ paster --plugin ckan db upgrade --config {config.ini}

6. Restart apache (so modpython has the latest code)::

   $ sudo /etc/init.d/apache2 restart

7. You could manually try CKAN works in a browser, or better still run the smoke tests found in ckanext/blackbox. To do this, install ckanext and run ckanext from another machine - see ckanext README.txt for instructions: https://bitbucket.org/okfn/ckanext and then run::

   $ python blackbox/smoke.py blackbox/ckan.net.profile.json

