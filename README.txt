## Introduction

The ckan software is used to run the CKAN/OpenRegistry site (CKAN stands for
the Comprehensive knowledge Archive Network) which provides a listing of
(mainly open) knowledge packages.

## Copying

Copyright (c) 2006-2007 Open Knowledge Foundation.

Licensed under the MIT license.

## Authors

Rufus Pollock <rufus@rufuspollock.org>

## Installation and Setup

Install ``ckan`` using easy_install::

    easy_install ckan

Make a config file as follows::

    paster make-config ckan config.ini

Tweak the config file as appropriate and then setup the application::

    paster setup-app config.ini

## Tests

When starting from a clean system for the tests to run properly you will need
to:

  1. Create the basic db structure: $ bin/ckan-admin rebuild
  2. Create some basic test data: $ bin/ckan-admin testdata

To run the tests you should use py.test:

    $ py.test ckan/tests

