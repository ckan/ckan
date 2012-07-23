/* An auto-complete module for select and input elements that can pull in
 * a list of terms from an API endpoint (provided using data-module-source).
 *
 * source   - A url pointing to an API autocomplete endpoint.
 * interval - The interval between requests in milliseconds (default: 1000).
 * items    - The max number of items to display (default: 10)
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
      this.el.select2({
        tags: this._onQuery, /* this needs to be "query" for non tags */
        formatResult: this.formatResult,
        formatNoMatches: this.formatNoMatches,
        formatInputTooShort: this.formatInputTooShort
      });
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

    /* Callback triggered when the select2 plugin needs to make a request.
     *
     * Returns nothing.
     */
    _onQuery: function (options) {
      this.lookup(options.term, options.callback);
    }
  };
});
