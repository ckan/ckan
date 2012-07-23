/* An auto-complete module for select and input elements that can pull in
 * a list of terms from an API endpoint (provided using data-module-source).
 *
 * source   - A url pointing to an API autocomplete endpoint.
 * interval - The interval between requests in milliseconds (default: 1000).
 * items    - The max number of items to display (default: 10)
 * tags     - Boolean attribute if true will create a tag input.
 *
 * Examples
 *
 *   // <input name="tags" data-module="autocomplete" data-module-source="http://" />
 *
 */
this.ckan.module('autocomplete', function (jQuery, _) {
  return {
    /* Options for the module */
    options: {
      tags: false,
      items: 10,
      source: null,
      interval: 1000,
      i18n: {
        noMatches: _('No matches found'),
        emptySearch: _('Start typing…'),
        inputTooShort: function (n) {
          return _('Input is too short, must be at least one character')
          .ifPlural(n, 'Input is too short, must be at least %d characters');
        }
      }
    },

    /* Sets up the module, binding methods, creating elements etc. Called
     * internally by ckan.module.initialize();
     *
     * Returns nothing.
     */
    initialize: function () {
      jQuery.proxyAll(this, /_on/, /format/);
      this.setupAutoComplete();
    },

    /* Sets up the auto complete plugin.
     *
     * Returns nothing.
     */
    setupAutoComplete: function () {
      var settings = {
        formatResult: this.formatResult,
        formatNoMatches: this.formatNoMatches,
        formatInputTooShort: this.formatInputTooShort,
        createSearchChoice: this.formatTerm, // Not used by tags.
        initSelection: this.formatInitialValue
      };

      // Different keys are required depending on whether the select is
      // tags or generic completion.
      if (this.options.tags) {
        settings.tags = this._onQuery;

        // Also need to watch for changes so we can handle formatting
        // inconsistencies that occur when dealing with tags.
        this.el.on('change', this._onChange);
      } else {
        settings.query = this._onQuery;
      }

      this.el.select2(settings);
    },

    /* Looks up the completions for the current search term and passes them
     * into the provided callback function.
     *
     * The results are formatted for use in the select2 autocomplete plugin.
     *
     * string - The term to search for.
     * fn     - A callback function.
     *
     * Examples
     *
     *   module.getCompletions('cake', function (results) {
     *     results === {results: []}
     *   });
     *
     * Returns a jqXHR promise.
     */
    getCompletions: function (string, fn) {
      var parts  = this.options.source.split('?');
      var end    = parts.pop();
      var source = parts.join('?') + encodeURIComponent(string) + end;
      var client = this.sandbox.client;
      var options = {format: client.parseCompletionsForPlugin};

      return client.getCompletions(source, options, fn);
    },

    /* Looks up the completions for the provided text but also provides a few
     * optimisations. It there is no search term it will automatically set
     * an empty array. Ajax requests will also be debounced to ensure that
     * the server is not overloaded.
     *
     * string - The term to search for.
     * fn     - A callback function.
     *
     * Returns nothing.
     */
    lookup: function (string, fn) {
      var module = this;

      // Cache the last searched term otherwise we'll end up searching for
      // old data.
      this._lastTerm = string;

      if (string) {
        if (!this._debounced) {
          // Set a timer to prevent the search lookup occurring too often.
          this._debounced = setTimeout(function () {
            delete module._debounced;

            // Cancel the previous request if it hasn't yet completed.
            if (module._last) {
              module._last.abort();
            }

            module._last = module.getCompletions(module._lastTerm, fn);
          }, this.options.interval);
        }
      } else {
        fn({results: []});
      }
    },

    /* Formatter for the select2 plugin that returns a string for use in the
     * results list with the current term emboldened.
     *
     * Returns a text string.
     */
    formatResult: function (state) {
      var term = this._lastTerm || null;
      return state.text.split(term).join(term && term.bold());
    },

    /* Formatter for the select2 plugin that returns a string used when
     * the filter has no matches.
     *
     * Returns a text string.
     */
    formatNoMatches: function (term) {
      return !term ? this.i18n('emptySearch') : this.i18n('noMatches');
    },

    /* Formatter used by the select2 plugin that returns a string when the
     * input is too short.
     *
     * Returns a string.
     */
    formatInputTooShort: function (term, min) {
      return this.i18n('inputTooShort', min);
    },

    /* Takes a string and converts it into an object used by the select2 plugin.
     *
     * term - The term to convert.
     *
     * Returns an object for use in select2.
     */
    formatTerm: function (term) {
      term = jQuery.trim(term || '');

      // Need to replace comma with a unicode character to trick the plugin
      // as it won't split this into multiple items.
      return {id: term.replace(/,/g, '\u002C'), text: term};
    },

    /* Callback function that parses the initial field value.
     *
     * element - The initialized input element wrapped in jQuery.
     *
     * Returns a term object or an array depending on the type.
     */
    formatInitialValue: function (element) {
      var value = jQuery.trim(element.val() || '');

      if (this.options.tags) {
        return jQuery.map(value.split(","), this.formatTerm);
      } else {
        return this.formatTerm(value);
      }
    },

    /* Callback triggered when the select2 plugin needs to make a request.
     *
     * Returns nothing.
     */
    _onQuery: function (options) {
      this.lookup(options.term, options.callback);
    },

    /* Called when the input changes. Used to split any comma separated tags
     * into individual items. This is a bit of a workaround as select2 doesn't
     * handle this yet.
     *
     * select2('val') actually parses comma separated input correctly but
     * doesn't render them. So we give it a gentle nudge.
     *
     * Returns nothing.
     */
    _onChange: function (event) {
      var parsed = jQuery.map(this.el.select2('val'), this.formatTerm);

      this.el.select2('val', parsed);
    }
  };
});
