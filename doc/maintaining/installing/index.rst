---------------
Installing CKAN
---------------

Before you can use CKAN on your own computer, you need to install it.
There are three ways to install CKAN:

#. Install from an operating system package
#. Install from source
#. Install from Docker Compose

CKAN 2.9 supports Python 3.6 or higher and Python 2.7. The next version of CKAN
will support Python 3 only.

Installing from package is the quickest and easiest way to install CKAN, but it requires
Ubuntu 18.04 64-bit or Ubuntu 20.04 64-bit. 

**You should install CKAN from package if**:

* You want to install CKAN on an Ubuntu 18.04 or 20.04, 64-bit server, *and*
* You only want to run one CKAN website per server

See :doc:`install-from-package`.

**You should install CKAN from source if**:

* You want to install CKAN on a 32-bit computer, *or*
* You want to install CKAN on a different version of Ubuntu, not 18.04 or 20.04, *or*
* You want to install CKAN on another operating system (eg. RHEL, CentOS, OS X), *or*
* You want to run multiple CKAN websites on the same server, *or*
* You want to install CKAN for development

See :doc:`install-from-source`.

The provided Docker Compose configuration provides a clean and quick way to deploy a vanilla CKAN
without extensions, while still allowing the addition (and customization) of extensions.
This option comes with the caveat that some further steps need to be taken to deploy a
production-ready CKAN. **You should install CKAN from Docker Compose if**:

* You want to install CKAN with less effort than a source install and more flexibility than a
  package install, **or**
* You want to run or even develop extensions with the minimum setup effort, **or**
* You want to see whether and how CKAN, Docker and your respective infrastructure will fit
  together.

See :doc:`install-from-docker-compose`.

If you've already setup a CKAN website and want to upgrade it to a newer
version of CKAN, see :doc:`/maintaining/upgrading/index`.

------------

.. toctree::
   :maxdepth: 1

   install-from-package
   install-from-source
   install-from-docker-compose
   deployment
