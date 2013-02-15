HTML Coding Standards
=====================

Formatting
----------

All HTML documents must use **two spaces** for indentation and there should be
no trailing whitespace. XHTML syntax must be used (this is more a Genshi
requirement) and all attributes must use double quotes around attributes. ::

    <!-- XHTML boolean attributes must still have values and self closing tags must have a closing / -->
    <video autoplay="autoplay" poster="poster_image.jpg">
      <source src="foo.ogg" type="video/ogg" />
    </video>

HTML5 elements should be used where appropriate reserving ``<div>`` and ``<span>``
elements for situations where there is no semantic value (such as wrapping
elements to provide styling hooks).

Doctype and layout
------------------

All documents must be using the HTML5 doctype and the ``<html>`` element should
have a ``"lang"`` attribute. The ``<head>`` should also at a minimum include
``"viewport"`` and ``"charset"`` meta tags. ::

    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Example Site</title>
      </head>
      <body></body>
    </html>

Forms
-----

Form fields must always include a ``<label>`` element with a ``"for"`` attribute
matching the ``"id"`` on the input. This helps accessibility by focusing the
input when the label is clicked, it also helps screen readers match labels to
their respective inputs. ::

    <label for="field-email">email</label>
    <input type="email" id="field-email" name="email" value="" />

Each ``<input>`` should have an ``"id"`` that is unique to the page. It does not
have to match the ``"name"`` attribute.

Forms should take advantage of the new HTML5 input types where they make sense
to do so, placeholder attributes should also be included where relevant.
Including these can provided enhancements in browsers that support them such as
tailored inputs and keyboards. ::

    <div>
      <label for="field-email">Email</label>
      <input type="email" id="field-email" name="email" value="name@example.com" />
    </div>
    <div>
      <label for="field-phone">Phone</label>
      <input type="phone" id="field-phone" name="phone" value="" placeholder="+44 077 12345 678" />
    </div>
    <div>
      <label for="field-url">Homepage</label>
      <input type="url" id="field-url" name="url" value="" placeholder="http://example.com" />
    </div>

Wufoo provides an `excellent reference`_ for these attributes.

.. _excellent reference: http://wufoo.com/html5/

Including meta data
-------------------

Classes should ideally only be used as styling hooks. If you need to include
additional data in the html document, for example to pass data to JavaScript,
then the HTML5 ``data-`` attributes should be used. ::

    <a class="btn" data-format="csv">Download CSV</a>

These can then be accessed easily via jQuery using the ``.data()`` method. ::

    jQuery('.btn').data('format'); //=> "csv"

    // Get the contents of all data attributes.
    jQuery('.btn').data(); => {format: "csv"}

One thing to note is that the JavaScript API for datasets will convert all
attribute names into camelCase. So ``"data-file-format"`` will become ``fileFormat``.

For example: ::

    <a class="btn" data-file-format="csv">Download CSV</a>

Will become: ::

    jQuery('.btn').data('fileFormat'); //=> "csv"
    jQuery('.btn').data(); => {fileFormat: "csv"}

Targeting Internet Explorer
---------------------------

Targeting lower versions of Internet Explorer (IE), those below version 9,
should be handled by the stylesheets. Small fixes should be provided inline
using the ``.ie`` specific class names. Larger fixes may require a separate
stylesheet but try to avoid this if at all possible.

Adding IE specific classes: ::

    <!doctype html>
    <!--[if lt IE 7]> <html lang="en" class="ie ie6"> <![endif]-->
    <!--[if IE 7]>    <html lang="en" class="ie ie7"> <![endif]-->
    <!--[if IE 8]>    <html lang="en" class="ie ie8"> <![endif]-->
    <!--[if gt IE 8]><!--> <html lang="en"> <!--<![endif]-->

.. note:: Only add lines for classes that are actually being used.

These can then be used within the CSS: ::

    .clear:before,
    .clear:after {
        content: "";
        display: table;
    }

    .clear:after {
        clear: both;
    }

    .ie7 .clear {
        zoom: 1; /* For IE 6/7 (trigger hasLayout) */
    }

i18n
----

Don't include line breaks within ``<p>`` blocks.  ie do this: ::

  <p>Blah foo blah</p>
  <p>New paragraph, blah</p>

And **not**: ::

  <p>Blah foo blah
     New paragraph, blah</p>

