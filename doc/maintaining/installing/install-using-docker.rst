====================================
Installing CKAN using a Docker image
====================================

.. note::
   Installing CKAN using a Docker image is currently under evaluation. There may
   be omissions or inaccuracies in this documentation. Proceed with caution.

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

You will also need to have separately configured both the |postgres| database
and the |solr| search index. Details of this installation will differ between
operating systems. On Ubuntu, you can run::

    sudo apt-get install -y postgresql solr-jetty

after which you should follow the instructions in :ref:`postgres-setup` and
:ref:`setting up solr` to configure these services.


---------------
Installing CKAN
---------------

In the simplest case, installing CKAN should be a matter of running a single
command. For example, to install the latest available version of the CKAN image
as published to the `Docker hub`_, and assuming you installed |postgres| and
|solr| as described in :ref:`postgres-setup` and :ref:`setting up solr`, you can
run::

    $ docker run -d -p 5000:80 \
        -e DATABASE_URL=postgresql://ckan_default:<password>@<localip>/ckan_default \
        -e SOLR_URL=http://<localip>:8983/solr/ckan_default \
        ckan/ckan

.. _Docker hub: https://hub.docker.com/

where you must replace ``<password>`` with the password you chose for your
database user and ``<localip>`` with the local IP address of your server. This
will start a new CKAN container in the background, listening on port 5000.

.. note::
   The first time you run this ``docker run`` command, Docker will have to
   download the ``ckan/ckan`` image: this may be quite slow, as the image
   contains all of CKAN's dependencies pre-built. Once you've downloaded the
   image, however, subsequent calls to ``docker run`` will be much faster. If
   you want, you can ``docker pull ckan/ckan`` to pre-fetch the image.

If all goes well you should now have a CKAN instance running. You can use
``docker ps`` to verify that your container started. You should see something
like the following::

    $ docker ps
    CONTAINER ID        IMAGE                         COMMAND               CREATED             STATUS              PORTS                     NAMES
    cab6e63c77b1        ckan/ckan:latest              /sbin/my_init         30 days ago         Up 1 minutes        0.0.0.0:5000->80/tcp      jovial_perlman

Using the container id (here it's ``cab6e63c77b1``), you can perform other
actions on your container, such as viewing the logs::

    $ docker logs cab6e63c77b1

listing the port bindings for the container::

    $ docker ports cab6e63c77b1

or stopping the container::

    $ docker stop cab6e63c77b1

If you wish to run CKAN on a different port or bind it to a specific IP address
on the machine, please consult the output of ``docker help run`` to see valid
values for the ``-p/--publish`` option.


----------------------------
Running maintenance commands
----------------------------

.. note::
   This is currently more fiddly than we would like, and we will hopefully soon
   add a helper command to make this easier.

You can run maintenance commands in their own ephemeral container (configured
with the same ``DATABASE_URL`` and ``SOLR_URL``) by specifying a custom command
for the container. For example, to create a sysadmin user called ``joebloggs``::

    $ docker run -i -t -e DATABASE_URL=... -e SOLR_URL=... \
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
