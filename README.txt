Introduction
============

Comprehensive Knowledge Archive Network (CKAN) Software.

See ckan.__long_description__ for more information.


Installation and Setup
======================

1. Get the code and install it:

   Get it from the mercurial repo::
   
      hg clone https://knowledgeforge.net/ckan/hg ckan

   Install it::

      cd ckan
      python setup.py

   Alternatively you can install using pip::
   
      virtualenv --no-site-packages pyenv-ckan
      # or using http://www.doughellmann.com/projects/virtualenvwrapper/
      # mkvirtualenv --no-site-packages pyenv-ckan
      pip -E pyenv-ckan install --editable hg+https://knowledgeforge.net/ckan/hg#egg=ckan
      # or using pip-requirements if you've grabbed it
      # pip -E pyenv-ckan install -r pip-requirements.txt

   This step should install most the library dependencies for CKAN. However
   some dependencies may not be able to be installed automatically. Please see
   install_requires option (and associated comments) in setup.py.

3. Make a config file as follows::

      paster make-config ckan config.ini

4. Tweak the config file as appropriate and then setup the application::

      paster setup-app config.ini

5. Run the webserver::

      paster serve config.ini 

5. Run the webserver for ::

      paster serve --reload config.ini 

6. Point your browswer at: localhost:5000 (if you set a different port in your
   config file then youl will need to change 5000 to whatever port value you
   chose).


## Contributors

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


## Tests

Make sure you've created a config called development.ini, then:: 

    nosetests ckan/tests


## Copying

This material is open and licensed under the MIT license as follows:

Copyright (c) 2006-2009 Open Knowledge Foundation.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.


