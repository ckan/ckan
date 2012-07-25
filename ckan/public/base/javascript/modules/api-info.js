/* Loads the API Info snippet into a modal dialog. Retrieves the snippet
 * url from the href on the module element.
 *
 * Examples
 *
 *   <a href="http://example.com/path/to/template" data-module="api-info">API</a>
 *
 */
this.ckan.module('api-info', function (jQuery, _) {
  return {
    options: {
      template: null
    },
    initialize: function () {
      jQuery.proxyAll(this, /_on/);

      this.el.on('click', this._onClick);
      this.el.button();

      this.options.template = this.options.template || this.el.attr('href');
    },
    loading: function (loading) {
      this.el.button(loading !== false ? 'loading' : 'reset');
    },
    show: function () {
      var sandbox = this.sandbox,
          module = this;

      if (this.modal) {
        return this.modal.modal('show');
      }

      this.loadTemplate().done(function (html) {
        module.modal = jQuery(html);
        module.modal.find('.modal-header :header').append('<button class="close" data-dismiss="modal">×</button>');
        module.modal.modal().appendTo(sandbox.body);
      });
    },
    hide: function () {
      if (this.modal) {
        this.modal.modal('hide');
      }
    },
    loadTemplate: function () {
      if (!this.promise) {
        this.loading();

        // This should use sandbox.client!
        this.promise = jQuery.get(this.options.template);
        this.promise.then(this._onTemplateSuccess, this._onTemplateError);
      }
      return this.promise;
    },
    _onClick: function (event) {
      event.preventDefault();
      this.show();
    },
    _onTemplateSuccess: function () {
      this.loading(false);
    },
    _onTemplateError: function () {
      this.loading(false);
      this.sandbox.notify(_('Failed to load data API information').fetch());
    }
  };
});
