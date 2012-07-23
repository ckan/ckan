
Plugins Toolkit
===============

To allow a safe way for extensions to interact with ckan a toolkit is
provided. We aim to keep this toolkit stable across ckan versions so
that extensions will work across diferent versions of ckan.

.. Note::

    It is advised that when writing extensions that all interaction with
    ckan is done via the toolkit so that they do not break when new
    versions of ckan are released.

Over time we will be expanding the functionality available via
this toolkit.

Example extension that registers a new helper function available to
templates via h.example_helper() ::

    import ckan.plugins as p


    class ExampleExtension(p.SingletonPlugin):

        p.implements(p.IConfigurer)
        p.implements(p.ITemplateHelpers)

        def update_config(self, config):
            # add template directory that contains our snippet
            p.toolkit.add_template_directory(config, 'templates')

        @classmethod
        def example_helper(cls, data=None):
            # render our custom snippet
            return p.toolkit.render_snippet('custom_snippet.html', data)


        def get_helpers(self):
            # register our helper function
            return {'example_helper': self.example_helper}

The following functions, classes and exceptions are provided by the toolkit.

*class* **CkanCommand**
  Base class for building paster functions.


*exception* **CkanVersionException**
  Exception raised if required ckan version is not available.


*exception* **NotAuthorized**
  Exception raised when an action is not permitted by a user.


*exception* **ObjectNotFound**
  Exception raised when an object cannot be found.


*exception* **ValidationError**
  Exception raised when supplied data is invalid.
  it contains details of the error that occurred.


**_** (*value*)
  Mark a string for translation. Returns the localized unicode
  string of value.
  
  Mark a string to be localized as follows::
  
  _('This should be in lots of languages')
  
  


**add_public_directory** (*config, relative_path*)
  Function to aid adding extra public paths to the config.
  The path is relative to the file calling this function.


**add_template_directory** (*config, relative_path*)
  Function to aid adding extra template paths to the config.
  The path is relative to the file calling this function.


**asbool** (*obj*)
  part of paste.deploy.converters: convert strings like yes, no, true, false, 0, 1 to boolean


**asint** (*obj*)
  part of paste.deploy.converters: convert stings to integers


**aslist** (*obj, sep=None, strip=True*)
  part of paste.deploy.converters: convert string objects to a list


**check_access** (*action, context, data_dict=None*)
  check that the named action with the included context and
  optional data dict is allowed raises NotAuthorized if the action is
  not permitted or True.


**check_ckan_version** (*min_version=None, max_version=None*)
  Check that the ckan version is correct for the plugin.


**get_action** (*action*)
  Get the requested action function.


*class* **literal**
  Represents an HTML literal.
  
  This subclass of unicode has a ``.__html__()`` method that is
  detected by the ``escape()`` function.
  
  Also, if you add another string to this string, the other string
  will be quoted and you will get back another literal object.  Also
  ``literal(...) % obj`` will quote any value(s) from ``obj``.  If
  you do something like ``literal(...) + literal(...)``, neither
  string will be changed because ``escape(literal(...))`` doesn't
  change the original literal.
  
  Changed in WebHelpers 1.2: the implementation is now now a subclass of
  ``markupsafe.Markup``.  This brings some new methods: ``.escape`` (class
  method), ``.unescape``, and ``.striptags``.
  
  


**render** (*template_name, data=None*)
  Main template render function.


**render_snippet** (*template_name, data=None*)
  helper for the render_snippet function
  similar to the render function.


**render_text** (*template_name, data=None*)
  Render genshi text template.


**requires_ckan_version** (*min_version, max_version=None*)
  Check that the ckan version is correct for the plugin.

