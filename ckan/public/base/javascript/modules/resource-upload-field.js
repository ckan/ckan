this.ckan.module('resource-upload-field', function (jQuery) {
  var _nameIsDirty = !! $('input[name="name"]').val();
  return {
    initialize: function() {
      $('input[name="name"]').on('change', function() {
        _nameIsDirty = true;
      });

      $('#field-resource-upload').on('change', function() {
        if (_nameIsDirty) {
          return;
        }
        var file_name = $(this).val().split(/^C:\\fakepath\\/).pop();

        // Internet Explorer 6-11 and Edge 20+
        var isIE = !!document.documentMode;
        var isEdge = !isIE && !!window.StyleMedia;
        // for IE/Edge when 'include filepath option' is enabled
        if (isIE || isEdge) {
          var fName = file_name.match(/[^\\\/]+$/);
          file_name = fName ? fName[0] : file_name;
        }

        $('input[name="name"]').val(file_name);
      });
    }
  }
});
