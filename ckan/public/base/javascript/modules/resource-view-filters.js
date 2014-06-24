this.ckan.module('resource-view-filters', function (jQuery, _) {
  'use strict';

  // TODO: Don't show values already filtered by on the new selects

  function initialize() {
    var self = this,
        columnsValues = self.options.columnsValues,
        template = self.options.template;

    _appendDropdowns(self.el, template, columnsValues);
  }

  function _appendDropdowns(el, template, columnsValues) {
    var dropdowns = $('<div></div>'); // FIXME: We don't need a div

    $.each(columnsValues, function (filter, values) {
      dropdowns.append(_buildDropdown(self.el, template, filter, values));
    });

    el.append(dropdowns);

    function _buildDropdown(el, template, filterName, values) {
      var filters = ckan.views.viewhelpers.filters.get(filterName) || [];
      template = $(template.replace(/{filter}/g, filterName));
      var dropdowns = template.find('.dropdown-values');

      filters = filters.concat([undefined]); // Can't use push because we need to create a new array
      filters.forEach(function (value, i) {
        var dropdown = $('<input type="hidden" name="'+filterName+'"></input>');

        if (value !== undefined) {
          dropdown.val(value);
        }

        dropdowns.append(dropdown);
      });

      dropdowns.find('input').select2({
        data: values,
        allowClear: true, // FIXME: This isn't working
        width: '220px',
        initSelection: function (element, callback) {
          var data = {id: element.val(), text: element.val()};
          callback(data);
        },
      }).on('change', _onChange);

      return template;
    }
  }

  function _onChange(evt) {
    var filterName = evt.currentTarget.name,
        filterValue = evt.val,
        currentFilters = ckan.views.viewhelpers.filters.get(filterName) || [],
        addToIndex = currentFilters.length;

    if (evt.removed) {
      addToIndex = currentFilters.indexOf(evt.removed.id);
      if (addToIndex !== -1) {
        currentFilters.splice(addToIndex, 1);
      }
    }
    if (evt.added) {
      currentFilters.splice(addToIndex, 0, filterValue);
    }

    ckan.views.viewhelpers.filters.set(filterName, currentFilters);
  }

  return {
    initialize: initialize,
    options: {
      template: [
        '<div class="dropdown">',
        '  {filter}:',
        '  <div class="dropdown-values"></div>',
        '</div>',
      ].join('\n')
    }
  };
});
