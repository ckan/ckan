/* Module for reordering resources
 */
this.ckan.module('resource-reorder', function($, _) {
  return {
    options: {
      id: false,
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
    cache: false,

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

      this.cache = this.el.html();

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
        this.reset();
        this.is_reordering = false;
        this.el.html(this.cache)
          .sortable()
          .sortable('disable');
        this.html_handles = $('.handle', this.el);
      }
    },

    _onHandleSave: function() {
      var order = [];
      $('.resource-item', this.el).each(function() {
        order.push($(this).data('id'));
      });
      this.sandbox.client.call('POST', 'package_resource_reorder', {
        id: this.options.id,
        order: order
      });
      this.cache = this.el.html();
      this.reset();
      this.is_reordering = false;
    },

    reset: function() {
      this.html_form_actions
        .add(this.html_handles)
        .add(this.html_title)
        .hide();
      this.el
        .removeClass('reordering')
        .sortable('disable');
      $('.page_primary_action').show();
    }

  };
});
