
Plugins Toolkit
===============

To allow a safe way for extensions to interact with ckan a toolkit is
provided. We aim to keep this toolkit stable across ckan versions so
that extensions will work across different versions of ckan.

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

*class* **BAseController**
  Base class for building controllers.


*class* **CkanCommand**
  Base class for building paster functions.


*class* **DefaultDatasetForm**
  base class for IDatasetForm.


*exception* **CkanVersionException**
  Exception raised if required ckan version is not available.


*exception* **NotAuthorized**
  Exception raised when an action is not permitted by a user.


*exception* **ObjectNotFound**
  Exception raised when an object cannot be found.


*exception* **ValidationError**
  Exception raised when supplied data is invalid.
  it contains details of the error that occurred.


*exception* **UnknownConverter**
  Exception raised when a converter cannot be found.


*exception* **UnknownValidator**
  Exception raised when a validator cannot be found.


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


**get_converter** (*coverter*)
  Get the requested converter function.


**get_validator** (*validator*)
  Get the requested validator function.


**literal** (*html*)
  Treat the html as a literal that will not get escaped.


**render** (*template_name, data=None*)
  Main template render function.


**render_snippet** (*template_name, data=None*)
  helper for the render_snippet function
  similar to the render function.


**render_text** (*template_name, data=None*)
  Render genshi text template.


**requires_ckan_version** (*min_version, max_version=None*)
  Check that the ckan version is correct for the plugin.


**request** object
  This is the http request and contains the environ, cookies etc.


**response** object
  This is the http response.


**abort** (*error_code, error_message*)
  Aborts the current request.


**redirect**
  This causes a http redirect to be returned to the client.


**url_for**
  This function can be used to create urls.


**side_effect_free** decorator
  This marks action functions as accessible via the action api.


**auth_sysadmins_check** decorator
  This marks auth functions as needing to be run for sys admins.  Usually
  sysadmins are automatically allowed to run actions etc.


**get_or_bust** (*data_dict, keys*)
    Try and get values from dictionary and if they are not there
    raise a ValidationError.
