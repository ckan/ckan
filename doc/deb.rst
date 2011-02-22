Packaging CKAN as Debian Files
++++++++++++++++++++++++++++++

You need two virtual python environments, one for building the missing
dependencies and one for building the conflicting dependencies:

::
    wget http://pylonsbook.com/virtualenv.py 
    python virtualenv.py missing
    python virtualenv.py conflict
    cd missing
    bin/easy_install pip
    bin/pip install -e hg+https://hg.3aims.com/private/BuildKit#egg=BuildKit
    bin/pip install -r lucid_missing.txt
    cd ../conflict
    bin/easy_install pip
    bin/pip install -e hg+https://hg.3aims.com/private/BuildKit#egg=BuildKit
    bin/pip install -r lucid_conflict.txt

The BuildKit script will build and place Debian packages in
``~/python-packaging``.Make sure this directory is empty, otherwise things
could be removed or overwritten.

You'll also need the following tools:

::

    sudo apt-get install -y python wget dh-make devscripts build-essential fakeroot cdbs

And depending on the source repositories of the things you are packaging you'll probably need:

::

    sudo apt-get install -y mercurial git-core subversion

You run it like this:

::

    cd missing
    python -m buildkit.update_all .

You should find all your packages nicely created now.

Now let's create the ``python-ckan-deps`` package for all the conflicting packages:


::

    cd conflict/
    mkdir ckan-deps
    mv src/* ckan-deps
    mv ckan-deps src/
    cd ../
    python -m buildkit.deb conflict ckan-deps 1.3 http://ckan.org python-ckan

