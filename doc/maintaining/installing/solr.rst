:orphan:

CKAN uses Solr_ as its search platform, and uses a customized Solr schema file
that takes into account CKAN's specific search needs. Now that we have CKAN
installed, we need to install and configure Solr.

.. _Solr: http://lucene.apache.org/solr/


.. warning:: CKAN supports **Solr 8**. Starting from CKAN 2.10 this is the only Solr version supported. CKAN 2.9 can run with Solr 8 as long as it is patched to at least 2.9.5. CKAN 2.9 can also run against Solr 6 but this is not recommended as this Solr version does no longer receive security updates.


There are two supported ways to install Solr.

1. Using CKAN's official Docker images. This is generally the easiest one and the recommended one if you are developing CKAN locally.
2. Installing Solr locally and configuring it with the CKAN schema. You can use this option if you can't or don't want to use Docker.


Installing Solr using Docker
============================

You will need to have Docker installed. Please refer to its `installation documentation <https://docs.docker.com/engine/install/>`_ for details.

There are pre-configured Docker images for Solr for each CKAN version. Make sure to pick the image tag that matches your CKAN version (they are named ``ckan/ckan-solr:<Major version>.<Minor version>``). To start a local Solr service you can run:

   .. parsed-literal::

    docker run --name ckan-solr -p 8983:8983 -d ckan/ckan-solr:2.9

You can now jump to the `Next steps <#next-steps-with-solr>`_ section.

Installing Solr manually
========================

.. note::

   These instructions explain how to deploy Solr using the Tomcat web
   server, but CKAN doesn't require Tomcat - you can deploy Solr to another web
   server, such as Jetty, if that's convenient on your operating system.

#. Change the default port Tomcat runs on (8080) to the one expected by CKAN. To do so change the following line in the ``/etc/tomcat9/server.xml`` file (``tomcat8`` in older Ubuntu versions)::

        From:

        <Connector port="8080" protocol="HTTP/1.1"


        To:

        <Connector port="8983" protocol="HTTP/1.1"


   .. note:: This is not required by CKAN, you can keep the default Tomcat port or use a different one, just make sure to update the :ref:`solr_url` setting in your :ref:`config_file` accordingly.

#. Replace the default ``schema.xml`` file with a symlink to the CKAN schema
   file included in the sources.

   .. parsed-literal::

      sudo mv /etc/solr/conf/schema.xml /etc/solr/conf/schema.xml.bak
      sudo ln -s |virtualenv|/src/ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml

#. Now restart Solr (use ``tomcat8`` on older Ubuntu versions)::

    sudo service tomcat9 restart

   .. note:: On Ubuntu 18.04 and older, instead of the Solr UI you may see an Internal Server Error page with a message containing:

     .. parsed-literal::

      java.io.IOException: Cannot create directory: /var/lib/solr/data/index

     This is caused by a `bug <https://bugs.launchpad.net/ubuntu/+source/lucene-solr/+bug/1829611>`_ and you need to run some extra commands to fix it:


     .. parsed-literal::

        sudo mv /etc/systemd/system/tomcat9.d /etc/systemd/system/tomcat9.service.d
        sudo systemctl daemon-reload
        sudo service tomcat9 restart


Next steps with Solr
====================

To check that Solr started you can visit the web interface at http://localhost:8983/solr

.. warning:: The two installation methods above will leave you with a setup that is fine for local development, but Solr should never be exposed publicly in a production site. Pleaser refer to the `Solr documentation <https://solr.apache.org/guide/securing-solr.html>`_ to learn how to secure your Solr instance.


If you followed any of the instructions above, the CKAN Solr core will be available at http://localhost:8983/solr/ckan. If for whatever reason you ended up with a different one (eg with a different port, host or core name), you need to change the :ref:`solr_url` setting in your :ref:`config_file` (|ckan.ini|) to point to your Solr server, for example::

       solr_url=http://my-solr-host:8080/solr/ckan-2.9


.. _Solr: https://solr.apache.org/
.. _Docker: https://www.docker.com/