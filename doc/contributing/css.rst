====================
CSS coding standards
====================

.. Note::
  For CKAN 2.0 we use Sass as a pre-processor for our core CSS. View
  `Front-end Documentation <./frontend/index.html#stylesheets>`_
  for more information on this subject.

----------
Formatting
----------

All CSS documents must use **two spaces** for indentation and files should have
no trailing whitespace. Other formatting rules:

- Use soft-tabs with a two space indent.
- Use double quotes.
- Use shorthand notation where possible.
- Put spaces after ``:`` in property declarations.
- Put spaces before ``{`` in rule declarations.
- Use hex color codes ``#000`` unless using ``rgba()``.
- Always provide fallback properties for older browsers.
- Use one line per property declaration.
- Always follow a rule with one line of whitespace.
- Always quote ``url()`` and ``@import()`` contents.
- Do not indent blocks.

For example: ::

    .media {
      overflow: hidden;
      color: #fff;
      background-color: #000; /* Fallback value */
      background-image: linear-gradient(black, grey);
    }

    .media .img {
      float: left;
      border: 1px solid #ccc;
    }

    .media .img img {
      display: block;
    }

    .media .content {
      background: #fff url("../images/media-background.png") no-repeat;
    }

------
Naming
------

All ids, classes and attributes must be lowercase with hyphens used for
separation. ::

    /* GOOD */
    .dataset-list {}

    /* BAD */
    .datasetlist {}
    .datasetList {}
    .dataset_list {}

--------
Comments
--------

Comments should be used liberally to explain anything that may be unclear at
first glance, especially IE workarounds or hacks. ::

    .prose p {
      font-size: 1.1666em /* 14px / 12px */;
    }

    .ie7 .search-form {
      /*
        Force the item to have layout in IE7 by setting display to block.
        See: http://reference.sitepoint.com/css/haslayout
      */
      display: inline-block;
    }

--------------------------
Modularity and specificity
--------------------------

Try keep all selectors loosely grouped into modules where possible and avoid
having too many selectors in one declaration to make them easy to override. ::

    /* Avoid */
    ul#dataset-list {}
    ul#dataset-list li {}
    ul#dataset-list li p a.download {}

Instead here we would create a dataset "module" and styling the item outside of
the container allows you to use it on it's own e.g. on a dataset page: ::

    .dataset-list {}
    .dataset-list-item {}
    .dataset-list-item .download {}

In the same vein use classes make the styles more robust, especially where the
HTML may change. For example when styling social links: ::

    <ul class="social">
      <li><a href="">Twitter</a></li>
      <li><a href="">Facebook</a></li>
      <li><a href="">LinkedIn</a></li>
    </ul>

You may use pseudo selectors to keep the HTML clean: ::

    .social li:nth-child(1) a {
      background-image: url(twitter.png);
    }

    .social li:nth-child(2) a {
      background-image: url(facebook.png);
    }

    .social li:nth-child(3) a {
      background-image: url(linked-in.png);
    }

However this will break any time the HTML changes for example if an item is
added or removed. Instead we can use class names to ensure the icons always
match the elements (Also you'd probably sprite the image :). ::

    .social .twitter {
      background-image: url(twitter.png);
    }

    .social .facebook {
      background-image: url(facebook.png);
    }

    .social .linked-in {
      background-image: url(linked-in.png);
    }

Avoid using tag names in selectors as this prevents re-use in other contexts. ::

    /* Cannot use this class on an <ol> or <div> element */
    ul.dataset-item {}

Also ids should not be used in selectors as it makes it far too difficult to
override later in the cascade. ::

    /* Cannot override this button style without including an id */
    .btn#download {}
