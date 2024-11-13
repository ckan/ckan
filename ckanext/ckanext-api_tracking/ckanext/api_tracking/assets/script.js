ckan.module("api_tracking-module", function ($, _) {
  "use strict";
  return {
    options: {
      debug: false,
    },

    initialize: function () {
      
    },
  };
});

$(document).ready(function () {
  $('#package_name').select2({
    placeholder: 'Select package name(s)',
    allowClear: true
  })
})
