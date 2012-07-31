this.ckan.module('confirm-delete', function (jQuery, _) {
  return {
    /* An object of module options */
    options: {
      /* Locale options can be overidden with data-module-i18n attribute */
      i18n: {
        heading: _('Please Confirm Action').fetch(),
        content: _('Are you sure you want to delete this item?').fetch(),
        confirm: _('Confirm').fetch(),
        cancel: _('Cancel').fetch()
      },
      template: [
        '<div class="modal">',
        '<div class="modal-header">',
        '<button type="button" class="close" data-dismiss="modal">×</button>',
        '<h3></h3>',
        '</div>',
        '<div class="modal-body"></div>',
        '<div class="modal-footer">',
        '<button class="btn btn-cancel"></button>',
        '<button class="btn btn-primary"></button>',
        '</div>',
        '</div>'
      ].join('\n')
    },

    /* Sets up the event listeners for the object. Called internally by
     * module.createInstance().
     *
     * Returns nothing.
     */
    initialize: function () {
      jQuery.proxyAll(this, /_on/);
      this.el.on('click', this._onClick);
    },

    /* Presents the user with a confirm dialogue to ensure that they wish to
     * delete the current item.
     *
     * Examples
     *
     *   jQuery('.delete').click(function () {
     *     module.confirm();
     *   });
     *
     * Returns nothing.
     */
    confirm: function () {
      this.sandbox.body.append(this.createModal());
      this.modal.modal('show');
    },

    /* Performs the delete action for the current item.
     *
     * Returns nothing.
     */
    performDelete: function () {
      // create a form and submit it to confirm the deletion
      var form = jQuery('<form/>', {
        action: this.el.attr('href'),
        method: 'POST'
      });
      form.appendTo('body').submit();
    },

    /* Creates the modal dialog, attaches event listeners and localised
     * strings.
     *
     * Returns the newly created element.
     */
    createModal: function () {
      var i18n = this.options.i18n;

      if (!this.modal) {
        var element = this.modal = jQuery(this.options.template);
        element.on('click', '.btn-primary', this._onConfirmSuccess);
        element.on('click', '.btn-cancel', this._onConfirmCancel);
        element.modal({show: false});

        element.find('h3').text(i18n.heading);
        element.find('.modal-body').text(i18n.content);
        element.find('.btn-primary').text(i18n.confirm);
        element.find('.btn-cancel').text(i18n.cancel);
      }
      return this.modal;
    },

    /* Event handler that displays the confirm dialog */
    _onClick: function (event) {
      event.preventDefault();
      this.confirm();
    },

    /* Event handler for the success event */
    _onConfirmSuccess: function (event) {
      this.performDelete();
    },

    /* Event handler for the cancel event */
    _onConfirmCancel: function (event) {
      this.modal.modal('hide');
    }
  };
});
