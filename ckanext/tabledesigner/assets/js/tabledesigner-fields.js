this.ckan.module('tabledesigner-fields', function($, _) {
  return {
    initialize: function() {
      var $this = $(this.el);
      var $templates = $this.children('div[name="tabledesigner-template"]');
      var templates = Object.fromEntries(
        $templates.toArray().map( x => [x.dataset.tdtype, x.outerHTML])
      );
      var $add = $this.find('a[name="tabledesigner-add"]');
      $templates.remove();

      $add.on('click', function(e) {
        var $last = $this.find('.tabledesigner-field').last();
        var group = ($last.data('index') + 1) || 1;
        var $copy = $(templates[e.target.dataset.tdtype]
          .replace(/TABLEDESIGNER-INDEX/g, group));
        $this.find('.tabledesigner-fields-group').append($copy);
        $copy.hide().show(100);
        $copy.find('input').first().focus();
        e.preventDefault();
      });

      $(document).on('click', 'a[name="tabledesigner-remove"]', function(e) {
        var $curr = $(this).closest('.tabledesigner-field');
        var $body = $curr.find('.field-content');
        var $button = $curr.find('.btn-tabledesigner-remove');
        var $removed = $curr.find('.field-removed-notice');
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
