this.ckan.module('autocomplete', function (jQuery, _) {
  return {
    source: null,
    options: {
      items: 10,
      source: null,
      i18n: {
        noMatches: _('No matches found'),
        emptySearch: _('Start typing…'),
        inputTooShort: function (n) {
          return _('Input is too short, must be at least one character')
          .ifPlural(n, 'Input is too short, must be at least %d characters');
        }
      }
    },
    initialize: function () {
      jQuery.proxyAll(this, /_on/, /format/);

      // Need to keep a reference to this source so we can change the contents.
      this.source = jQuery.isArray(this.options.source) ? this.options.source : [];

      this.el.select2({
        tags: this._onQuery, /* this needs to be "query" for non tags */
        formatNoMatches: this.formatNoMatches,
        formatInputTooShort: this.formatInputTooShort
      });
    },
    getCompletions: function (string, fn) {
      var parts  = this.options.source.split('?');
      var end    = parts.pop();
      var source = parts.join('?') + string + end;
      var client = this.sandbox.client;
      var options = {format: client.parseCompletionsForPlugin};

      client.getCompletions(source, options, fn);
    },
    lookup: function () {
      var module = this;

      if (!this._debounced) {
        this._debounced = true;
        setTimeout(function () {
          delete module._debounced;
          module.getCompletions(module._onLoadCompletions);
        }, 300);
      } else {
        this.typeahead._lookup();
      }
    },
    formatNoMatches: function (term) {
      return !term ? this.i18n('emptySearch') : this.i18n('noMatches');
    },
    formatInputTooShort: function (term, min) {
      return this.i18n('inputTooShort', min);
    },
    _onQuery: function (options) {
      this.getCompletions(options.term, options.callback);
    },
    _onLoadCompletions: function (items) {
      var args = [0, this.source.length].concat(items);
      this.source.splice.apply(this.source, args);
      this.typeahead._lookup();
    }
  };
});
