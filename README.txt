README
++++++

Introduction
============

Comprehensive Knowledge Archive Network (CKAN) Software.

See :mod:`ckan.__long_description__` for more information.


Developer Installation
======================

1. Get the code and install it:

   We recommend installing using pip and virtualenv::
   
      # grab the install requirements from the ckan mercurial repo
      # Or checkout the mercurial repo directly!
      wget http://knowledgeforge.net/ckan/hg/raw-file/tip/pip-requirements.txt
      # create a virtualenv to install into
      virtualenv pyenv-ckan
      # install using pip-requirements
      pip -E pyenv-ckan install -r pip-requirements.txt

3. Make a config file as follows::

      # NB: you need to activate the virtualenv
      paster --plugin ckan make-config ckan {your-config.ini}

4. Tweak the config file as appropriate and then setup the application::

      paster --plugin ckan setup-app {your-config.ini}

   NB: you'll need to setup a database -- see sqlalchemy.url config option.
   We support only PostgreSQL at this time. You'll need to install the relevant
   python library (eg. On debiani/ubuntu: python-psycopg2)

   NB: You may also need to create the Pylon's cache directory specified by
   cache_dir in the config file.

5. Run the webserver::

      paster serve {your-config.ini} 

6. Point your browser at: localhost:5000 (if you set a different port in your
   config file then youl will need to change 5000 to whatever port value you
   chose).


Test
====

Make sure you've created a config called development.ini, then:: 

    nosetests ckan/tests


Documentation
=============

The home page for the CKAN project is: http://knowledgeforge.net/ckan

This file is part of the developer docs. The complete developer docs are built from the ckan repository using `Sphinx <http://sphinx.pocoo.org/>`_ and uploaded by an admin to KnowledgeForge. To build the developer docs::

      python setup.py build_sphinx
 

Contributors
============

  * Rufus Pollock <rufus [at] rufuspollock [dot] org>
  * David Read
  * John Bywater
  * Nick Stenning (css and js)

Also especial thanks to the following projects without whom this would not have
been possible:

  * CKAN logo: "angry hamster" http://www.maedelmaedel.com/ and
    http://www.villainous.biz/
  * famfamfam.com for silk icons <http://www.famfamfam.com/lab/icons/silk/>
  * Pylons: <http://pylonshq.com/>
  * Python: <http://www.python.org>


Copying and License
===================

This material is copyright (c) 2006-2010 Open Knowledge Foundation.

It is open and licensed under the GNU Affero General Public License (AGPL) v3.0
whose full text may be found at:

<http://www.fsf.org/licensing/licenses/agpl-3.0.html>

