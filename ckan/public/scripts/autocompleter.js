// TODO: Remove as this appears to be unused code. (Check this).

(function () {
  
  function processResult(e, item) {
    var input_box = $(this)
    input_box.val('')
    var parent_dd = input_box.parent('dd')
    var old_name = input_box.attr('name')
    var field_name_regex = /^(\S+)__(\d+)__(\S+)$/;
    var split = old_name.match(field_name_regex)

    var new_name = split[1] + '__' + (parseInt(split[2]) + 1) + '__' + split[3]

    input_box.attr('name', new_name)
    input_box.attr('id', new_name)

    parent_dd.before(
      '<input type="hidden" name="' + old_name + '" value="' + item[1] + '">' +
      '<dd>' + item[0] + '</dd>'
    );
  }
  
  $(document).ready(function () {
    $('input.autocomplete').autocomplete('/package/autocomplete', {})
               .result(processResult);
  });
})(jQuery);
