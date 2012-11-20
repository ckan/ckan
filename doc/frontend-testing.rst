Front-end Testing
=================

All CKAN features should be coded so that they work in the
following browsers:

* Internet Explorer: 9, 8 and 7
* Firefox: Latest
* Chrome: Latest

These browsers are determined by whatever has >=1% share
on this page <http://data.gov.uk/data/site-usage?month=2012-11>

Install browser virtual machines
================================

In order to test in all the needed browsers you'll need access to
all the above browser versions. Firefox and Chrome should be easy
whatever platform you are on. Internet Explorer is a little trickier.
You'll need Virtual Machines.

We suggest you use <https://github.com/xdissent/ievms> to get an
Internet Explorer virtual machines.

Testing methodology
===================

Soon...

Common pitfulls & their fixes
=============================

Reserver JS keywords
--------------------

Since IE has a stricter language definition in JS it really doesn't
like you using JS reserved keywords method names, variables, etc...
This is a good list of keywords not to use in your JavaScript:

<https://developer.mozilla.org/en-US/docs/JavaScript/Reference/Reserved_Words>

Unclosed JS arrays / objects
----------------------------

Internet Explorer doesn't like it's JS to have unclosed JS objects
and arrays. For example:

::

    var foo = {
    	bar: 'Test',
    };

Will break. However:

::

    var foo = {
    	bar: 'Test'
    };

Will not break.