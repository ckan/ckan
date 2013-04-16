Building a JavaScript Module
============================

CKAN makes heavy use of modules to add additional functionality to the
page. Essentially all a module consists of is an object with an
``.initialize()`` and ``.teardown()`` method.

Here we will go through the basic functionality of building a simple
module that sends a "favourite" request to the server when the user
clicks a button.

HTML
----

The idea behind modules is that the element should already be in the
document when the page loads. For example our favourite button will work
just fine without our module JavaScript loaded.

::

    <form action="/favourite" method="post" data-module="favorite">
      <button class="btn" name="package" value="101">Submit</button>
    </form>

Here it's the ``data-module="favorite"`` that tells the CKAN module
loader to create a new instance for this element.

JavaScript
----------

Modules reside in the *javascript/modules* directory and should share
the same name as the module. We use hyphens to delimit spaces in both
filenames and modules.

::

    /javascript/modules/favorite.js

A module can be created by calling ``ckan.module()``:

::

    ckan.module('favorite', function (jQuery, _) {
      return {};
    });

We pass in the module name and a factory function that should return our
module object. This factory gets passed a local jQuery object and a
translation object.

.. Note::
    In order to include a module for page render inclusion within an
    extension it is recommended that you use ``{% resource %}`` within
    your templates. See the `Resource Documentation <./resources.html>`_

Initialisation
~~~~~~~~~~~~~~

Once ckan has found an element on the page it creates a new instance of
your module and if present calls the ``.initialize()`` method.

::

    ckan.module('favorite', function (jQuery, _) {
      return {
        initialize: function () {
          console.log('I've been called for element: %o', this.el);
        }
      };
    });

Here we can set up event listeners and other setup functions.

::

    initialize: function () {
      // Grab our button and assign it to a property of our module.
      this.button = this.$('button');

      // Watch for our favourite button to be clicked.
      this.button.on('submit', jQuery.proxy(this._onClick, this));
    },
    _onClick: function (event) {}

Event Handling
~~~~~~~~~~~~~~

Now we create our click handler for the button:

::

    _onClick: function (event) {
      event.preventDefault();
      this.favorite();
    }

And this calls a ``.favorite()`` method. It's generally best not to do
too much in event handlers it means that you can't use the same
functionality elsewhere.

::

    favorite: function () {
      // The client on the sandbox should always be used to talk to the api.
      this.sandbox.client.favoriteDataset(this.button.val());
    }

Notifications and Internationalisation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This submits the dataset to the API but ideally we want to tell the user
what we're doing.

::

    options: {
      i18n: {
        loading: _('Favouriting dataset'),
        done: _('Favourited dataset %(id)s')
      }
    },
    favorite: function () {
      // i18n gets a translation key from the options object.
      this.button.text(this.i18n('loading'));

      // The client on the sandbox should always be used to talk to the api.
      var request = this.sandbox.client.favoriteDataset(this.button.val())
      request.done(jQuery.proxy(this._onSuccess, this));
    },
    _onSuccess: function () {
      // We can perform interpolation on messages.
      var message = this.i18n('done', {id: this.button.val()});

      // Notify allows global messages to be displayed to the user.
      this.sandbox.notify(message, 'success');
    }

Options
~~~~~~~

Displaying an id to the user isn't very friendly. We can use the
``data-module`` attributes to pass options through to the module.

::

    <form action="/favourite" method="post" data-module="favorite" data-module-dataset="my dataset">

This will override the defaults in the options object.

::

    ckan.module('favorite', function (jQuery, _) {
      return {
        options: {
          dataset: '',
          i18n: {...}
        }
        initialize: function () {
          console.log('this dataset is: %s', this.options.dataset);
          //=> "this dataset is: my dataset"
        }
      };
    });

Error handling
~~~~~~~~~~~~~~

When ever we make an Ajax request we want to make sure that we notify
the user if the request fails. Again we can use
``this.sandbox.notify()`` to do this.

::

    favorite: function () {
      // The client on the sandbox should always be used to talk to the api.
      var request = this.sandbox.client.favoriteDataset(this.button.val())
      request.done(jQuery.proxy(this._onSuccess, this));
      request.fail(jQuery.proxy(this._onError, this));
    },
    _onError: function () {
      var message = this.i18n('error', {id: this.button.val()});

      // Notify allows global messages to be displayed to the user.
      this.sandbox.notify(message, 'error');
    }

Module Scope
~~~~~~~~~~~~

You may have noticed we keep making calls to ``jQuery.proxy()`` within
these methods. This is to ensure that ``this`` when the callback is
called is the module it belongs to.

We have a shortcut method called ``jQuery.proxyAll()`` that can be used
in the ``.initialize()`` method to do all the binding at once. It can
accept method names or simply a regexp.

::

    initialize: function () {
      jQuery.proxyAll(this, '_onSuccess');

      // Same as:
      this._onSuccess = jQuery.proxy(this, '_onSuccess');

      // Even better do all methods starting with _on at once.
      jQuery.proxyAll(this, /_on/);
    }

Publish/Subscribe
~~~~~~~~~~~~~~~~~

Sometimes we want modules to be able to talk to each other in order to
keep the page state up to date. The sandbox has the ``.publish()`` and
``.subscribe()`` methods for just this cause.

For example say we had a counter up in the header that showed how many
favourite datasets the user had. This would be incorrect when the user
clicked the ajax button. We can publish an event when the favorite
button is successful.

::

    _onSuccess: function () {
      // Notify allows global messages to be displayed to the user.
      this.sandbox.notify(message, 'success');

      // Tell other modules about this event.
      this.sandbox.publish('favorite', this.button.val());
    }

Now in our other module 'user-favorite-counter' we can listen for this.

::

    ckan.module('user-favorite-counter', function (jQuery, _) {
      return {
        initialize: function () {
          jQuery.proxyAll(this, /_on/);
          this.sandbox.subscribe('favorite', this._onFavorite);
        },
        teardown: function () {
          // We must always unsubscribe on teardown to prevent memory leaks.
          this.sandbox.unsubscribe('favorite', this._onFavorite);
        },
        incrementCounter: function () {
          var count = this.el.text() + 1;
          this.el.text(count);
        },
        _onFavorite: function (id) {
          this.incrementCounter();
        }
      };
    });

Unit Tests
----------

Every module has unit tests. These use Mocha, Chai and Sinon to assert
the expected functionality of the module.
