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

      element.find('h3').text(i18n('heading'));
      element.find('.embed-content').prepend(i18n('content'));
      element.find('.embed-width-label').prepend(i18n('width'));
      element.find('.embed-height-label').prepend(i18n('height'));

      var widthInput = element.find('#embed-width'),
          heightInput = element.find('#embed-height'),
          onBlur = _updateEmbedCode(embedUrl, widthInput, heightInput);

      element.on('blur', 'input', onBlur);
      onBlur();
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

  function _updateEmbedCode(url, widthInput, heightInput) {
    return function () {
      var width = widthInput.val(),
          height = heightInput.val();

      element.find('textarea').text(_embedCode(url, width, height));
    };
  }

  function _embedCode(url, width, height) {
    var markup = '<iframe width="' + width +
                 '" height="' + height +
                 '" src="' + url +
                 '" frameBorder="0"></iframe>';
    return markup;
  }

  return {
    initialize: initialize,
    options: {
      i18n: {
        heading: _('Embed resource view'),
        content: _('You can copy and paste the embed code into a CMS or blog software that supports raw HTML'),
        width: _('Width'),
        height: _('Height')
      },
      template: [
          '<div class="modal resource-view-embed">',
          '<div class="modal-header">',
          '<button type="button" class="close" data-dismiss="modal">×</button>',
          '<h3></h3>',
          '</div>',
          '<div class="modal-body">',
          '<p class="embed-content"></p>',
          '<div class="span3">',
          '<label for="embed-width" class="embed-width-label"></label>',
          '<input id="embed-width" value="700">',
          '<label for="embed-height" class="embed-height-label"></label>',
          '<input id="embed-height" value="400">',
          '</div>',
          '<div class="span3">',
          '<textarea></textarea>',
          '</div>',
          '</div>',
          '</div>'
      ].join('\n')
    }
  }
});
