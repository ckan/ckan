CKAN is open-source data hub software. CKAN makes it easy to publish, share and
work with data. It's a data management system that provides a powerful platform
for cataloging, storing and accessing datasets with a rich front-end, full API
(for both data and catalog), visualization tools and more. Read more at
http://ckan.org/. 

 * Installation instructions: see docs at http://docs.ckan.org/
 * Project wiki: http://wiki.ckan.org/
 * Developer mailing list: ckan-dev@lists.okfn.org
 * Issue tracker: http://trac.ckan.org/

Building Documentation
======================

1. Install python-sphinx (>= 1.1)

2. Initialize the theme submodule::

    git submodule init
    git submodule update

3. Run the command to build the docs::

    python setup.py build_sphinx

Copying and License
===================

This material is copyright (c) 2006-2011 Open Knowledge Foundation.

It is open and licensed under the GNU Affero General Public License (AGPL) v3.0
whose full text may be found at:

http://www.fsf.org/licensing/licenses/agpl-3.0.html

