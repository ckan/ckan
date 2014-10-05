====================================
Installing CKAN using a Docker image
====================================

.. important::
   These instructions require Docker >=1.0. 
   The released version of Docker is 1.2 as at this writing, this is compatible with `boot2docker`_
   
.. important:: 
   The CKAN container supports and enables the datastore & datapusher by default
   The Postgres container supports and configures PostGIS on the ckan database 
   but the spatial extention is not enabled by default

.. note::
   Installing CKAN using a Docker image is currently under evaluation. There may
   be omissions or inaccuracies in this documentation.

This section describes how to install CKAN & extensions using a Docker_ image. Docker is a
tool that allows all kinds of software to be shipped and deployed in a standard
format, much as cargo is shipped around the world in `standardised shipping
containers`_.

CKAN is built into a binary image, which you can then use as a blueprint to
launch multiple containers which run CKAN and attendant services in an isolated
environment. Providing a full introduction to Docker concepts is out of the
scope of this document: you can learn more in the `Docker documentation`_.

.. _Docker: http://www.docker.com/
.. _Docker documentation: http://docs.docker.com/
.. _standardised shipping containers: https://en.wikipedia.org/wiki/Intermodal_container
.. _boot2docker: https://github.com/boot2docker/boot2docker


-------------
Prerequisites
-------------

In order to install CKAN using Docker, you will need to have installed Docker.
Please follow the instructions for installing Docker from `the Docker
documentation <https://docs.docker.com/installation/>`_.

---------------
Installing CKAN
---------------

In the simplest case, installing CKAN should be a matter of running three
commands: to run |postgres|, |solr|, and CKAN::

    $ docker docker run 
         -d 
         --name postgres 
         -h postgres.docker.local 
         ckan/postgresql
    $ docker run 
         -d 
         --name solr 
         -h solr.docker.local 
         ckan/solr
    $ docker run \
         -d \
         --name ckan \
         -h ckan.docker.local \
         -p 80:80 \
         -p 8800:8800 \
         --link postgres:postgres \
         --link solr:solr \
         ckan/ckan

This start a new CKAN container in the background, connected to default
installations of |postgres| and |solr| also running in containers.

.. warning::
   The default run command avove to start the |postgres| container is INAPPROPRIATE FOR PRODUCTION USE. The
   default database username and password is "ckan_user:ckan_pass" and if you do not
   change this the contents of your database may well be exposed to the public.
   You can provide secure credentials when the container is created by overriding the environment variables
   
You can provide secure credentials when the container is created by overriding the environment variables
The same approach can be taken to use a different database & user name::
   
     ENV CKAN_DB ckan
     ENV CKAN_USER ckan_user
     ENV CKAN_PASS ckan_pass
     ENV DATASTORE_DB datastore
     ENV DATASTORE_USER datastore_user
     ENV DATASTORE_PASS datastore_pass
   
Example with custom passwords for the database & datastore::

    $ docker run \
         -d \
         --name postgres \
         -h postgres.docker.local \
         -e CKAN_PASS=mypassword \
         -e DATASTORE_PASS=mypassword \
         ckan/postgresql

.. note::
   The first time you run these ``docker run`` commands, Docker will have to
   download the software images: this may be quite slow. Once you've downloaded
   the images, however, subsequent calls to ``docker run`` will be much faster.
   If you want, you can run ``echo postgresql solr ckan | xargs -n1 -IIMG docker
   pull ckan/IMG`` to pre-fetch the images.

If all goes well you should now have a CKAN instance running. You can use
``docker ps -a`` to verify that your container started. You should see something
like the following::

    $ docker ps -a
    CONTAINER ID        IMAGE                   COMMAND                CREATED             STATUS              PORTS                                        NAMES
    0e6acf77679a        ckan/ckan:latest        "/sbin/my_init"        34 minutes ago      Up 2 seconds        0.0.0.0:80->80/tcp, 0.0.0.0:8800->8800/tcp   ckan                     
    bc0be2622c0d        ckan/postgres:latest    "/sbin/my_init"        35 minutes ago      Up About a minute   5432/tcp                                     ckan/postgres,postgres   
    a592d07ffffc        ckan/solr:latest        "/sbin/my_init"        36 minutes ago      Up 2 minutes        8983/tcp                                     ckan/solr,solr

Using the CKAN container name or id (here it's ``0e6acf77679a``), you can perform other
actions on your container, such as viewing the logs::

    $ docker logs ckan

or stopping the container::

    $ docker stop ckan

If you wish to run CKAN on a different port or bind it to a specific IP address
on the machine, please consult the output of ``docker help run`` to see valid
values for the ``-p/--publish`` option.

You can also configure the CKAN container to connect to remote |postgres| and
|solr| services, without using Docker links, by setting the ``DATABASE_URL``, 
``DATASTORE_WRITE_URL``, ``DATASTORE_READ_URL`` and
``SOLR_URL`` environment variables::

    $ docker run 
         -d 
         --name ckan \
         -h ckan.docker.local \
         -p 80:80 \
         -p 8800:8800 \
         -e DATABASE_URL=postgresql://ckan_user:ckan_pass@postgres_ip_address/ckan \
         -e DATASTORE_WRITE_URL=postgresql://ckan_user:ckan_pass@postgres_ip_address/datastore \
         -e DATASTORE_READ_URL=postgresql://datastore_user:datastore_pass@postgres_ip_address/datastore \
         -e SOLR_URL=http://solr_ip_address:8983/solr/ckan


----------------------------
Running maintenance commands
----------------------------

.. note::
   This is currently more fiddly than we would like, and we will hopefully soon
   add a helper command to make this easier.

You can run maintenance commands in their own ephemeral container by specifying
a custom command for the container::

    $ docker run \
         -i -t \
         --name ckan \
         -h ckan.docker.local \
         -p 80:80 \
         -p 8800:8800 \
         --link postgres:postgres \
         --link solr:solr \
         --link redis:redis \
         ckan/ckan \
         /sbin/my_init -- \
         /bin/bash
         
For example, to create a sysadmin user::

    $ $CKAN_HOME/bin/paster --plugin=ckan sysadmin -c $CKAN_CONFIG/ckan.ini add admin

----------------------------
Customizing the Docker image
----------------------------

You may well find you want to customize your CKAN installation, either by
setting custom configuration options not exposed by the Docker image, or by
installing additional CKAN extensions. A full guide to extending Docker images
is out-of-scope of this installation documentation, but you can use the
functionality provided by ``docker build`` to extend the ``ckan/ckan`` image:
http://docs.docker.com/reference/builder/.

There is an example custom configuration enabling the CKAN Archiver, Harvest & Spatial extensions
in the ``contrib/docker/custom`` folder
You can customise & build this image::

    $ docker build --tag="your_username/ckan_custom" .

You would then reference your built image instead of ``ckan/ckan`` when calling
the ``docker run`` commands listed above.
