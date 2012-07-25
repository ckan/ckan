/* Loads the API Info snippet into a modal dialog. Retrieves the snippet
 * url from the data-snippet-url on the module element.
 *
 * template - The url to the template to display in a modal.
 *
 * Examples
 *
 *   <a data-module="api-info" data-module-template="http://example.com/path/to/template">API</a>
 *
 */
this.ckan.module('api-info', function (jQuery, _) {
  return {
    options: {
      template: null,
      i18n: {
        noTemplate: _('There is no API data to load for this resource').fetch(),
        loadError: _('Failed to load data API information').fetch()
      }
    },
    initialize: function () {
      jQuery.proxyAll(this, /_on/);

      this.el.on('click', this._onClick);
      this.el.button();
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
      if (!this.options.template) {
        this.sandbox.notify(this.options.i18n.noTemplate);
        return jQuery.Deferred().reject().promise();
      }

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
      this.sandbox.notify(this.options.i18n.loadError);
    }
  };
});
