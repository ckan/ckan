this.ckan.module('resource-view-filters', function (jQuery, _) {
  'use strict';

  function _onChange(evt) {
    var filterName = evt.currentTarget.name,
        filterValue = evt.val;

    if (ckan.views && ckan.views.viewhelpers) {
      ckan.views.viewhelpers.filters.set(filterName, filterValue);
    }
  }

  function _appendDropdowns(el, template, columnsValues) {
    var dropdowns = $('<div></div>'); // FIXME: We don't need a div

    $.each(columnsValues, function (filter, values) {
      dropdowns.append(_buildDropdown(self.el, template, filter, values));
    });

    el.append(dropdowns);

    function _buildDropdown(el, template, filter, values) {
      var dropdown = $(template.replace(/{filter}/g, filter));

      dropdown.find('input').select2({
        data: values,
        allowClear: true, // FIXME: This isn't working
        width: '220px',
      }).on('change', _onChange);

      return dropdown;
    }
  }

  function initialize() {
    var self = this,
        columnsValues = self.options.columnsValues,
        template = self.options.template;

    _appendDropdowns(self.el, template, columnsValues);
  }

  return {
    initialize: initialize,
    options: {
      template: [
        '<div class="dropdown">',
        '  {filter}:',
        '  <div class="dropdown-values">',
        '    <input type="hidden" name="{filter}"></input>',
        '  </div>',
        '</div>',
      ].join('\n')
    }
  };
});
