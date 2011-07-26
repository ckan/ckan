======================
Developer Installation
======================

This section marks the start of the second half of this manual, covering advanced usage of CKAN. 

To do a developer install, please first follow the standard :doc:`install` guide, using Debian packages to get a working instance of CKAN. 

After that you'll need to set up and enter a virtual Python environment, as follows: 

::

    sudo apt-get install virtualenv pip mercurial
    virtualenv /home/ubuntu/pyenv
    . /home/ubuntu/pyenv/bin/activate

To develop against any dependencies, you first need a developer install of CKAN itself. You can install CKAN like this:

::

	pip install -e hg+http://bitbucket.org/okfn/ckan#egg=ckan
		
You can now install any of the developer versions of the CKAN dependencies you want to work on like this (using the appropriate URL):

::

    pip install -e hg+http://bitbucket.org/okfn/<dependency-name>@<version>#egg=<egg-name>

The dependency you've installed will appear in ``/home/ubuntu/pyenv/src/`` where you can work on it. 

To test your changes you'll need to use the ``paster serve`` command from the ``ckan`` directory:

::

    cd /home/ubuntu/pyenv/src/ckan
    . ../../bin/activate
    paster make-config ckan development.ini

Then make any changes to the ``development.ini`` file that you need before continuing:

::

    paster db upgrade
    paster serve --reload

Your new CKAN developer install (together with any new dependencies you have installed in developer mode) will be running on http://localhost:5000/

After installing CKAN, you should make sure that your deployment passes the tests, as described in :doc:`test`.
