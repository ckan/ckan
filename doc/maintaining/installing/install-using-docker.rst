====================================
Installing CKAN using a Docker image
====================================

.. important::
   These instructions require Docker >=1.0. The released version of Docker is
   1.0.1 as at this writing.

.. note::
   Installing CKAN using a Docker image is currently under evaluation. There may
   be omissions or inaccuracies in this documentation. In particular, the
   current Docker image omits the configuration required to run the
   DataStore/DataPusher. Proceed with caution.

This section describes how to install CKAN using a Docker_ image. Docker is a
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

    $ docker run -d --name db ckan/postgresql
    $ docker run -d --name solr ckan/solr
    $ docker run -d -p 80:80 --link db:db --link solr:solr ckan/ckan

This start a new CKAN container in the background, connected to default
installations of |postgres| and |solr| also running in containers.

.. warning::
   The default |postgres| container is INAPPROPRIATE FOR PRODUCTION USE. The
   default database username and password is "ckan:ckan" and if you do not
   change this the contents of your database may well be exposed to the public.

.. note::
   The first time you run these ``docker run`` commands, Docker will have to
   download the software images: this may be quite slow. Once you've downloaded
   the images, however, subsequent calls to ``docker run`` will be much faster.
   If you want, you can run ``echo postgresql solr ckan | xargs -n1 -IIMG docker
   pull ckan/IMG`` to pre-fetch the images.

If all goes well you should now have a CKAN instance running. You can use
``docker ps`` to verify that your container started. You should see something
like the following::

    $ docker ps
    CONTAINER ID        IMAGE                         COMMAND               CREATED             STATUS              PORTS                     NAMES
    cab6e63c77b1        ckan/ckan:latest              /sbin/my_init         30 days ago         Up 1 minutes        0.0.0.0:80->80/tcp        jovial_perlman
    fb47b3744d6d        ckan/postgresql:latest        /usr/local/bin/run    9 days ago          Up 1 minutes        5432/tcp                  db,jovial_perlman/db
    96e963812fc9        ckan/solr:latest              java -jar start.jar   15 days ago         Up 1 minutes        8983/tcp                  solr,jovial_perlman/solr

Using the CKAN container id (here it's ``cab6e63c77b1``), you can perform other
actions on your container, such as viewing the logs::

    $ docker logs cab6e63c77b1

or stopping the container::

    $ docker stop cab6e63c77b1

If you wish to run CKAN on a different port or bind it to a specific IP address
on the machine, please consult the output of ``docker help run`` to see valid
values for the ``-p/--publish`` option.

You can also configure the CKAN container to connect to remote |postgres| and
|solr| services, without using Docker links, by setting the ``DATABASE_URL`` and
``SOLR_URL`` environment variables::

    $ docker run -d -p 80:80 \
        -e DATABASE_URL=postgresql://ckanuser:password@192.168.0.5/ckan \
        -e SOLR_URL=http://192.168.0.6:8983/solr/ckan


----------------------------
Running maintenance commands
----------------------------

.. note::
   This is currently more fiddly than we would like, and we will hopefully soon
   add a helper command to make this easier.

You can run maintenance commands in their own ephemeral container by specifying
a custom command for the container. For example, to create a sysadmin user
called ``joebloggs``::

    $ docker run -i -t --link db:db --link solr:solr \
        ckan/ckan \
        /sbin/my_init -- \
        /bin/bash -c \
        '$CKAN_HOME/bin/paster --plugin=ckan sysadmin -c $CKAN_CONFIG/ckan.ini add joebloggs'

----------------------------
Customizing the Docker image
----------------------------

You may well find you want to customize your CKAN installation, either by
setting custom configuration options not exposed by the Docker image, or by
installing additional CKAN extensions. A full guide to extending Docker images
is out-of-scope of this installation documentation, but you can use the
functionality provided by ``docker build`` to extend the ``ckan/ckan`` image:
http://docs.docker.com/reference/builder/.

For example, if you wanted custom configuration and the CKAN Spatial extension,
you could build an image from a Dockerfile like the following::

    FROM ckan/ckan

    # Install git
    RUN DEBIAN_FRONTEND=noninteractive apt-get update
    RUN DEBIAN_FRONTEND=noninteractive apt-get install -q -y git

    # Install the CKAN Spatial extension
    RUN $CKAN_HOME/bin/pip install -e git+https://github.com/ckan/ckanext-spatial.git@stable#egg=ckanext-spatial

    # Add my custom configuration file
    ADD mycustomconfig.ini $CKAN_CONFIG/ckan.ini

You would then reference your built image instead of ``ckan/ckan`` when calling
the ``docker run`` commands listed above.
