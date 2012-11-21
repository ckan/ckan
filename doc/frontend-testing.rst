Front-end Testing
=================

All new CKAN features should be coded so that they work in the
following browsers:

* Internet Explorer: 9, 8 and 7
* Firefox: Latest
* Chrome: Latest

These browsers are determined by whatever has >= 1% share on this
page: http://data.gov.uk/data/site-usage?month=2012-11

Install browser virtual machines
================================

In order to test in all the needed browsers you'll need access to
all the above browser versions. Firefox and Chrome should be easy
whatever platform you are on. Internet Explorer is a little trickier.
You'll need Virtual Machines.

We suggest you use https://github.com/xdissent/ievms to get your
Internet Explorer virtual machines.

Testing methodology
===================

Firstly we have a primer page. If you've touched any of the core
front-end code you'll need to check if the primer is rendering
correctly. The primer is located at:
http://localhost:5000/testing/primer and it should look like:
https://dl.dropbox.com/s/69y9ecpf3u3zkpe/ckan-primer.png

Secondly whilst writing a new feature you should endeavour to test
in at least in your core browser and an alternative browser as often
as you can.

Thirdly you should fully test all new features that have a front-end
element in all browsers before making your pull request into
CKAN master.

Common pitfulls & their fixes
=============================

Here's a few of the most common front end bugs and a list of their
fixes.

Reserved JS keywords
--------------------

Since IE has a stricter language definition in JS it really doesn't
like you using JS reserved keywords method names, variables, etc...
This is a good list of keywords not to use in your JavaScript:

https://developer.mozilla.org/en-US/docs/JavaScript/Reference/Reserved_Words

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
