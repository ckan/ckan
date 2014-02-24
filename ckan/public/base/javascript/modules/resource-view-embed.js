this.ckan.module('resource-view-embed', function (jQuery, _) {
  var element;

  function initialize() {
    var self = this,
        template = self.options.template,
        i18n = function (key) {
          // We can't use i18n directly because it uses "this".
          return self.i18n.call(self, key);
        },
        embedUrl = self.options.embedUrl;

    _createModal(template, i18n, embedUrl);
    self.el.find('a').on('click', _onClick);
  }

  function _createModal(template, i18n, embedUrl) {
    if (!element) {
      element = jQuery(template);
      element.on('click', '.btn-cancel', _onClose);
      element.modal({show: false});
      element.css({
        'margin-top': element.height() * -0.5,
        'top': '50%'
      });

      element.find('h3').text(i18n('heading'));
      element.find('.modal-content').text(i18n('content'));
      element.find('textarea').text(_iframeMarkup(embedUrl));
    }
    return element;
  }

  function _onClick(evt) {
    evt.preventDefault();
    element.modal('show');
  }

  function _onClose() {
    element.modal('hide');
  }

  function _iframeMarkup(url) {
    var markup = '<iframe src="' + url + '"></iframe>';
    return markup;
  }

  return {
    initialize: initialize,
    options: {
      i18n: {
        heading: _('Embed resource view'),
        content: _('To embed this view, copy and paste the following code as HTML into your page:')
      },
      template: [
          '<div class="modal resource-view-embed">',
          '<div class="modal-header">',
          '<button type="button" class="close" data-dismiss="modal">×</button>',
          '<h3></h3>',
          '</div>',
          '<div class="modal-body">',
          '<p class="modal-content"></p>',
          '<textarea></textarea>',
          '</div>',
          '</div>'
      ].join('\n')
    }
  }
});
