this.ckan.module('resource-view-filters', function (jQuery) {
  'use strict';

  function initialize() {
    var self = this,
        resourceId = self.options.resourceId,
        fields = self.options.fields,
        dropdownTemplate = self.options.dropdownTemplate,
        addFilterTemplate = '<a class="btn btn-primary" href="#">' + self._('Add Filter') + '</a>',
        filtersDiv = $('<div></div>');

    var filters = ckan.views.filters.get();
    _appendDropdowns(filtersDiv, resourceId, dropdownTemplate, fields, filters);
    var addFilterButton = _buildAddFilterButton(self, filtersDiv, addFilterTemplate,
                                                fields, filters, function (evt) {
      // Build filters object with this element's val as key and a placeholder
      // value so _appendDropdowns() will create its dropdown
      var filters = {};
      filters[evt.val] = [];

      $(this).select2('destroy');
      _appendDropdowns(filtersDiv, resourceId, dropdownTemplate, fields, filters);
      evt.preventDefault();
    });
    self.el.append(filtersDiv);
    self.el.append(addFilterButton);
  }

  function _buildAddFilterButton(self, el, template, fields, filters, onChangeCallback) {
    var addFilterButton = $(template),
        currentFilters = Object.keys(filters),
        fieldsNotFiltered = $.grep(fields, function (field) {
          return !filters.hasOwnProperty(field);
        }),
        data = $.map(fieldsNotFiltered, function (d) {
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
        placeholder: self._('Select a field'),
        width: 'resolve',
      }).on('change', onChangeCallback);

      evt.preventDefault();
    });

    return addFilterButton;
  }

  function _appendDropdowns(dropdowns, resourceId, template, fields, filters) {
    $.each(fields, function (i, field) {
      if (filters.hasOwnProperty(field)) {
        dropdowns.append(_buildDropdown(self.el, template, field));
      }
    });

    return dropdowns;

    function _buildDropdown(el, template, filterName) {
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

      var queryLimit = 20;
      dropdowns.find('input').select2({
        allowClear: true,
        placeholder: ' ', // select2 needs a placeholder to allow clearing
        width: 'resolve',
        minimumInputLength: 0,
        ajax: {
          url: ckan.url('/api/3/action/datastore_search'),
          datatype: 'json',
          quietMillis: 200,
          cache: true,
          data: function (term, page) {
            var offset = (page - 1) * queryLimit,
                query;

            query = {
              resource_id: resourceId,
              limit: queryLimit,
              offset: offset,
              fields: filterName,
              distinct: true,
              sort: filterName,
              include_total: false
            };


            if (term !== '') {
              var q = {};
              if (term.indexOf(' ') == -1) {
                term = term + ':*';
                query.plain = false;
              }
              q[filterName] = term;
              query.q = JSON.stringify(q);
            }

            return query;
          },
          results: function (data, page) {
            var records = data.result.records,
                hasMore = (records.length == queryLimit),
                results;

            results = $.map(records, function (record) {
              return { id: record[filterName], text: String(record[filterName]) };
            });

            return { results: results, more: hasMore };
          }
        },
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
        currentFilters = ckan.views.filters.get(filterName) || [],
        addToIndex = currentFilters.length;

    // Make sure we're not editing the original array, but a copy.
    currentFilters = currentFilters.slice();

    if (evt.removed) {
      addToIndex = currentFilters.indexOf(evt.removed.id);
      if (addToIndex !== -1) {
        currentFilters.splice(addToIndex, 1);
      }
    }
    if (evt.added) {
      currentFilters.splice(addToIndex, 0, filterValue);
    }

    if (currentFilters.length > 0) {
      ckan.views.filters.set(filterName, currentFilters);
    } else {
      ckan.views.filters.unset(filterName);
    }
  }

  return {
    initialize: initialize,
    options: {
      dropdownTemplate: [
        '<div class="resource-view-filter">',
        '  {filter}:',
        '  <div class="resource-view-filter-values"></div>',
        '</div>',
      ].join('\n')
    }
  };
});
