=========================
Prepare to Use Extensions
=========================

If you are running a package installation of CKAN, before you start using and testing extensions (described in :doc:`extensions`) you need to prepare your system. 

Firstly, you'll need to set up and enter a virtual Python environment, as follows: 

::

    # install software we need (virtualenv and git to retrieve the source code)
    sudo apt-get install python-virtualenv git-core
    # create a python virtual env and activate
    virtualenv /home/ubuntu/pyenv
    . /home/ubuntu/pyenv/bin/activate

Then, you need to install the CKAN source into your virtual environment. You can install CKAN like this:

::

	pip install -e git+http://github.com/okfn/ckan#egg=ckan
	
Your new CKAN developer install will be running on http://localhost:5000/
		
When you start using extensions, you should install any of the developer versions of the CKAN extensions you want to work on like this (using the appropriate URL):

::

    pip install -e git+http://github.com/okfn/<dependency-name>@<version>#egg=<egg-name>

The dependency you've installed will appear in ``/home/ubuntu/pyenv/src/`` where you can work on it. 

After working on extensions, you should make sure that your deployment passes the tests, as described in :doc:`test`.
