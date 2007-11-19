## Introduction

The ckan software is used to run the CKAN/OpenRegistry site (CKAN stands for
the Comprehensive knowledge Archive Network) which provides a listing of
(mainly open) knowledge packages.


## Copying

This material is open and licensed under the MIT license as follows:

Copyright (c) 2006-2007 Open Knowledge Foundation.

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


## Authors

Rufus Pollock <rufus [at] rufuspollock [dot] org>
Nick Stenning
John Bywater (v0.1 only)


## Installation and Setup

1. Get the code if you do not have it already (see Getting the Code below).

2. Install it:

      $ sudo python setup.py

   If you want to work from a subversion copy and plan to make modifications do:
   
      $ sudo python setup.py develop

   This step should install most the library dependencies for CKAN. However
   some dependencies may not be able to be installed automatically. Please see
   install_requires option (and associated comments) in setup.py.

3. Make a config file as follows:

      $ paster make-config ckan config.ini

   Alternatively just copy an existing configuration (such as development.ini):

      $ cp development.ini config.ini

4. Tweak the config file as appropriate and then setup the application::

      $ paster setup-app config.ini

5. Run the webserver:

      $ paster serve config.ini 

6. Point your browswer at: localhost:5000 (if you set a different port in your
   config file then youl will need to change 5000 to whatever port value you
   chose).

7. [optional] Production deployment. CKAN2 is built using pylons. A full
   walkthrough of production deployment can be found at:

   http://pylonshq.com/project/pylonshq/wiki/FastCGI.


## Getting the Code

Download ckan or checkout the code from the subversion repository.


## Tests

When starting from a clean system for the tests to run properly you will need
to:

  1. Create the basic db structure: $ bin/ckan-admin rebuild
  2. Create some basic test data: $ bin/ckan-admin testdata

To run the tests you should use py.test:

    $ py.test ckan/tests

Note that the functional tests require twill: <http://twill.idyll.org/>
