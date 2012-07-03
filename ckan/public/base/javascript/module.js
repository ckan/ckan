this.ckan = this.ckan || {};

/* The module system ties JavaScript code to elements on the page. A module is
 * simply a function that recieves an element and a sandboxed module object.
 *
 * The sandbox provides useful methods for querying within the module element
 * as well as making ajax calls and talking to other modules. The idea being to
 * isolate a single component from the rest of the page keeping the codebase
 * very modular and reusable.
 *
 * Modules are initialized through the DOM keeping boilerplate setup code to a
 * minimum. If an element in the page has a "data-module" attribute then an
 * instance of that module (if registered) will be created when the page loads
 * and will recieve the element and the sandbox mentioned above.
 *
 * Examples
 *
 *   // For element: <select data-module="language-picker"></select>
 *
 *   // Function recieves the sandbox, options and translate() arguments.
 *   ckan.module('language-picker', function (sb, options, _) {
 *     // .el is the dom node the element was created with.
 *     sb.el.on('change', function () {
 *
 *       // Publish the new language so other modules can update.
 *       sb.publish('lang', this.selected);
 *
 *       // Display a localized notification to the user.
 *       // NOTE: _ is an alias for sb.translate()
 *       sb.alert(_('Language changed to: ' + this.selected).fetch());
 *     });
 *
 *     // listen for other updates to lang.
 *     sb.subscribe('lang', function (lang) {
 *       // Update the element select box.
 *       sb.el.select(lang);
 *     });
 *   });
 */
(function (ckan, $, window) {
  // Prefixes for the HTML attributes use to pass options into the modules.
  var MODULE_PREFIX = 'data-module';
  var MODULE_OPTION_PREFIX = 'data-module-';

  /* Add a new module to the registry.
   *
   * name     - A unique name for the module to be registered.
   * factory  - This function will be called when the module is initialized.
   * defaults - An object of default options for the module.
   *
   * Examples
   *
   *   ckan.module('like-button', function (mod, options, _) {
   *     mod.element.on('click', function () {
   *       var url = options.endpoint;
   *       var message = _('Dataset was liked!').fetch();
   *       mod.ajax( ... );
   *     });
   *   }, {
   *     endpoint: '/api/v2/like'
   *   });
   *
   * Returns the module object.
   */
  function module(name, factory, defaults) {
    if (module.registry[name]) {
      throw new Error('There is already a module registered as "' + name  + '"');
    }

    // Store the default options on the function and add to registry.
    factory.defaults = defaults || {};
    module.registry[name] = factory;

    return module;
  }

  /* Holds all of the registered module functions */
  module.registry = {};

  /* Searches the document for modules and initializes them. This should only
   * be called once on page load.
   *
   * Examples
   *
   *   jQuery.ready(ckan.module.initialize);
   *
   * Returns the module object.
   */
  module.initialize = function () {
    var registry = module.registry;

    $('[data-module]').each(function () {
      var name = this.getAttribute(MODULE_PREFIX);
      var factory = registry[name];

      if (module && typeof module === 'function') {
        module.createModule(factory, this);
      }
    });

    return module;
  };

  /* Creates a new module instance for the element provided.
   *
   * The module factory is called with the sandbox, options object and
   * translate function as arguments. In the same way as a jQuery callback the
   * scope of the factory is set to the element the module is bound to.
   *
   * factory - The module factory function to call.
   * element - The element that created the module.
   *
   * Examples
   *
   *   module.createModule(function (sb, opts, _) {
   *     this  === sb.el[0];     // The div passed in as the second arg.
   *     opts  === sb.opts;      // Any data-module-* options on the div.
   *     _     === sb.translate; // A translation function.
   *   }, document.createElement('div'));
   *
   * Returns nothing.
   */
  module.createModule = function (factory, element) {
    var defaults = $.extend({}, module.defaults);
    var options  = $.extend(defaults, module.extractOptions(element));
    var sandbox  = ckan.sandbox(element, options);

    factory.call(element, sandbox, sandbox.options, ckan.i18n.translate);
  };

  /* Extracts any properties starting with MODULE_OPTION_PREFIX from the
   * element and returns them as an object.
   *
   * Keys with additonal hyphens will be converted to camelCase. Each attribute
   * will be passed to JSON.parse() so that complex object can be provided as
   * options (although this is not recommended).
   *
   * element - The element from which to extract the attributes.
   *
   * Examples
   *
   *   // Source <div data-module-url="http://..." data-module-full-name="fred">
   *
   *   module.extractOptions(div); //=> {url: "http://...", fullName: "fred"}
   *
   * Returns an object of extracted options.
   */
  module.extractOptions = function (element) {
    var attrs = element.attributes;
    var index = 0;
    var length = attrs.length;
    var options = {};
    var prop;
    var attr;
    var value;

    for (; index < length; index += 1) {
      attr = attrs[index];

      if (attr.name.indexOf(MODULE_OPTION_PREFIX) === 0) {
        prop = attr.name.slice(MODULE_OPTION_PREFIX.length);

        // Attempt to parse the string as JSON. If this fails then simply use
        // the attribute value as is.
        try {
          value = $.parseJSON(attr.value);
        } catch (error) {
          if (error instanceof window.SyntaxError) {
            value = attr.value;
          } else {
            throw error;
          }
        }

        options[$.camelCase(prop)] = value;
      }
    }

    return options;
  };

  ckan.module = module;

})(this.ckan, this.jQuery, this);
