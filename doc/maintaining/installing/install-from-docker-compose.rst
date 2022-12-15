.. include:: /_substitutions.rst

===================================
Installing CKAN with Docker Compose
===================================
This chapter is a tutorial on how to install CKAN with Docker Compose. The scenario shown here is 
one of many possible scenarios and environments in which CKAN can be used with Docker.

This chapter aims to provide a simple, yet fully customizable deployment - easier to configure than
a source install, more customizable than a package install.

The discussed setup can be useful as a development / staging environment; additional care has to be
taken to use this setup in production.


--------------
1. Environment
--------------
The hosts can be local environments or cloud VMs. This tutorial works perfectly on Ubuntu 20.04 LTS (Focal) 
and MacOS 11.5 (Big Sur). Other hosts should be fine also. It is assumed that the user has direct access 
(via terminal / ssh) to the systems and has root access.

a. Storage

Using a cloud based VM, external storage volumes are cheaper than VMs and easy to backup.
In our use case, we use a cloud based VM with 16 GB storage, have mounted a 100 GB btrfs-formatted
external storage volume, and symlinked ``/var/lib/docker`` to the external volume.
This allows us to store the bulky and/or precious cargo -- Docker images, Docker data volumes
containing the CKAN databases, filestore, and config -- on a cheaper service.
On the other hand, a snapshotting filesystem like btrfs is ideal for rolling backups.
The same cost consideration might apply to other cloud-based providers.

.. note:: This setup stores data in named volumes, mapped to folder locations which can be
  networked or local storage.
  An alternative would be to re-write ``docker-compose.yml`` to map local storage
  directly, bypassing named volumes. Both solutions will save data to a specified location.

  Further reading: `Docker Volumes <https://docs.docker.com/engine/tutorials/dockervolumes/>`_.

b. Docker

Docker is installed system-wide following the official `Docker CE installation guidelines
<https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/>`_.

To verify a successful Docker installation, run ``docker run hello-world``.
``docker version`` should output versions for client and server.

c. Docker Compose

Docker Compose is installed system-wide following the official `Docker Compose installation
guidelines <https://docs.docker.com/compose/install/>`_.
There are three scenario's to install Docker Compose. Pick the scenario applicable to you. 
My Ubuntu 20.04 host required Scenario two (Install the Compose plugin) as I had aready installed 
the Docker Engine and Docker CLI. For MacOS I had already installed the Docker Desktop

To verify a successful Docker Compose installation, run ``docker-compose version``.

d. CKAN Docker Official repository

Clone the CKAN Docker repo into a directory of your choice::

    cd /path/to/my/projects
    git clone https://github.com/ckan/ckan-docker

You can update the main Docker configuration file (Dockerfile) to use any of the CKAN base images
from the CKAN (ckan/ckan-base) DockerHub repository

----------------------
2. Build Docker images
----------------------
In this step we will build the Docker images and create Docker data volumes with user-defined,
sensitive settings (e.g. database passwords).

a. Sensitive settings and environment variables

Copy ``.env.template`` to ``.env`` and follow instructions
within to set passwords and other sensitive or user-defined variables.
The defaults will work fine in a development environment on Linux. For Windows and MacOS, the `CKAN_SITE_URL` must be updated.

.. note:: Related reading:

   * `Docker-compose .env file <https://docs.docker.com/compose/env-file/>`_
   * `Environment variables in Compose <https://docs.docker.com/compose/environment-variables/>`_
   * Newcomers to Docker should read the excellent write-up on
     `Docker variables <http://vsupalov.com/docker-env-vars/>`_ by Vladislav Supalov (GitHub @th4t)

b. Build the images and start the containers

Inside the ckan-docker directory::

    docker-compose up -d --build

For the remainder of this chapter, we assume that ``docker-compose`` commands are all run inside
``ckan-docker``, where ``docker-compose.yml`` and ``.env`` are located.

The ``depends_on:`` sections in the compose file expresses the dependency between services. The ckan service
depends on the db, solr and redis services being started before it will start. The nginx service has the same 
dependency on the ckan service itself. The nginx service will be the last one to start.

After this step, CKAN should be running at ``https://localhost:${NGINX_SSLPORT}`` and ``http://localhost:${NGINX_PORT}``.

There should be six containers running (``docker ps``):

* ``nginx``: NGINX reverse proxy
* ``ckan``: CKAN with standard extensions
* ``db``: CKAN's database, later also running CKAN's datastore database
* ``redis``: A pre-built Redis image.
* ``solr``: A pre-built SolR image set up for CKAN.
* ``datapusher``: A pre-built CKAN Datapusher image.

There should be four named Docker volumes (``docker volume ls | grep docker``). They will be
prefixed with the Docker Compose project name (default: ``ckan-docker`` or value of host environment
variable ``COMPOSE_PROJECT_NAME``.)

* ``ckan-docker_ckan_config``: location of the CKAN config file: ckan.ini
* ``ckan-docker_ckan_home``: home of ckan source and libraries
* ``ckan-docker_ckan_storage``: location of CKAN's filestore (resource files)
* ``ckan-docker_pg_data``: location of the database files for CKAN's default and datastore databases

The location of these named volumes needs to be backed up in a production environment.
To migrate CKAN data between different hosts, simply transfer the content of the named volumes.
A detailed use case of data transfer will be discussed in step 5.

The docker container names are all configured using environment variables rather than hard coding names
directly in the docker compose file

c. Convenience: paths to named volumes

The files inside named volumes reside on a long-ish path on the host.
Purely for convenience, we'll define environment variables for these paths.
We'll use a prefix ``VOL_`` to avoid overriding variables in ``docker-compose.yml``.::

    # Find the path to a named volume
    docker volume inspect ckan-docker_ckan_home | jq -c '.[] | .Mountpoint'
    # "/var/lib/docker/volumes/docker_ckan_config/_data"

    export VOL_CKAN_HOME=`docker volume inspect ckan-docker_ckan_home | jq -r -c '.[] | .Mountpoint'`
    echo $VOL_CKAN_HOME

    export VOL_CKAN_CONFIG=`docker volume inspect ckan-docker_ckan_config | jq -r -c '.[] | .Mountpoint'`
    echo $VOL_CKAN_CONFIG

    export VOL_CKAN_STORAGE=`docker volume inspect ckan-docker_ckan_storage | jq -r -c '.[] | .Mountpoint'`
    echo $VOL_CKAN_STORAGE

We won't need to access files inside ``docker_pg_data`` directly, so we'll skip creating the shortcut.
As shown further below, we can use ``psql`` from inside the ``ckan`` container to run commands
against the database and import / export files from ``$VOL_CKAN_HOME``.

---------------------------
3. Datastore and DataPusher
---------------------------
The datastore database and user are created when the `db` container is first started, however we need to do 
some additional configuration before enabling the datastore and datapusher settings in the ``ckan.ini``.

a. Configure datastore database

With running ``ckan`` container, execute the built-in setup script against the ``db`` container::

    docker exec ckan ckan -c /srv/app/ckan.ini datastore set-permissions | docker exec -i db psql -U ckan

The script pipes in the output of ``ckan datastore set-permissions`` - however,
as this output can change in future versions of CKAN, we set the permissions directly.
The effect of this script is persisted in the named volume ``ckan-docker_pg_data``.

.. note:: We re-use the already privileged default user of the CKAN database as read/write user
    for the datastore. The database user (``ckan``) is hard-coded, the password is supplied through
    the``.env`` variable ``POSTGRES_PASSWORD``.
    A new user ``datastore_ro`` is created (and also hard-coded) as readonly user with password
    ``DATASTORE_READONLY_USER``.
    Hard-coding the database table and usernames allows to prepare the set-permissions SQL script,
    while not exposing sensitive information to the world outside the Docker host environment.

After this step, the datastore database is ready to be enabled in the ``ckan.ini``.

b. Enable datastore and datapusher in ``ckan.ini``

Edit the ``ckan.ini`` (note: requires sudo)::

    sudo vim $VOL_CKAN_CONFIG/ckan.ini

Add ``datastore datapusher`` to ``ckan.plugins`` and enable the datapusher option
``ckan.datapusher.formats``.

The remaining settings required for datastore and datapusher are already taken care of:

* ``ckan.storage_path`` (``/var/lib/ckan``) is hard-coded in ``docker-compose.yml`` and 
* CKAN's base image ``Dockerfile``. This path is hard-coded as it remains internal
  to the containers, and changing it would have no effect on the host system.
* ``ckan.datastore.write_url = postgresql://ckan:POSTGRES_PASSWORD@db/datastore`` and
  ``ckan.datastore.read_url = postgresql://datastore:DATASTORE_READONLY_PASSWORD@db/datastore``
  are provided by the ``env_file:`` line in ``docker-compose.yml``.

Restart the ``ckan`` container to apply changes to the ``ckan.ini``::

    docker-compose restart ckan

Now the datastore API should return content when visiting::

    <CKAN_SITE_URL>/api/3/action/datastore_search?resource_id=_table_metadata

-------------------------
4. The CKAN admin user
-------------------------
A CKAN Admin user is pre-built in the CKAN base image. The credentials are located in the 
``CKAN_SYSADMIN_NAME`` and ``CKAN_SYSADMIN_PASSWORD`` environment variables from the ``.env`` file.
The admin user's API key will be instrumental in tranferring data from other instances.

---------------
5. Migrate data
---------------
This section illustrates the data migration from an existing CKAN instance ``SOURCE_CKAN``
into our new Docker Compose CKAN instance assuming direct (ssh) access to ``SOURCE_CKAN``.

a. Transfer resource files

Assuming the CKAN storage directory on ``SOURCE_CKAN`` is located at ``/path/to/files`` (containing
resource files and uploaded images in ``resources`` and ``storage``), we'll simply ``rsync``
``SOURCE_CKAN``'s storage directory into the named volume ``docker_ckan_storage``::

    sudo rsync -Pavvr USER@SOURCE_CKAN:/path/to/files/ $VOL_CKAN_STORAGE

b. Transfer users

Users could be exported using the python package ``ckanapi``, but their password hashes will be
excluded. To transfer users preserving their passwords, we need to dump and restore the ``user``
table.

On source CKAN host with access to source db ``ckan_default``, export the ``user`` table::

    pg_dump -h CKAN_DBHOST -P CKAN_DBPORT -U CKAN_DBUSER -a -O -t user -f user.sql ckan_default

On the target host, make ``user.sql`` accessible to the source CKAN container.
Transfer user.sql into the named volume ``docker_ckan_home`` and ``chown`` it to the docker user::

    rsync -Pavvr user@ckan-source-host:/path/to/user.sql $VOL_CKAN_HOME/venv/src

    # $VOL_CKAN_HOME is owned by the user "ckan" (UID 900) as created in the CKAN Dockerfile
    sudo ls -l $VOL_CKAN_HOME
    # drwxr-xr-x 1 900 900 62 Jul 17 16:13 venv

    # Chown user.sql to the owner of $CKAN_HOME (ckan, UID 900)
    sudo chown 900:900 $VOL_CKAN_HOME/venv/src/user.sql

Now the file ``user.sql`` is accessible from within the ``ckan`` container::

    docker exec -it ckan /bin/bash -c "export TERM=xterm; exec bash"

    ckan@eca111c06788:/$ psql -U ckan -h db -f $CKAN_VENV/src/user.sql

c. Export and upload groups, orgs, datasets

Using the python package ``ckanapi`` we will dump orgs, groups and datasets from the source CKAN
instance, then use ``ckanapi`` to load the exported data into the target instance.
The datapusher will automatically ingest CSV resources into the datastore.

d. Rebuild search index

Trigger a Solr index rebuild::

    docker exec -it ckan ckan -c /srv/app/ckan.ini search-index rebuild

-----------------
6. Add extensions
-----------------
There are two scenarios to add extensions:

* Maintainers of production instances need extensions to be part of the ``ckan`` image and an
  easy way to enable them in the ``ckan.ini``.
  Automating the installation of existing extensions (without needing to change their source)
  requires customizing CKAN's ``Dockerfile`` and scripted post-processing of the ``ckan.ini``.
* Developers need to read, modify and use version control on the extensions' source. This adds
  additional steps to the maintainers' workflow.

For maintainers, the process is in summary:

* Run a bash shell inside the running ``ckan`` container, download and install extension.
  Alternatively, add a ``pip install`` step for the extension into a custom CKAN Dockerfile.
* Restart ``ckan`` service, read logs.

a. Download and install extension from inside ``ckan`` container into ``ckan-docker_ckan_home`` volume

The process is very similar to installing extensions in a source install. The only difference is
that the installation steps will happen inside the running container.

The downloaded and installed files will be persisted in the named volume ``ckan-docker_ckan_home``.

In this example we will enter the running ``ckan`` container to install
`ckanext-geoview <https://github.com/ckan/ckanext-geoview>`_ from source,
`ckanext-showcase <https://github.com/ckan/ckanext-showcase>`_ from GitHub,
and `ckanext-envvars <https://github.com/okfn/ckanext-envvars>`_ from PyPi::

    # Enter the running ckan container:
    docker exec -it ckan /bin/bash -c "export TERM=xterm; exec bash"

    # Option 1: From source
    git clone https://github.com/ckan/ckanext-geoview.git
    cd ckanext-geoview
    pip install -r pip-requirements.txt
    python setup.py install
    python setup.py develop
    cd ..

    # Option 2: Pip install from GitHub
    pip install -e "git+https://github.com/ckan/ckanext-showcase.git#egg=ckanext-showcase"

    # Option 3: Pip install from PyPi
    pip install ckanext-envvars

    # exit the ckan container:
    exit

b. Modify CKAN config

Follow the respective extension's instructions to set CKAN config variables::

    sudo vim $VOL_CKAN_CONFIG/ckan.ini

.. todo:: Demonstrate how to set ``ckan.ini`` settings from environment variables using
   ``ckanext-envvars``.

c. Reload and debug

::

    docker-compose restart ckan
    docker-compose logs ckan

d. Develop extensions: modify source, install, use version control

While maintainers will prefer to use stable versions of existing extensions, developers of
extensions will need access to the extensions' source, and be able to use version control.

The use of Docker and the inherent encapsulation of files and permissions makes the development of
extensions harder than a CKAN source install.

Firstly, the absence of private SSH keys inside Docker containers will make interacting with
GitHub a lot harder. On the other hand, two-factor authentication on GitHub breaks BasicAuth
(HTTPS, username and password) and requires a "personal access token" in place of the password.

To use version control from inside the Docker container:

* Clone the HTTPS version of the GitHub repo.
* On GitHub, create a personal access token with "full control of private repositories".
* Copy the token code and use as password when running ``git push``.

Secondly, the persisted extension source at ``VOL_CKAN_HOME`` is owned by the CKAN container's
``docker`` user (UID 900) and therefore not writeable to the developer's host user account by
default. There are various workarounds. The extension source can be accessed from both outside and
inside the container.

Option 1: Accessing the source from inside the container::

    docker exec -it ckan /bin/bash -c "export TERM=xterm; exec bash"
    source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/
    # ... work on extensions, use version control ...
    # in extension folder:
    python setup.py install
    exit
    # ... edit extension settings in ckan.ini and restart ckan container
    sudo vim $VOL_CKAN_CONFIG/ckan.ini
    docker-compose restart ckan

Option 2: Accessing the source from outside the container using ``sudo``::

    sudo vim $VOL_CKAN_CONFIG/ckan.ini
    sudo vim $VOL_CKAN_HOME/venv/src/ckanext-datawagovautheme/ckanext/datawagovautheme/templates/package/search.html

Option 3: The Ubuntu package ``bindfs`` makes the write-protected volumes accessible to a system
user::

    sudo apt-get install bindfs
    mkdir ~/VOL_CKAN_HOME
    sudo chown -R `whoami`:docker $VOL_CKAN_HOME
    sudo bindfs --map=900/`whoami` $VOL_CKAN_HOME ~/VOL_CKAN_HOME

    cd ~/VOL_CKAN_HOME/venv/src

    # Do this with your own extension fork
    # Assumption: the host user running git clone (you) has write access to the repository
    git clone https://github.com/parksandwildlife/ckanext-datawagovautheme.git

    # ... change files, use version control...

Changes in HTML templates and CSS will be visible right away.
For changes in code, we'll need to unmount the directory, change ownership back to the ``ckan``
user, and follow the previous steps to ``python setup.py install`` and
``pip install -r requirements.txt`` from within the running container, modify the ``ckan.ini``
and restart the container::

    sudo umount ~/VOL_CKAN_HOME
    sudo chown -R 900:900 $VOL_CKAN_HOME
    # Follow steps a-c

.. note:: Mounting host folders as volumes instead of using named volumes may result in a simpler
   development workflow. However, named volumes are Docker's canonical way to persist data.
   The steps shown above are only some of several possible approaches.

------------------------
1. Environment variables
------------------------

This section is targeted at CKAN maintainers seeking a deeper understanding of variables,
and at CKAN developers seeking to factor out settings as new ``.env`` variables.

Variable substitution propagates as follows:

* ``.env.template`` holds the defaults and the usage instructions for variables.
* The maintainer copies ``.env`` from ``.env.template`` and modifies it following the instructions.
* Docker Compose interpolates variables in ``docker-compose.yml`` from ``.env``.
* Docker Compose can pass on these variables to the containers as build time variables
  (when building the images) and / or as run time variables (when running the containers).
* ``ckan-entrypoint.sh`` has access to all run time variables of the ``ckan`` service.
* ``ckan-entrypoint.sh`` injects environment variables (e.g. ``CKAN_SQLALCHEMY_URL``) into the
  running ``ckan`` container, overriding the CKAN config variables from ``ckan.ini``.

See :doc:`/maintaining/configuration` for a list of environment variables
(e.g. ``CKAN_SQLALCHEMY_URL``) which CKAN will accept to override ``ckan.ini``.

After adding new or changing existing ``.env`` variables, locally built images and volumes may
need to be dropped and rebuilt. Otherwise, docker will re-use cached images with old or missing
variables::

    docker-compose down
    docker-compose up -d --build

    # if that didn't work, try:
    docker rmi $(docker images -q -f dangling=true)
    docker-compose up -d --build

    # if that didn't work, try:
    docker rmi $(docker images -q -f dangling=true)
    docker volume prune
    docker-compose up -d --build

.. warning:: Removing named volumes will destroy data.
    ``docker volume prune`` will delete any volumes not attached to a running(!) container.
    Backup all data before doing this in a production setting.

