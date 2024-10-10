this.ckan.module('resource-upload-field', function (jQuery) {
  var _nameIsDirty = !! $('input[name="name"]').val();
  var urlField = $('#field-resource-url');
  return {
    initialize: function() {
      $('input[name="name"]').on('change', function() {
        _nameIsDirty = true;
      });

      // Change input type to text if Upload is selected
      if ($('#resource-url-upload').prop('checked')) {
        urlField.attr('type', 'text');
      }

      // revert to URL for Link option
      $('#resource-link-button').on('click', function() {
        urlField.attr('type', 'url');
      }) 

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
