this.ckan.module('basic-form', function (jQuery) {
  return {
    initialize: function () {
      var message = this._('There are unsaved modifications to this form');
      this.el.incompleteFormWarning(message);
      // Internet Explorer 7 fix for forms with <button type="submit">
      if ($('html').hasClass('ie7')) {
        this.el.on('submit', function() {
          var form = $(this);
          $('button', form).each(function() {
            var button = $(this);
            $('<input type="hidden">').prop('name', button.prop('name')).prop('value', button.val()).appendTo(form);
          });
        });
      }
    }
  };
});
