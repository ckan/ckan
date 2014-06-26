this.ckan.module('resource-view-filters', function (jQuery, _) {
  'use strict';

  function initialize() {
    var self = this,
        columnsValues = self.options.columnsValues,
        dropdownTemplate = self.options.dropdownTemplate,
        addFilterTemplate = self.options.addFilterTemplate,
        filtersDiv = $('<div></div>');

    var filters = ckan.views.viewhelpers.filters.get();
    _appendDropdowns(filtersDiv, dropdownTemplate, columnsValues, filters);
    var addFilterButton = _buildAddFilterButton(filtersDiv, addFilterTemplate, columnsValues, filters, function (evt) {
      // Build filters object with this element's val as key and a placeholder
      // value so _appendDropdowns() will create its dropdown
      var filters = {};
      filters[evt.val] = [];

      $(this).select2('destroy');
      _appendDropdowns(filtersDiv, dropdownTemplate, columnsValues, filters);
      evt.preventDefault();
    });
    self.el.append(filtersDiv);
    self.el.append(addFilterButton);
  }

  function _buildAddFilterButton(el, template, columnsValues, filters, onChangeCallback) {
    // TODO: Add Object.keys() and .filter() method for browsers that don't implement it.
    var addFilterButton = $(template),
        currentFilters = Object.keys(filters),
        columns = Object.keys(columnsValues),
        columnsNotFiltered = columns.filter(function (column) {
          return currentFilters.indexOf(column) == -1;
        }),
        data = $.map(columnsNotFiltered, function (d) {
          return { id: d, text: d };
        });

    if (data.length === 0) {
      return '';
    }

    addFilterButton.click(function (evt) {
      // FIXME: Move this class name to some external variable to keep it DRY
      var addFilterDiv = $('<div class="resource-view-filter"><input type="hidden"></input></div>'),
          addFilterInput = addFilterDiv.find('input');
      el.append(addFilterDiv);

      // TODO: Remove element from "data" when some select selects it.
      addFilterInput.select2({
        data: data,
        placeholder: 'Select a column',
        width: 'resolve',
      }).on('change', onChangeCallback);

      evt.preventDefault();
    });

    return addFilterButton;
  }

  function _appendDropdowns(dropdowns, template, columnsValues, filters) {

    $.each(columnsValues, function (filter, values) {
      if (filters.hasOwnProperty(filter)) {
        dropdowns.append(_buildDropdown(self.el, template, filter, values));
      }
    });

    return dropdowns;

    function _buildDropdown(el, template, filterName, values) {
      var theseFilters = filters[filterName] || [];
      template = $(template.replace(/{filter}/g, filterName));
      // FIXME: Get the CSS class from some external variable
      var dropdowns = template.find('.resource-view-filter-values');

      // Can't use push because we need to create a new array, as we're
      // modifying it.
      theseFilters = theseFilters.concat([undefined]);
      theseFilters.forEach(function (value, i) {
        var dropdown = $('<input type="hidden" name="'+filterName+'"></input>');

        if (value !== undefined) {
          dropdown.val(value);
        }

        dropdowns.append(dropdown);
      });

      dropdowns.find('input').select2({
        data: values,
        allowClear: true,
        placeholder: ' ', // select2 needs a placeholder to allow clearing
        width: 'resolve',
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
      dropdownTemplate: [
        '<div class="resource-view-filter">',
        '  {filter}:',
        '  <div class="resource-view-filter-values"></div>',
        '</div>',
      ].join('\n'),
      addFilterTemplate: [
        '<a href="#">Add Filter</a>',
      ].join('\n')
    }
  };
});
