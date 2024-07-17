---------------
Installing CKAN
---------------

.. include:: /_supported_versions.rst

CKAN 2.10 supports Python 3.8 to Python 3.11.

Before you can use CKAN on your own computer, you need to install it.
There are three ways to install CKAN:

#. Install from an operating system package
#. Install from source
#. Install from Docker Compose


Additional deployment tips can be found in our wiki, such as the recommended
`Hardware Requirements <https://github.com/ckan/ckan/wiki/Hardware-Requirements>`_.

Package install
===============

Installing from package is the quickest and easiest way to install CKAN, but it requires
Ubuntu 20.04 64-bit or Ubuntu 22.04 64-bit.

You should install CKAN from package if:

* You want to install CKAN on an Ubuntu 20.04 or 22.04, 64-bit server, *and*
* You only want to run one CKAN website per server

See :doc:`install-from-package`.

Source install
==============

You should install CKAN from source if:

* You want to install CKAN on a 32-bit computer, *or*
* You want to install CKAN on a different version of Ubuntu, not 20.04 or 22.04, *or*
* You want to install CKAN on another operating system (eg. RHEL, CentOS, OS X), *or*
* You want to run multiple CKAN websites on the same server, *or*
* You want to install CKAN for development

See :doc:`install-from-source`.

Docker Compose install
======================

The `ckan-docker <https://github.com/ckan/ckan-docker>`_ repository contains the necessary scripts 
and images to install CKAN using Docker Compose. It provides a clean and quick way to deploy a
standard CKAN instance pre-configured with the :doc:`Filestore <../filestore>` and :doc:`../datastore`.
It also allows the addition (and customization) of extensions. The emphasis leans more towards
a Development environment, however the base install can be used as the foundation for progressing
to a Production environment. Please note that a fully-fledged CKAN Production system using Docker containers is 
beyond the scope of the provided setup.
 
You should install CKAN from Docker Compose if:

* You want to install CKAN with less effort than a source install and more flexibility than a
  package install, **or**
* You want to run or even develop extensions with the minimum setup effort, **or**
* You want to see whether and how CKAN, Docker and your respective infrastructure will fit
  together.

To install CKAN using Docker Compose, follow the links below:


* `Configuration and setup files to run a CKAN site <https://github.com/ckan/ckan-docker>`_.

* `Official Docker images for CKAN <https://github.com/ckan/ckan-docker-base>`_.


If you've already setup a CKAN website and want to upgrade it to a newer
version of CKAN, see :doc:`/maintaining/upgrading/index`.

------------

.. toctree::
   :maxdepth: 1

   install-from-package
   install-from-source
   deployment
