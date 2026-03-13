this.ckan.module('resource-view-filters', function (jQuery) {
  'use strict';

  function initialize() {
    var self = this,
        resourceId = self.options.resourceId,
        fields = self.options.fields,
        dropdownTemplate = self.options.dropdownTemplate,
        addFilterTemplate = '<a class="btn btn-primary" href="#">' + self._('Add Filter') + '</a>',
        filtersDiv = $('<div></div>');

    if (!window.ckan) window.ckan = {};
    if (!ckan.views) ckan.views = {};
    if (!ckan.views.filters) {
      ckan.views.filters = (function () {
        function parseFilters() {
          var params = new URLSearchParams(window.location.search.substring(1));
          var raw = params.get('filters');
          var out = {};
          if (!raw) return out;
          try {
            raw = decodeURIComponent(raw);
          } catch (e) {}
          raw.split('|').forEach(function (kv) {
            var parts = kv.split(':');
            var key = parts.shift();
            var val = parts.join(':');
            try {
              val = decodeURIComponent(val);
            } catch (e) {}
            if (!val) return;
            if (val.charAt(0) === '{' && val.charAt(val.length-1) === '}') {
              out[key] = out[key] || [];
              out[key].push(val);
            } else {
              out[key] = out[key] || [];
              out[key].push(val);
            }
          });
          return out;
        }

        function buildAndRedirect(filtersObj) {
          var parts = [];
          for (var k in filtersObj) {
            var vals = filtersObj[k];
            if (!Array.isArray(vals)) vals = [vals];
            vals.forEach(function (v) {
              parts.push(encodeURIComponent(k) + ':' + encodeURIComponent(v));
            });
          }
          var params = new URLSearchParams(window.location.search.substring(1));
          if (parts.length > 0) {
            params.set('filters', parts.join('|'));
          } else {
            params.delete('filters');
          }
          var newUrl = window.location.pathname + (params.toString() ? ('?' + params.toString()) : '');
          window.location = newUrl;
        }

        return {
          get: function (name) {
            var f = parseFilters();
            if (name) return f[name];
            return f;
          },
          set: function (name, vals) {
            var f = parseFilters();
            f[name] = vals;
            buildAndRedirect(f);
          },
          unset: function (name) {
            var f = parseFilters();
            delete f[name];
            buildAndRedirect(f);
          }
        };
      }());
    }

    var filters = ckan.views.filters.get();
    _appendDropdowns(filtersDiv, resourceId, dropdownTemplate, fields, filters);
    var addFilterButton = _buildAddFilterButton(self, filtersDiv, addFilterTemplate,
                                                fields, filters, function (evt) {
      
      var filters = {};
      filters[evt.val] = [];

      $(this).select2('destroy');
      _appendDropdowns(filtersDiv, resourceId, dropdownTemplate, fields, filters);
      evt.preventDefault();
    });
    self.el.append(filtersDiv);
    self.el.append(addFilterButton);

    filtersDiv.on('change', '.operator-select', function() {
      var row = $(this).closest('.filter-row');
      var input = row.find('input');
      var filterName = input.attr('name');
      var operatorSelect = $(this);
      var filterName = operatorSelect.data('filterName');
      var newOperator = operatorSelect.val();
      var oldOperator = operatorSelect.data('previous-operator') || '=';
      
      var existingFilters = ckan.views.filters.get(filterName) || [];
      if (!Array.isArray(existingFilters)) {
        existingFilters = [existingFilters];
      }

      var mergedFilter = {};
      var equalityValues = [];
      for (var i = 0; i < existingFilters.length; i++) {
        var f = existingFilters[i];
        if (typeof f === 'string' && f.startsWith('{') && f.endsWith('}')) {
          try {
            var parsed = JSON.parse(f);
            $.extend(mergedFilter, parsed);
          } catch (e) {}
        } else if (f !== undefined && f !== null && f !== '') {
          equalityValues.push(f);
        }
      }

      var selValue = null;
      try {
        var selData = input.select2('data');
        if (selData) {
          if ($.isArray(selData)) {
            selValue = selData.length ? (selData[0].id || selData[0].text) : null;
          } else {
            selValue = selData.id || selData.text || selData;
          }
        }
      } catch (e) {
        selValue = input.val();
      }

      var currentValue = selValue || null;
      if (!currentValue) {
        if (oldOperator !== '=' && mergedFilter[oldOperator] !== undefined) {
          currentValue = mergedFilter[oldOperator];
        } else if (mergedFilter[newOperator] !== undefined) {
          currentValue = mergedFilter[newOperator];
        } else if (equalityValues.length === 1) {
          currentValue = equalityValues[0];
        }
      }

      if (!currentValue) {
        return;
      }

      if (newOperator === '=') {
        if (oldOperator !== '=' && mergedFilter[oldOperator] !== undefined) {
          var val = mergedFilter[oldOperator];
          delete mergedFilter[oldOperator];
          equalityValues.push(val);
        } else if (oldOperator === '=' ) {
        } else {
          equalityValues.push(currentValue);
        }
      } else {
        if (oldOperator === '=') {
          var idx = equalityValues.indexOf(currentValue);
          if (idx !== -1) equalityValues.splice(idx, 1);
          mergedFilter[newOperator] = currentValue;
        } else {
          if (mergedFilter[oldOperator] !== undefined) {
            var v = mergedFilter[oldOperator];
            delete mergedFilter[oldOperator];
            mergedFilter[newOperator] = v;
          } else {
            mergedFilter[newOperator] = currentValue;
          }
        }
      }

      var finalArray = equalityValues.slice();
      if (Object.keys(mergedFilter).length > 0) {
        finalArray.push(JSON.stringify(mergedFilter));
      }

      if (finalArray.length > 0) {
        ckan.views.filters.set(filterName, finalArray);
      } else {
        ckan.views.filters.unset(filterName);
      }

      operatorSelect.data('previous-operator', newOperator);
    });
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
        dropdowns.append(_buildDropdown(template, field, filters));
      }
    });

    return dropdowns;

    function _buildDropdown(template, filterName, filters) {
      var theseFilters = filters[filterName] || [];
      template = $(template.replace(/{filter}/g, filterName));
      // FIXME: Get the CSS class from some external variable
      var dropdowns = template.find('.resource-view-filter-values');

      var filterPairs = [];
      
      if (Array.isArray(theseFilters)) {
        for (var i = 0; i < theseFilters.length; i++) {
          var filter = theseFilters[i];
          if (typeof filter === 'string' && filter.startsWith('{') && filter.endsWith('}')) {
            try {
              var parsed = JSON.parse(filter);
              for (var op in parsed) {
                filterPairs.push({ operator: op, value: parsed[op] });
              }
            } catch (e) {
              filterPairs.push({ operator: '=', value: filter });
            }
          } else {
            filterPairs.push({ operator: '=', value: filter });
          }
        }
      }

      filterPairs.push({ operator: '=', value: undefined });

      filterPairs.forEach(function (pair) {
        // FIXME: -- use external CSS classes
        var row = $('<div class="filter-row" style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;"></div>');
        
        var operatorSelect = $('<select class="operator-select" style="width: 70px; height: 34px; padding: 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 13px;"><option value="=">=</option><option value="gt">&gt;</option><option value="gte">&gt;=</option><option value="lt">&lt;</option><option value="lte">&lt;=</option></select>');
        operatorSelect.data('filterName', filterName);
        operatorSelect.data('previous-operator', pair.operator);
        
        var inputWrapper = $('<div style="flex: 1; min-width: 0;"></div>');
        var input = $('<input type="hidden" name="'+filterName+'"></input>');

        operatorSelect.val(pair.operator);
        if (pair.value !== undefined) {
          input.val(pair.value);
        }

        inputWrapper.append(input);
        row.append(operatorSelect).append(inputWrapper);
        dropdowns.append(row);
      });

      var queryLimit = 20;
      dropdowns.find('input').select2({
        allowClear: true,
        placeholder: ' ', // select2 needs a placeholder to allow clearing
        width: '100%',
        minimumInputLength: 0,
        createSearchChoice: function(term, data) {
          if ($(data).filter(function() { return this.text.localeCompare(term) === 0; }).length === 0) {
            return {id: term, text: term};
          }
        },
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
        filterValue = evt.val;

    var operator = $(evt.currentTarget).closest('.filter-row').find('.operator-select').val() || '=';
    
    var mergedFilter = {};
    var equalityValues = [];

    var existingFilters = ckan.views.filters.get(filterName) || [];
    if (!Array.isArray(existingFilters)) {
      existingFilters = [existingFilters];
    }

    for (var i = 0; i < existingFilters.length; i++) {
      var f = existingFilters[i];
      if (typeof f === 'string' && f.startsWith('{') && f.endsWith('}')) {
        try {
          var parsed = JSON.parse(f);
          $.extend(mergedFilter, parsed);
        } catch (e) {}
      } else if (f !== undefined && f !== null && f !== '') {
        equalityValues.push(f);
      }
    }

    if (evt.removed) {
      var removedId = evt.removed.id;
      var eqIndex = equalityValues.indexOf(removedId);
      if (eqIndex !== -1) {
        equalityValues.splice(eqIndex, 1);
      } else {
        for (var op in mergedFilter) {
          if (mergedFilter[op] == removedId) {
            delete mergedFilter[op];
          }
        }
      }
    }

    if (evt.added) {
      if (operator === '=') {
        equalityValues.push(filterValue);
      } else {
        mergedFilter[operator] = filterValue;
      }
    }

    var finalArray = equalityValues.slice();
    if (Object.keys(mergedFilter).length > 0) {
      finalArray.push(JSON.stringify(mergedFilter));
    }

    if (finalArray.length > 0) {
      ckan.views.filters.set(filterName, finalArray);
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
