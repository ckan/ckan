/* An auto-complete module for select and input elements that can pull in
 * a list of terms from an API endpoint (provided using data-module-source).
 *
 * source   - A url pointing to an API autocomplete endpoint.
 * interval - The interval between requests in milliseconds (default: 300).
 * tags     - Boolean attribute if true will create a tag input.
 * createtags - Boolean attribute if false will not allow creating new tags
 * key      - A string of the key you want to be the form value to end up on
 *            from the ajax returned results
 * label    - A string of the label you want to appear within the dropdown for
 *            returned results
 * tokensep - A string that contains characters which will be interpreted
 *            as separators for tags when typed or pasted (default ",").
 * Examples
 *
 *   // <input name="tags" data-module="autocomplete" data-module-source="http://" />
 *
 */
this.ckan.module('autocomplete', function (jQuery) {
  return {
    /* Options for the module */
    options: {
      tags: false,
      createtags: true,
      key: false,
      label: false,
      source: null,
      tokensep: ',',
      interval: 300,
      dropdownClass: '',
      containerClass: '',
      minimumInputLength: 0
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
        width: 'resolve',
        templateResult: this.templateResult,
        language: {
          noResults: this.formatNoMatches,
          inputTooShort: this.formatInputTooShort,
          searching: this.formatSearching,
        },
        dropdownCssClass: this.options.dropdownClass,
        tokenSeparators: this.options.tokensep.split(''),
        minimumInputLength: this.options.minimumInputLength,
        selectionCssClass: this.options.containerClass
      };

      // Different keys are required depending on whether the select is
      // tags or generic completion.
      if (!this.el.is('select')) {

        settings.dataAdapter = this.dataAdapter();
        if ( this.options.tags ){
          var Utils = $.fn.select2.amd.require('select2/utils');
          var Tags = $.fn.select2.amd.require('select2/data/tags');
          settings.dataAdapter = Utils.Decorate(settings.dataAdapter, Tags)
          settings.multiple = "multiple"

          // tokenizer is not applied when custom data adapter is used
          if (settings.tokenSeparators != null) {
            var Tokenizer = $.fn.select2.amd.require('select2/data/tokenizer');
            settings.dataAdapter = Utils.Decorate(settings.dataAdapter, Tokenizer);
          }
        }

        // minimum input length is not applied when custom data adapter is used
        if (this.options.minimumInputLength > 0) {
          var Utils = $.fn.select2.amd.require('select2/utils');
          var MinimumInputLength = $.fn.select2.amd.require('select2/data/minimumInputLength');
          settings.dataAdapter = Utils.Decorate(settings.dataAdapter, MinimumInputLength)
        }

        // Disable creating new tags
        if (!this.options.createtags) {
          settings.createTag = function (params) {
            return undefined;
          }
        }
        else{
            settings.createTag = this.formatTerm;
        }
      }
      else {
        if (/MSIE (\d+\.\d+);/.test(navigator.userAgent)) {
            var ieversion=new Number(RegExp.$1);
            if (ieversion<=7) {return}
         }
      }

      // Add placeholder to select2 component if its given on the element
      if ( this.el.attr('placeholder') ) {
        settings.placeholder = this.el.attr('placeholder');
      }

      // clean up rendered select2 from htmx back/forward navigation
      this.el.removeClass('select2-hidden-accessible')
      this.el.removeAttr('data-select2-id')
      this.el.next('span.select2-container').remove()
      this.el.find('option').removeAttr('data-select2-id')

      var select2 = this.el.select2(settings).data('select2');

      if (this.options.tags && select2 && select2.search) {
        // find the "fake" input created by select2 and add the keypress event.
        // This is not part of the plugins API and so may break at any time.
        select2.search.on('keydown', this._onKeydown);
      }

      // This prevents Internet Explorer from causing a window.onbeforeunload
      // even from firing unnecessarily
      $('.select2-choice', select2.container).on('click', function() {
        return false;
      });

      this._select2 = select2;
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
      var options = {
        format: function(data) {
          var completion_options = jQuery.extend(options, {objects: true});
          return {
            results: client.parseCompletions(data, completion_options)
          }
        },
        key: this.options.key,
        label: this.options.label
      };

      return client.getCompletions(source, options, fn);
    },

    /* Looks up the completions for the provided text but also provides a few
     * optimisations. If there is no search term it will automatically set
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

      // Kills previous timeout
      clearTimeout(this._debounced);

      if (!string) {
        // Wipe the dropdown for empty calls.
        fn({results:[]});
      } else {
        // Set a timer to prevent the search lookup occurring too often.
        this._debounced = setTimeout(function () {
          var term = module._lastTerm;

          // Cancel the previous request if it hasn't yet completed.
          if (module._last && typeof module._last.abort == 'function') {
            module._last.abort();
          }

          module._last = module.getCompletions(term, fn);
        }, this.options.interval);

        // This forces the ajax throbber to appear, because we've called the
        // callback already and that hides the throbber
        $('.select2-search input', this._select2.dropdown).addClass('select2-active');
      }
    },

    /* Formatter for the select2 plugin that returns a string for use in the
     * results list with the current term emboldened.
     *
     * state     - The current object that is being rendered.
     * container - The element the content will be added to (added in 3.0)
     *
     *
     * Returns a text string or a jquery object.
     */
    templateResult: function (state, container) {
      var term = this._lastTerm || null;

      if (state.loading) {
        return state.text
      }

      var Utils = $.fn.select2.amd.require('select2/utils');

      if (container && state.id) {
        // Append the select id to the element for styling.
        $(container).attr('data-value', state.id);
      }

      var result = [];
      $(state.text.split(term)).each(function() {
        result.push(Utils.escapeMarkup(this));
      });

      return $("<span>" + result.join(term && Utils.escapeMarkup(term).bold()) + "</span>");
    },

    /* Formatter for the select2 plugin that returns a string used when
     * the filter has no matches.
     *
     * Returns a text string.
     */
    formatNoMatches: function () {
      // hack to detect if we are searching something for autocomplete api
      if ( this.options.source ) {
        var term = this._lastTerm || null;
        return !term ? this._('Start typing…') : this._('No matches found');
      }
      else {
        return this._('No matches found')
      }
    },

    /* Formatter used by the select2 plugin that returns a string when the
     * input is too short.
     *
     * Returns a string.
     */
    formatInputTooShort: function (term, min) {
      return this.ngettext(
        'Input is too short, must be at least one character',
        'Input is too short, must be at least %(num)d characters',
        min
      );
    },

    /* Formatter used by the select2 plugin that returns a string when
     * XHR is being performed.
     *
     * Returns a string.
     */
    formatSearching: function () {
      return this._('Searching...');
    },

    formatTerm: function (term) {
      if (typeof term === 'object') {
        term = term.term;
      }
      term = jQuery.trim(term || '');

      // Don't create tag from empty terms
      if (term === '') {
        return
      }

      // Need to replace comma with a unicode character to trick the plugin
      // as it won't split this into multiple items.
      return {id: term.replace(/,/g, '\u002C'), text: term};
    },

    /* Callback function that parses the initial field value.
     *
     * element  - The initialized input element wrapped in jQuery.
     * callback - A callback to run once the formatting is complete.
     *
     * Returns a term object or an array depending on the type.
     */
    formatInitialValue: function (element, callback) {
      var value = jQuery.trim(element.val() || '');
      var formatted;

      if (this.options.tags) {
        formatted = jQuery.map(value.split(","), this.formatTerm);
      } else {
        formatted = this.formatTerm(value);
      }

      // Select2 v3.0 supports a callback for async calls.
      if (typeof callback === 'function') {
        callback(formatted);
      }

      return formatted;
    },

    /* Callback triggered when the select2 plugin needs to make a request.
     *
     * Returns nothing.
     */
    _onQuery: function (options) {
      if (options) {
        this.lookup(options.term, options.callback);
      }
    },

    /* Called when a key is pressed.  If the key is a comma we block it and
     * then simulate pressing return.
     *
     * Returns nothing.
     */
    _onKeydown: function (event) {
      if (typeof event.key !== 'undefined' ? event.key === ',' : event.which === 188) {
        event.preventDefault();
        setTimeout(function () {
          var e = jQuery.Event("keydown", { which: 13 });
          jQuery(event.target).trigger(e);
        }, 10);
      }
    },

    dataAdapter: function(){
      // Create custom data adapter for Select2 4.0
      // See https://select2.org/upgrading/migrating-from-35#custom-data-adapters-instead-of-query

      var module = this;
      var ArrayData = $.fn.select2.amd.require('select2/data/array');
      var Utils = $.fn.select2.amd.require('select2/utils');

      function CKANDataAdapter ($element, options) {
        CKANDataAdapter.__super__.constructor.call(this, $element, options);
      }

      Utils.Extend(CKANDataAdapter, ArrayData);

      CKANDataAdapter.prototype.query = function (params, callback) {
        module._onQuery({
          term: params.term,
          callback: callback
        });
      };

      CKANDataAdapter.prototype.current = function (callback) {
        module.formatInitialValue(this.$element, function(formatted) {
          // Ensure we always return an array for Select2 4.0
          if (formatted && !Array.isArray(formatted)) {
            formatted = [formatted];
          }
          callback(formatted || []);
        });
      };

      return CKANDataAdapter;
    }
  };
});
