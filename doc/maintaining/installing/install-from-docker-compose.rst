.. include:: /_substitutions.rst

===================================
Installing CKAN with docker-compose
===================================

This chapter describes how to install CKAN with docker-compose. The scenario shown here is one of
many possibile scenarios and environments in which CKAN can be used with Docker.

This chapter aims to provide a simple, yet fully customizable deployment - easier to configure than
a source install, more customizable than a package install.

.. note:: Some design decisions are opinionated, and there are alternatives.

--------------
1. Environment
--------------
We will use a Ubuntu environment, so far this has been tested on:

* Amazon AWS EC2 Ubuntu 14.04 LTS
* Ubuntu 16.04 LTS on a desktop

a. Storage

Using a cloud based VM, external storage volumes are cheaper than VMs and easy to backup.
In our use case, we use an AWS EC2 with 16 GB storage, have mounted a 100 GB btrfs-formatted
external storage volume, and symlinked ``/var/lib/docker`` to the external volume.
This allows us to store the bulky and precious cargo -- Docker images, Docker data volumes
containing the CKAN databases, filestore, and config -- on a cheaper service.
On the other hand, a snapshotting filesystem like btrfs is ideal for rolling backups.
The same cost consideration might apply to other cloud-based providers.

.. note:: This setup stores data in named volumes, mapped to folder locations which can be
  network or local storage.
  An alternative would be to re-write ``docker-compose.yml`` to map local storage
  directly, bypassing named volumes. Both solutions will save data to a specified location.

b. Docker

Docker is installed system-wide following the official `Docker CE installation guidelines
<https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/>`_.

To verify a successful Docker installation, run ``docker run hello-world``.
``docker version`` should output versions for client and server.

c. Docker Compose

Docker Compose is installed system-wide following the official `Docker Compose installation
guidelines <https://docs.docker.com/compose/install/>`_.

To verify a successful Docker Compose installation, run ``docker-compose version``.

d. CKAN source

Clone CKAN into a directory of your choice::

    cd /path/to/my/projects
    git clone git@github.com:ckan/ckan.git .

----------------------
2. Build Docker images
----------------------
In this step we will build the Docker images and create Docker data volumes with user-defined,
sensitive settings (e.g. for database passwords).

a. Sensitive settings and environment variables

In a production environment, copy ``contrib/docker/.env.template`` to ``contrib/docker/.env``
and follow instructions within to set passwords and other sensitive or user-defined variables.
The defaults will work fine in a development environment.

b. Build the images

Inside the CKAN directory::

    cd contrib/docker
    docker-compose up -d --build

For the remainder of this chapter, we assume that docker-compose commands are all run inside
``contrib/docker``.

On first runs, the postgres container could need longer to initialize the database cluster than
the ckan container will wait for. This time span depends heavily on available system resources.
If the CKAN logs show problems connecting to the database, restart the ckan container a few times::

    docker-compose restart ckan
    docker ps | grep ckan
    docker-compose logs -f ckan

.. note:: Earlier versions of ``ckan-entrypoint.sh`` used to wait and ping the db container
  using detailed db credentials (host, port, user, password).
  While this delay sometimes worked, it also obfuscated other possible problems.
  However, the db cluster needs to initialize only once, and starts up quickly in subsequent
  runs. This setup chose the very opinionated option of doing away with the delay altogether in
  favour of failing early.

After this step, CKAN should be running at ``CKAN_SITE_URL``.

There should be five containers running (``docker ps``):

* ``ckan``: CKAN with standard extensions
* ``db``: CKAN's database, later also running CKAN's datastore database
* ``redis``: A pre-built Redis image.
* ``solr``: A pre-built SolR image set up for CKAN.
* ``datapusher``: A pre-built CKAN Datapusher image.

There should be four named Docker volumes (``docker volume ls | grep docker``). They will be
prefixed with the Docker project name (default: ``docker``)

* ``docker_ckan_config``: home of ckan.ini
* ``docker_ckan_home``: home of ckan venv and source, later also additional CKAN extensions
* ``docker_ckan_storage``: home of CKAN's filestore (resource files)
* ``docker_pg_data``: home of the database files for CKAN's default and datastore databases

The location of these named volumes needs to be backed up in a production environment.
To migrate CKAN data between different hosts, simply transfer the content of the named volumes.
A detailed use case of data transfer will be discussed in step 5.

---------------------------
3. Datastore and datapusher
---------------------------
To enable the datastore, the datastore database and database users have to be created before
enabling the datastore and datapusher settings in the ``ckan.ini``.

a. Create and configure datastore database

With running CKAN containers, execute the built-in setup scripts against the ``db`` container::

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

Add ``datastore datapusher`` to ``ckan.plugins`` and enable the datapusher option
``ckan.datapusher.formats``.

The remaining settings required for datastore and datapusher are already taken care of:

* ``ckan.storage_path`` (``/var/lib/ckan``) is hard-coded in ``ckan-entrypoint.sh``,
  ``docker-compose.yml`` and CKAN's ``Dockerfile``. This path is hard-coded as it remains internal
  to the containers, and changing it would have no effect on the host system.
* ``ckan.datastore.write_url = postgresql://ckan:POSTGRES_PASSWORD@db/datastore`` and
  ``ckan.datastore.read_url = postgresql://datastore:DATASTORE_READONLY_PASSWORD@db/datastore``
  are provided by ``docker-compose.yml``.


Restart the ``ckan`` container to apply changes to the ``ckan.ini``::

    docker-compose restart ckan

Now the datastore API should return content when visiting::

    CKAN_SITE_URL/api/3/action/datastore_search?resource_id=_table_metadata

-------------------------
4. Create CKAN admin user
-------------------------
With all four Docker images up and running, create the CKAN admin user (johndoe in this example)::

    docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckan sysadmin -c /etc/ckan/ckan.ini add johndoe

Now you should be able to login to the new, empty CKAN.
The admin user's API key will be instrumental in tranferring data from other instances.

---------------
5. Migrate data
---------------
.. todo:: This section requires testing.

Pending testing, and presuming same dataset schema (ckanext-scheming) on
source and target CKANs, the process should be as simple as:

* ``rsync`` contents of the filestore into the storage volume.
* Use python package ``ckanapi`` to dump orgs, groups and datasets from source CKAN instance,
  transfer files, then use ``ckanapi`` to load the exported data into the target instance.
* Let datapusher populate datastore.
* Trigger a Solr index rebuild.

-----------------
6. Add extensions
-----------------
There are two use cases how to add extensions:

* Developers will want to have access to the extensions' source.
* Maintainers of production instances will want extensions to be part of the ``ckan`` image and an
  easy way to enable them in the ``ckan.ini``. This requires customizing CKAN's ``Dockerfile`` and
  scripted post-processing of the ``ckan.ini``.

For developers, the process is:

* Run a bash shell inside the running ``ckan`` image, download and install extension.
* Edit ``ckan.ini``
* Restart ``ckan`` service, read logs.

a. Download and install extension inside ``ckan`` image

The process is very similar to installing extensions in a source install. The only difference is
that the installation steps happen inside the running container, using the virtualenv created
inside the ckan image by CKAN's Dockerfile, which is different from the virtualenv we have created
on the host machine in step 2.

The downloaded and installed files will be persisted in the named volume ``docker_ckan_home``.

In this example we'll install `ckanext-geoview <https://github.com/ckan/ckanext-geoview>`_::

    # Enter the running ckan container:
    docker exec -it ckan bash

    # Inside the running container, activate the virtualenv
    source $CKAN_VENV/bin/activate

    # Download source
    cd $CKAN_VENV/src/
    git clone https://github.com/ckan/ckanext-geoview.git
    cd ckanext-geoview

    # Install extension's requirements
    pip install -r pip-requirements.txt

    # Install extension
    python setup.py install
    python setup.py develop

    # exit the ckan container:
    exit

Some extensions require database upgrades, often through paster scripts.
E.g., ``ckanext-spatial``::


    # Enter the running ckan container:
    docker exec -it ckan bash

    # Inside the running ckan container
    source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/
    git clone https://github.com/ckan/ckanext-spatial.git
    cd ckanext-spatial
    pip install -r pip-requirements.txt
    python setup.py install && python setup.py develop
    exit

    docker exec -it db psql -U ckan -f 20_postgis_permissions.sql
    docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial spatial initdb -c /etc/ckan/ckan.ini

    sudo vim /var/lib/docker/volumes/docker_ckan_config/_data/ckan.ini

    # in plugins, add:
    spatial_metadata spatial_query

    ckanext.spatial.search_backend = solr

.. note:: In order to work on your own forks of CKAN extensions, the container's
  ssh publickey must be added to the respective repository's authorized keys.

b. Modify CKAN config

Follow the respective extension's instructions to set CKAN config variables::

    sudo vim /var/lib/docker/volumes/docker_ckan_config/_data/ckan.ini

c. Reload and debug

::

    docker-compose restart ckan
    docker-compose logs ckan

.. todo:: A more automated way to install extensions would be to factor out user-defined settings
  into environment variables, and automate installation steps as scripts.
  Pull requests with working scripts for each extension are welcome!

------------------------
7. Environment variables
------------------------
Sensitive settings can be managed in (at least) two ways, either as environment variables, or as
`Docker secrets <https://docs.docker.com/engine/swarm/secrets/>`_.
This section illustrates the use of evironment variables.

This section is targeted at CKAN maintainers seeking a deeper understanding of variables,
and at CKAN developers seeking to factor out settings as new ``.env`` variables.

The flow of variable substitution is as follows:

* ``.env.template`` holds the defaults and the usage instructions for variables.
* ``.env`` is copied and modified from ``.env.template`` with values chosen by the maintainer.
* docker-compose interpolates variables in ``docker-compose.yml`` from ``.env``.
* docker-compose can pass on these variables to the containers as build time variables
  (when building the images) and / or as run time variables (when running the containers).
* ``ckan-entrypoint.sh`` has access to all run time variables of the ``ckan`` service.
* ``ckan-entrypoint.sh`` injects environment variables (e.g. ``CKAN_SQLALCHEMY_URL``) into the
  running ``ckan`` container, overriding the CKAN config variables from ``ckan.ini``.

See :doc:`/maintaining/configuration` for a list of environment variables
(e.g. ``CKAN_SQLALCHEMY_URL``) which CKAN will accept to override ``ckan.ini``.

After adding new or changing existing ``.env`` variables, locally built images and volumes may
need to be dropped and rebuilt. Otherwise, docker will re-use cached images with old or without
variables::

    docker-compose down
    docker-compose up -d --build

    # if that didn't work, try:
    docker rmi $(docker images -f dangling=true -q)
    docker-compose up -d --build

    # if that didn't work, try:
    docker rmi $(docker images -f dangling=true -q)
    docker volume rm $(docker volume ls -f dangling=true -q)
    docker-compose up -d --build

.. warning:: Removing named volumes will destroy data.
    Backup all data when doing this in a production setting.

