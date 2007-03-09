## Introduction

The ckan software is used to run the CKAN/OpenRegistry site (CKAN stands for
the Comprehensive knowledge Archive Network) which provides a listing of
(mainly open) knowledge packages.


## Copying

Copyright (c) 2006-2007 Open Knowledge Foundation.

Licensed under the MIT license:
  
  <http://www.opensource.org/licenses/mit-license.php>


## Authors

Rufus Pollock <rufus@rufuspollock.org>


## Installation and Setup

1. Get the code if you do not have it already (see Getting the Code below).

2. Install it:

      $ sudo python setup.py

   If you want to work from a subversion copy and plan to make modifications do:
   
      $ sudo python setup.py develop

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

7. [optional] Production deployment. Ckan2 is built using pylons. A full
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
