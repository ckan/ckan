this.ckan.module('confirm-action', function (jQuery) {
  return {
    options: {
      /* Content can be overriden by setting data-module-content to a
       * *translated* string inside the template, e.g.
       *
       *     <a href="..."
       *        data-module="confirm-action"
       *        data-module-content="{{ _('Are you sure?') }}">
       *    {{ _('Delete') }}
       *    </a>
       */
      content: '',

      /* By default confirm-action creates a new form and submit it
       * But you can use closest to el form by setting data-module-with-data=true
       *
       *     <a href="..."
       *        data-module="confirm-action"
       *        data-module-with-data=true>
       *     {{ _('Save') }}
       *     </a>
       */
      withData: '',

      /* This is part of the old i18n system and is kept for backwards-
       * compatibility for templates which set the content via the
       * `i18n.content` attribute instead of via the `content` attribute
       * as described above.
       */
      i18n: {
        content: '',
      },
      confirmText: null,
      cancelText: null,
      title: null,
      type: null,
    },
    initialize: function () {
      jQuery.proxyAll(this, /_on/);
      this.el.on('click', this._onClick);
    },

    _onClick: function (event) {
      event.preventDefault();

      const message =
        this.options.content ||
        this.options.i18n.content ||
        this._('Are you sure you want to perform this action?');

      // Presents the user with a confirm dialogue
      ckan.confirm({
        message: message,
        title: this.options.title,
        confirmText: this.options.confirmText,
        cancelText: this.options.cancelText,
        onConfirm: () => {
          this.performAction();
        },
      });
    },

    performAction: function () {
      var form = this.el.closest('form');

      if (form.attr('hx-post') || form.attr('hx-get')) {
        return htmx.trigger(form[0], 'submit');
      }

      if (!this.options.withData && !form.attr('hx-post')) {
        // create a form and submit it to confirm the deletion
        form = jQuery('<form/>', {
          action: this.el.attr('href'),
          method: 'POST',
        });
      }

      this._appendCSRFInputToForm(form);

      form.appendTo('body').submit();
    },

    /**
     * Creates a hidden input with the CSRF token and appends it to the form.
     *
     * @param {HTMLElement} form
     */
    _appendCSRFInputToForm: function (form) {
      var csrf_field = $('meta[name=csrf_field_name]').attr('content');
      var csrf_value = $('meta[name=' + csrf_field + ']').attr('content');

      var hidden_csrf_input = $(
        `<input name="${csrf_field}" type="hidden" value="${csrf_value}">`
      );

      hidden_csrf_input.prependTo(form);
    },
  };
});
