/* Module that handles related item elements, at the moment this consists of
 * truncating the descriptions and allowing them to be toggled.
 *
 * truncate - The max number of characters in the description element.
 * truncateMore - A locale string for the "more" text.
 * truncateLess - A locale string for the "less" text.
 * truncatePrefix - A prefix for the more/less strings.
 * truncateSuffix - A suffix for the more/less strings.
 * truncateSelector - A selector for the element to truncate.
 * expandedClass - A class to apply to the element when expanded.
 */
this.ckan.module('related-item', function (jQuery, _) {
  return {
    /* options object can be extended using data-module-* attributes */
    options: {
      truncate: 55,
      truncateMore: null,
      truncateLess: null,
      truncatePrefix: '',
      truncateSuffix: '',
      truncateSelector: '.prose',
      expandedClass: 'expanded',
      hasExpanderClass: 'is-expander',
      i18n: {
        more: _('show more'),
        less: _('show less')
      }
    },

    /* Initialises the module setting up elements and event listeners.
     *
     * Returns nothing.
     */
    initialize: function () {
      jQuery.proxyAll(this, /_on/);

      var options = this.options;
      this.description = this.$(options.truncateSelector);
      this.truncated = this.description.truncate({
        max_length: options.truncate,
        more: options.truncateMore || this.i18n('more'),
        less: options.truncateLess || this.i18n('less'),
        link_prefix: options.truncatePrefix,
        link_suffix: options.truncateSuffix
      });

      this.collapsedHeight = this.el.height();
      this.truncated.on('expand.truncate', this._onExpand);
      this.truncated.on('collapse.truncate', this._onCollapse);

      if ($('.truncator-link', this.description).length > 0) {
        this.el.addClass(options.hasExpanderClass);
      }

    },

    /* Event handler called when the truncated text expands.
     *
     * event - An event object.
     *
     * Returns nothing.
     */
    _onExpand: function () {
      var diff = this.el.height() - this.collapsedHeight;
      this.el.addClass(this.options.expandedClass);
      this.el.css('margin-bottom', diff * -1);
    },

    /* Event handler called when the truncated text is collapsed.
     *
     * event - An event object.
     *
     * Returns nothing.
     */
    _onCollapse: function () {
      this.el.removeClass(this.options.expandedClass);
      this.el.css('margin-bottom', '');
    }
  };
});
