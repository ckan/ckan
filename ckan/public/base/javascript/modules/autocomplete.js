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
          .ifPlural(n, 'Input is too short, must be at least one character');
        }
      }
    },
    initialize: function () {
      jQuery.proxyAll(this, /_on/, /format/);

      // Need to keep a reference to this source so we can change the contents.
      this.source = jQuery.isArray(this.options.source) ? this.options.source : [];

      this.el.select2({
        tags: this._onQuery,
        formatNoMatches: this.formatNoMatches,
        formatInputTooShort: this.formatInputTooShort
      });
    },
    getCompletions: function (string, fn) {
      var parts  = this.options.source.split('?');
      var end    = parts.pop();
      var source = parts.join('?') + string + end;
      var module = this;

      jQuery.getJSON(source, function (data) {
        var map = {};
        var items = jQuery.map(data.ResultSet.Result, function (item) {
          item = typeof item === 'string' ? item : item.Name || '';

          var lowercased = item.toLowerCase();

          if (lowercased && !map[lowercased]) {
            map[lowercased] = 1;
            return item;
          }

          return null;
        });

        items = jQuery.grep(items, function (item) { return item !== null; });

        fn({results: module.createItems(items)});
      });
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
    createItem: function (item) {
      return {id: item, text: item};
    },
    createItems: function (items) {
      return jQuery.map(items, this.createItem);
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
