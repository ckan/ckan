"""Accumulate messages to show on the next page request.

The ``Flash`` class is useful when you want to redirect to another page and also
show a status message on that page, such as "Changes saved" or 
"No previous search found; returning to home page".

THE IMPLEMENTATION DEPENDS ON PYLONS.  However, it can easily be adapted
for another web framework.

PYRAMID USERS: use the flash methods built into Pyramid's ``Session`` object.
This implementation is incompatible with Pyramid.

A typical Pylons application instantiates a ``Flash`` object in 
myapp/lib/helpers.py::

    from webhelpers.pylonslib.flash import Flash as _Flash
    flash = _Flash()

The helpers module is then imported into your controllers and
templates as ``h``.  Whenever you want to set a message, call the instance::

    h.flash("Record deleted.")

You can set additional messages too::

    h.flash("Hope you didn't need it.")

Now make a place in your site template for the messages.  In Mako you
might do:

.. code-block:: mako

    <% messages = h.flash.pop_messages() %>
    % if messages:
    <ul id="flash-messages">
        % for message in messages:
        <li>${message}</li>
        % endfor
    </ul>
    % endif

You can style this to look however you want:

.. code-block:: css

    ul#flash-messages {
        color: red;
        background-color: #FFFFCC;
        font-size: larger;
        font-style: italic;
        margin-left: 40px;
        padding: 4px;
        list-style: none;
        }

Multiple flash objects
======================

You can define multiple flash objects in your application to display
different kinds of messages at different places on the page.  For instance,
you might use the main flash object for general messages, and a second
flash object for "Added dookickey" / "Removed doohickey" messages next to a
doohickey manager.

Message categories
==================

WebHelpers 1.0 adds message categories, contributed by Wichert Akkerman.
These work like severity levels in Python's logging system.  The standard
categories are "*warning*", "*notice*", "*error*", and "*success*", with
the default being "*notice*".  The category is available in the message's
``.category`` attribute, and is normally used to set the container's CSS
class.  

This is the *only* thing it does. Calling ``.pop_messages()`` pops all messages
in the order registered, regardless of category.  It is *not* possible to pop
only a certain category, or all levels above a certain level, or to group
messages by category. If you want to group different kinds of messages
together, or pop only certain categories while leaving other categories, you
should use multiple ``Flash`` objects.

You can change the standard categories by overriding the ``.categories``
and ``.default_category`` class attributes, or by providing alternate
values using constructor keywords.

Category example
----------------

Let's show a standard way of using flash messages in your site: we will
demonstrate *self-healing messages* (similar to what Growl does on OSX)
to show messages in a site.

To send a message from python just call the flash helper method::

   h.flash(u"Settings have been saved")

This will tell the system to show a message in the rendered page. If you need
more control you can specify a message category as well: one of *warning*,
*notice*, *error* or *success*. The default category is *notice*. For example::

   h.flash(u"Failed to send confirmation email", "warning")

We will use a very simple markup style: messages will be placed in a ``div``
with id ``selfHealingFeedback`` at the end of the document body. The messages
are standard paragraphs with a class indicating the message category. For
example::

  <html>
    <body>
      <div id="content">
        ...
        ...
      </div>
      <div id="selfHealingFeedback">
        <p class="success">Succesfully updated your settings</p>
        <p class="warning">Failed to send confirmation email</p>
      </div>
    </body>
  </html>

This can easily created from a template. If you are using Genshi this
should work:

.. code-block: html

  <div id="selfHealingFeedback">
    <p class="notice" py:for="message in h.flash.pop_messages()"
       py:attrs="{'class' : message.category}" py:content="message">
      This is a notice.
    </p>
  </div>

The needed CSS is very simple:

.. code-block: css

    #selfHealingFeedback {
        position: fixed;
        top: 20px;
        left: 20px;
        z-index: 2000;
    }

    #selfHealingFeedback p {
        margin-bottom: 10px;
        width: 250px;
        opacity: 0.93;
    }

    p.notice,p.error,p.success,p.warning {
        border: 3px solid silver;
        padding: 10px;
        -webkit-border-radius: 3px;
        -moz-border-radius: 3px;
        border-radius: 3px;
        -webkit-box-shadow: 0 0 5px silver;
    }

Choosing different colours for the categories is left as an exercise
for the reader.

Next we create the javascript that will manage the needed behaviour (this
implementation is based on jQuery)::

    function _SetupMessage(el) {
        var remover = function () {
            msg.animate({opacity: 0}, "slow")
               .slideUp("slow", function() { msg.remove() }); };

        msg.data("healtimer", setTimeout(remover, 10000))
           .click(function() { clearTimeout(msg.data("healtimer")); remover(); });
    }

    function ShowMessage(message, category) {
        if (!category)
            category="notice";

        var container = $("#selfHealingFeedback");

        if (!container.length)
            container=$("<div id='selfHealingFeedback'/>").appendTo("body");

        var msg = $("<p/>").addClass(category).html(message);
        SetupMessage(msg);
        msg.appendTo(container);
    }

    $(document).ready(function() {
        $("#selfHealingFeedback p").each(function() { SetupMessage($(this)); });
    }

The ``SetupMessage`` function configures the desired behaviour: a message
disappears after 10 seconds, or if you click on it. Removal is done using
a simple animation to avoid messages jumping around on the screen.

This function is called for all messages as soon as the document has fully
loaded. The ``ShowMessage`` function works exactly like the ``flash`` method
in python: you can call it with a message and optionally a category and it
will pop up a new message.

JSON integration
----------------

It is not unusual to perform a remote task using a JSON call and show a
result message to the user. This can easily be done using a simple wrapper
around the ShowMessage method::

    function ShowJSONResponse(info) {
        if (!info.message)
            return;

        ShowMessage(info.message, info.message_category);
    }

You can use this direct as the success callback for the jQuery AJAX method::

   $.ajax({type: "POST",
           url:  "http://your.domain/call/json",
           dataType: "json",
           success: ShowJSONResponse
   });

if you need to perform extra work in your callback method you can call
it yourself as well, for example::

   <form action="http://your.domain/call/form">
     <input type="hidden" name="json_url" value="http://your.domain/call/json">
     <button>Submit</button>
   </form>

   <sript type="text/javascript">
      $(document).ready(function() {
          $("button").click(function() {
              var button = $(this);

              button.addClass("processing");
              $.ajax({type: "POST",
                      url:  this.form["json_url"].value,
                      dataType: "json",
                      success: function(data, status) {
                          button.removeClass("processing");
                          ShowJSONResponse(data);
                       },
                       error: function(request, status, error) {
                          button.removeClass("processing");
                          ShowMessage("JSON call failed", "error");
                       }
              });

              return false;
          });
      });
   </script>

This sets up a simple form which can be submitted normally by non-javascript
enabled browsers. If a user does have javascript an AJAX call will be made
to the server and the result will be shown in a message. While the call is
active the button will be marked with a *processing* class.

The server can return a message by including a ``message`` field in its
response. Optionally a ``message_category`` field can also be included
which will be used to determine the message category. For example::

    @jsonify
    def handler(self):
       ..
       ..
       return dict(message=u"Settings successfully updated")
"""

# Do not import Pylons at module level; only within functions.  All WebHelpers
# modules should be importable on any Python system for the standard
# regression tests.

from webhelpers.html import escape

__all__ = ["Flash", "Message"]

class Message(object):
    """A message returned by ``Flash.pop_messages()``.

    Converting the message to a string returns the message text. Instances
    also have the following attributes:

    * ``message``: the message text.
    * ``category``: the category specified when the message was created.
    """

    def __init__(self, category, message):
        self.category=category
        self.message=message

    def __str__(self):
        return self.message

    __unicode__ = __str__

    def __html__(self):
        return escape(self.message)


class Flash(object):
    """Accumulate a list of messages to show at the next page request.
    """
    
    # List of allowed categories.  If None, allow any category.
    categories = ["warning", "notice", "error", "success"]
    
    # Default category if none is specified.
    default_category = "notice"

    def __init__(self, session_key="flash", categories=None, default_category=None):
        """Instantiate a ``Flash`` object.

        ``session_key`` is the key to save the messages under in the user's
        session. 

        ``categories`` is an optional list which overrides the default list 
        of categories. 

        ``default_category`` overrides the default category used for messages 
        when none is specified.
        """
        self.session_key = session_key
        if categories is not None:
            self.categories = categories
        if default_category is not None:
            self.default_category = default_category
        if self.categories and self.default_category not in self.categories:
            raise ValueError("unrecognized default category %r" % (self.default_category,))

    def __call__(self, message, category=None, ignore_duplicate=False):
        """Add a message to the session.

        ``message`` is the message text.

        ``category`` is the message's category. If not specified, the default
        category will be used.  Raise ``ValueError`` if the category is not
        in the list of allowed categories.
        
        If ``ignore_duplicate`` is true, don't add the message if another
        message with identical text has already been added. If the new
        message has a different category than the original message, change the
        original message to the new category.
        
        """
        if not category:
            category = self.default_category
        elif self.categories and category not in self.categories:
            raise ValueError("unrecognized category %r" % (category,))
        # Don't store Message objects in the session, to avoid unpickling
        # errors in edge cases.
        new_message_tuple = (category, message)
        from pylons import session
        messages = session.setdefault(self.session_key, [])
        # ``messages`` is a mutable list, so changes to the local variable are
        # reflected in the session.
        if ignore_duplicate:
            for i, m in enumerate(messages):
                if m[1] == message:
                    if m[0] != category:
                        messages[i] = new_message_tuple
                        session.save()
                    return    # Original message found, so exit early.
        messages.append(new_message_tuple)
        session.save()

    def pop_messages(self):
        """Return all accumulated messages and delete them from the session.

        The return value is a list of ``Message`` objects.
        """
        from pylons import session
        messages = session.pop(self.session_key, [])
        session.save()
        return [Message(*m) for m in messages]
