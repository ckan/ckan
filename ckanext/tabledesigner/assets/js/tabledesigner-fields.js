this.ckan.module('tabledesigner-fields', function($, _) {
  return {
    initialize: function() {
      var container = this;
      var $this = $(this.el);
      var $template = $this.children('div[name="tabledesigner-template"]');
      var template = $template.html();
      var $add = $this.find('a[name="tabledesigner-add"]');
      $template.remove();

      $add.on('click', function(e) {
        var $last = $this.find('.tabledesigner-fields').last();
        var group = ($last.data('index') + 1) || 0;
        var $copy = $(
          template.replace(/TABLEDESIGNER-INDEX0/g, group)
          .replace(/TABLEDESIGNER-INDEX1/g, group + 1));
        $this.find('.tabledesigner-fields-group').append($copy);
        $copy.hide().show(100);
        $copy.find('input').first().focus();
        e.preventDefault();
      });

      $(document).on('click', 'a[name="tabledesigner-remove"]', function(e) {
        var $curr = $(this).closest('.tabledesigner-fields-group');
        var $body = $curr.find('.fields-content');
        var $button = $curr.find('.btn-tabledesigner-remove');
        var $removed = $curr.find('.fields-removed-notice');
        $button.hide();
        $removed.show(100);
        $body.hide(100, function() {
          $body.html('');
        });
        e.preventDefault();
      });
    }
  }
});
