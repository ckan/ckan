(function () {
  
  function extractDataAttributes() {
    var el = $(this);
    $.each(this.attributes, function () {
      var m = this.name.match(/data\-(\S+)/);
      if (m) { el.data(m[1], this.value); }
    });
  }
  
  function processResult(e, item) {
    $(this).val('')
           .parent('dd').before(
      '<input type="hidden" name="PackageGroup--package_id" value="' + item[1] + '">' +
      '<dd>' + item[0] + '</dd>'
    );
  }
  
  $(document).ready(function () {
    $('input.autocomplete').each(function () {
      extractDataAttributes.apply(this);
      
      var url = $(this).data('autocomplete-url');
      
      if (url) {
        $(this).autocomplete(url, {})
               .result(processResult);
      }
    });
  });
})(jQuery);
