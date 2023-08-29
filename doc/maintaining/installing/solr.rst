:orphan:

CKAN uses Solr_ as its search engine, and uses a customized Solr schema file
that takes into account CKAN's specific search needs. Now that we have CKAN
installed, we need to install and configure Solr.


.. warning:: CKAN supports **Solr 9** (recommended version) and Solr 8. Starting from CKAN 2.10 these are the only Solr version supported. CKAN 2.9 can run with Solr 9 and 8 as long as it is patched to at least 2.9.5.


There are two supported ways to install Solr.

1. Using CKAN's official Docker_ images. This is generally the easiest one and the recommended one if you are developing CKAN locally
2. Installing Solr locally and configuring it with the CKAN schema. You can use this option if you can't or don't want to use Docker.


Installing Solr using Docker
============================

You will need to have Docker installed. Please refer to its `installation documentation <https://docs.docker.com/engine/install/>`_ for details.

There are pre-configured Docker images for Solr for each CKAN version. Make sure to pick the image tag that matches your CKAN version (they are named ``ckan/ckan-solr:<Major version>.<Minor version>``). To start a local Solr service you can run:

   .. parsed-literal::

    docker run --name ckan-solr -p 8983:8983 -d ckan/ckan-solr:2.10-solr9

You can now jump to the `Next steps <#next-steps-with-solr>`_ section.

Installing Solr manually
========================

The following instructions have been tested in Ubuntu 22.04 and are provided as a guidance only. For a Solr production setup is it recommended that you
follow the `official Solr documentation <https://solr.apache.org/guide/solr/latest/deployment-guide/taking-solr-to-production.html>`_.


#. Install the OS dependencies::

      sudo apt-get install openjdk-11-jdk

#. Download the latest supported version from the `Solr downloads page <https://solr.apache.org/downloads.html>`_. CKAN supports Solr version 9.x (recommended) and 8.x.

#. Extract the install script file to your desired location (adjust the Solr version number to the one you are using)::

    tar xzf solr-9.2.1.tgz solr-9.2.1/bin/install_solr_service.sh --strip-components=2

#. Run the installation script as ``root``::

    sudo bash ./install_solr_service.sh solr-9.2.1.tgz

#. Check that Solr started running::

    sudo service solr status

#. Create a new core for CKAN::

    sudo -u solr /opt/solr/bin/solr create -c ckan

#. Replace the standard schema with the CKAN one:

   .. parsed-literal::

    sudo -u solr wget -O /var/solr/data/ckan/conf/managed-schema https://raw.githubusercontent.com/ckan/ckan/dev-v2.10/ckan/config/solr/schema.xml


#. Restart Solr::

    sudo service solr restart


Next steps with Solr
====================

To check that Solr started you can visit the web interface at http://localhost:8983/solr

.. warning:: The two installation methods above will leave you with a setup that is fine for local development, but Solr should never be exposed publicly in a production site. Pleaser refer to the `Solr documentation <https://solr.apache.org/guide/securing-solr.html>`_ to learn how to secure your Solr instance.


If you followed any of the instructions above, the CKAN Solr core will be available at http://localhost:8983/solr/ckan. If for whatever reason you ended up with a different one (eg with a different port, host or core name), you need to change the :ref:`solr_url` setting in your :ref:`config_file` (|ckan.ini|) to point to your Solr server, for example::

       solr_url=http://my-solr-host:8080/solr/ckan-2.10


.. _Solr: https://solr.apache.org/
.. _Docker: https://www.docker.com/
