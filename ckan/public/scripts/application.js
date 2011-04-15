jQuery(function ($) {
// Nuffin!
});

(function () {
  $(document).ready(function () {
    setupUserAutocomplete($('input.autocomplete-user'));
  });

  // Attach user autocompletion to provided elements
  //
  // Requires: jquery-ui autocomplete
  function setupUserAutocomplete(elements) {
    elements.autocomplete({
      minLength: 2,
      source: function(request, callback) {
        var url = '/api/2/util/user/autocomplete?q=' + request.term;
        $.getJSON(url, function(data) {
          $.each(data, function(idx, userobj) {
            var label = userobj.name;
            if (userobj.fullname) {
              label += ' [' + userobj.fullname + ']';
            }
            userobj.label = label;
            userobj.value = userobj.name;
          });
          callback(data)
        });
      }
    });
  }
})(jQuery);

