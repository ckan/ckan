(function ($, window) {
  var escape = $.url.escape;

  function slugPreview(options) {
    options = $.extend(true, slugPreview.defaults, options || {});

    var collected = this.map(function () {
      var element = $(this);
      var field = element.find('input');
      var preview = $(options.template);
      var value = preview.find('.slug-preview-value');

      function setValue() {
        var val = escape(field.val()) || options.placeholder;
        value.text(val);
      }

      preview.find('.slug-preview-prefix').text(options.prefix);
      preview.find('button').text(options.trans.edit).click(function (event) {
        event.preventDefault();
        element.show();
        preview.hide();
      });

      setValue();
      field.on('change', setValue);

      element.after(preview).hide();

      return preview[0];
    });

    return this.pushStack(collected);
  }

  slugPreview.defaults = {
    prefix: '',
    placeholder: '',
    trans: {
      edit: 'Edit'
    },
    template: [
      '<div class="slug-preview">',
      '<strong>URL:</strong>',
      '<span class="slug-preview-prefix"></span><span class="slug-preview-value"></span>',
      '<button class="btn btn-small"></button>',
      '</div>'
    ].join('\n')
  };

  $.fn.slugPreview = slugPreview;

})(this.jQuery, this);
