/* Module for the resource form. Handles validation and updating the form
 * with external data such as from a file upload.
 */
this.ckan.module('resource-reorder', function($, _) {
  return {
    options: {
      form: {
        method: 'POST',
        file: 'file',
        params: []
      },
      i18n: {
        label: _('Reorder resources'),
        save: _('Save order'),
        cancel: _('Cancel')
      }
    },
    template: {
      title: '<h1></h1>',
      button: [
        '<a href="javascript:;" class="btn">',
        '<i class="icon-reorder"></i>',
        '<span></span>',
        '</a>'
      ].join('\n'),
      form_actions: [
        '<div class="form-actions">',
        '<a href="javascript:;" class="cancel btn pull-left"></a>',
        '<a href="javascript:;" class="save btn btn-primary"></a>',
        '</div>'
      ].join('\n'),
      handle: [
        '<a href="javascript:;" class="handle">',
        '<i class="icon-move"></i>',
        '</a>'
      ].join('\n')
    },
    is_reordering: false,

    initialize: function() {
      jQuery.proxyAll(this, /_on/);

      this.html_title = $(this.template.title)
        .text(this.i18n('label'))
        .insertBefore(this.el)
        .hide();
      var button = $(this.template.button)
        .on('click', this._onHandleStartReorder)
        .appendTo('.page_primary_action');
      $('span', button).text(this.i18n('label'));

      this.html_form_actions = $(this.template.form_actions)
        .hide()
        .insertAfter(this.el);
      $('.save', this.html_form_actions)
        .text(this.i18n('save'))
        .on('click', this._onHandleSave);
      $('.cancel', this.html_form_actions)
        .text(this.i18n('cancel'))
        .on('click', this._onHandleCancel);

      this.html_handles = $(this.template.handle)
        .hide()
        .appendTo($('.resource-item', this.el));

      this.el
        .sortable()
        .sortable('disable');

    },

    _onHandleStartReorder: function() {
      if (!this.is_reordering) {
        this.html_form_actions
          .add(this.html_handles)
          .add(this.html_title)
          .show();
        this.el
          .addClass('reordering')
          .sortable('enable');
        $('.page_primary_action').hide();
        this.is_reordering = true;
      }
    },

    _onHandleCancel: function() {
      if (this.is_reordering) {
        this.html_form_actions
          .add(this.html_handles)
          .add(this.html_title)
          .hide();
        this.el
          .removeClass('reordering')
          .sortable('disable');
        $('.page_primary_action').show();
        this.is_reordering = false;
      }
    },

    _onHandleSave: function() {
      if (!$('.save', this.html_form_actions).hasClass('disabled')) {
        var order = [];
        $('.resource-item', this.el).each(function() {
          order.push($(this).data('id'));
        });
        console.log(order);
      }
    }

  };
});
