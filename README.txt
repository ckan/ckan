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

To run the tests you should use py.test

