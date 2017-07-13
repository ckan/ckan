.. include:: /_substitutions.rst

===================================
Installing CKAN with docker-compose
===================================

This section describes how to install CKAN with docker-compose. The scenario shown here is one of
many possibile scenarios and environments in which CKAN can be used with Docker.


--------------
1. Environment
--------------
We will use a Ubuntu environment, so far this has been tested on:

* Amazon AWS EC2 Ubuntu 14.04 LTS
* Ubuntu 16.04 LTS on a desktop

Docker is installed system-wide following the official `Docker CE installation guidelines
<https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/>`_.

.. tip::

    Using a cloud based VM, external storage volumes are cheaper than VMs and easy to backup.
    In our use case, we use an EC2 with 16 GB storage, have mounted a 100 GB btrfs-formatted
    external storage volume, and symlinked ``/var/lib/docker`` to the external volume.
    This allows us to store the bulky and precious cargo -- Docker images, Docker data volumes
    containing the CKAN databases, filestore, and config -- on a cheaper service.
    On the other hand, a snapshotting filesystem like btrfs is ideal for backups, and it is easy to
    maintain rolling backups.
    The same cost consideration might apply to other cloud-based providers.

To verify a successful Docker installation, run ``docker run hello-world``.
``docker version`` should output versions for client and server.

-----------------------------
2. CKAN source and virtualenv
-----------------------------
In this step, we will create a virtualenv, clone the CKAN repository and install docker-compose.

a. virtualenvwrapper

While not essential, `virtualenvwrapper <http://virtualenvwrapper.readthedocs.io/en/latest/>`_
provides convenience methods to manage virtualenvs.

If using virtulenvwrapper, append the following lines (using your preferred and existing locations
for virtualenvs and projects) to ``~/.bashrc``::

    export WORKON_HOME=$HOME/.venvs
    export PROJECT_HOME=/path/to/projects
    source /usr/local/bin/virtualenvwrapper.sh
    export PIP_VIRTUALENV_BASE=WORKON_HOME

b. Create virtualenv for CKAN

If using virtualenvwrapper, create a virtualenv for CKAN with ``mkproject ckan``, else follow
the virtulenv setup instructions in :doc:`install-from-source`.

To verify a successful virtualenvwrapper setup for CKAN, check that ``workon ckan`` will jump you
into the CKAN project directory (``/path/to/projects/ckan`` in our example)
and activate the CKAN virtualenv (``~/.venvs/ckan``).

c. Clone CKAN source

Clone CKAN into the activated virtualenv::

    workon ckan
    git clone git@github.com:ckan/ckan.git .

d. Install docker-compose

In the  activated virtualenv, install and verify docker-compose using pip::

    workon ckan
    pip install docker-compose
    docker-compose version

----------------------
3. Build Docker images
----------------------
In this step we will build the Docker images and create Docker data volumes with user-defined,
sensitive settings (e.g. for database passwords).

a. Sensitive settings

In a production environment, copy ``contrib/docker/.env.template`` to ``contrib/docker/.env``
and follow instructions within to set passwords and other sensitive or user-defined variables.
The very unimaginative defaults will work fine in a development environment.

b. Build the images

With an activated virtualenv::

    workon ckan
    cd contrib/docker
    docker-compose build
    docker-compose up -d

For the remainder of this chapter, we assume that docker-compose commands are all run inside
``contrib/docker`` with the ``ckan`` virtualenv activated.

On first runs, the postgres container could need longer to initialise the database cluster than
the ckan container will wait for. In this case, simply restart the ckan container a few times::

    docker-compose restart ckan
    docker ps | grep ckan
    docker-compose logs -f ckan

After this step, CKAN should be running at ``CKAN_SITE_URL``.
There should be four containers running (``docker ps``)

* ``ckan``: CKAN with standard extensions
* ``db``: CKAN's database, later also running CKAN's datastore database
* ``redis``
* ``solr``

There should be four named Docker volumes (``docker volume ls | grep docker``). They will be
prefixed with the Docker project name (default: ``docker``)

* ``docker_ckan_config``: home of ckan.ini
* ``docker_ckan_home``: home of ckan venv and source, later also additional CKAN extensions
* ``docker_ckan_storage``: home of CKAN's filestore (resource files)
* ``docker_pg_data``: home of the database files for CKAN's default and datapusher databases

The location of these named volumes need to be backed up in a production environment.
To migrate CKAN data between different hosts, simply transfer the content of the named volumes.
A detailed use case of data transfer will be discussed later.

-------------------
4. Enable Datastore
-------------------
To enable the datastore, the datastore database and database users have to be created before
enabling the datastore and datapusher settings in the ``ckan.ini``.

a. Create and configure datastore database

With running CKAN containers, execute two prepared scripts against the ``db`` container::

    docker exec -it db psql -U ckan -f 00_create_datastore.sql
    docker exec -it db psql -U ckan -f 10_set_permissions.sql

The first script will create the datastore database and the datastore readonly user in the ``db``
container. The second script is the output of ``paster ckan set-permissions``.
The effect of these scripts is persisted in the named volume ``docker_pg_data``.

.. note:: We re-use the already privileged default user of the CKAN database as read/write user
    for the datastore. The database user (``ckan``) is hard-coded, the password is supplied through
    the``.env`` variable ``POSTGRES_PASSWORD``.
    A new user ``datastore_ro`` is created (and also hard-coded) as readonly user with password
    ``DATASTORE_READONLY_USER``.
    Hard-coding the database table and usernames allows to prepare the set-permissions SQL script,
    while not exposing sensitive information to the world outside the Docker host environment.

After this step, the datastore database is ready to be enabled in the ``ckan.ini``.

b. Enable datastore and datapusher in ``ckan.ini``

Find the path to the ``ckan.ini`` within the named volume::

    docker volume inspect docker_ckan_config | grep Mountpoint

    # "Mountpoint": "/var/lib/docker/volumes/docker_ckan_config/_data",

Edit the ``ckan.ini`` (note: requires sudo)::

    sudo vim /var/lib/docker/volumes/docker_ckan_config/_data/ckan.ini

    # filestore
    ckan.storage_path = /var/lib/ckan

    # datastore and datapusher
    # With your own POSTGRES_PASSWORD and DATASTORE_READONLY_USER:
    ckan.datastore.write_url = postgresql://ckan:POSTGRES_PASSWORD@db/datastore
    ckan.datastore.read_url = postgresql://datastore:DATASTORE_READONLY_PASSWORD@db/datastore
    # add datastore and datapusher to plugins
    # enable datapusher options

Restart the ``ckan`` container to apply changes to the ``ckan.ini``::

    docker-compose restart ckan

Now the datastore API should return content when visiting::

    CKAN_SITE_URL/api/3/action/datastore_search?resource_id=_table_metadata

TODO datapusher setup - own service / Dockerfile?


-------------------------
5. Create CKAN admin user
-------------------------
With all four Docker images up and running, create the CKAN admin user (johndoe in this example)::

    docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckan sysadmin -c /etc/ckan/default/ckan.ini add johndoe

Now you should be able to login to the new, empty CKAN.
The admin user's API key will be instrumental in tranferring data from other instances.

-----------------
6. Migrating data
-----------------
This section is a stub. Pending testing, and presuming same dataset schema (ckanext-scheming) on
source and target CKANs, the process should be as simple as:

* ``rsync`` contents of the filestore into the storage volume.
* Use python package ``ckanapi`` to dump orgs, groups and datasets from source CKAN instance, then
  to load into new instance.
* Let datapusher populate datastore.
* Trigger a Solr index rebuild.

--------------------
7. Adding extensions
--------------------
This section is a stub.

There are two use cases how to add extensions:

* Developers will want to have access to the extensions' source.
* Maintainers of production instances will want extensions to be part of the ``ckan`` image and an
  easy way to enable them in the ``ckan.ini``.

--------------------------------------------
8. Changing and adding environment variables
--------------------------------------------
This section is targetted at the CKAN developer seeking to factor out settings as new ``.env``
variables.

The flow of variable substitution is as follows:

* ``.env.template`` holds the defaults and the usage instructions for variables.
* ``.env`` is copied and modified from ``.env.template`` with values chosen by the maintainer.
* docker-compose interpolates variables in ``docker-compose.yml`` from ``.env``.
* docker-compose can pass on these variables to the containers as build time variables
  (when building the images) and / or as run time variables (when running the containers).
* ``ckan-entrypoint.sh`` has access to all run time variables of the ``ckan`` service.
* ``ckan-entrypoint.sh`` injects some variables (e.g. ``CKAN_SQLALCHEMY_URL``) into the running
  ``ckan`` container, supplementing the CKAN config variables from ``ckan.ini``.

After adding new, or changing the value of existing ``.env`` variables, locally built images and
volumes need to be dropped and rebuilt.
Otherwise, docker will re-use cached images with old or without variables::

    docker-compose down
    docker rmi $(docker images -f dangling=true -q)
    docker volume rm $(docker volume ls -f dangling=true -q)
    docker-compose build
    docker-compose up -d

.. warning:: Removing named volumes will destroy data.
    Backup all data when doing this in a production setting.

