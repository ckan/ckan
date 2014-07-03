ckan.module('resource-view-filters-form', function (jQuery) {
  'use strict';

  function applyDropdown(selectField, resourceId) {
    var inputField = selectField.parent().find('input'),
        filterName = selectField.val(),
        queryLimit = 100;

    inputField.select2({
      width: 'resolve',
      minimumInputLength: 0,
      ajax: {
        url: '/api/3/action/datastore_search',
        datatype: 'json',
        quietMillis: 200,
        cache: true,
        data: function (term, page) {
          var limit = queryLimit + 1, // Get 1 more than the queryLimit
                                      // so we can test later if there's more
                                      // data
              offset = (page - 1) * queryLimit;
          return {
            q: term,
            resource_id: resourceId,
            limit: queryLimit + 1,
            offset: offset,
            fields: filterName,
            sort: filterName
          };
        },
        results: function (data, page) {
          var uniqueResults = {},
              results = data.result.records.slice(0, queryLimit),
              hasMore = (data.result.records.length == queryLimit + 1),
              theData;
          $.each(results, function (i, record) {
            uniqueResults[record[filterName]] = true;
          });
          theData = $.map(Object.keys(uniqueResults), function (record) {
            return { id: record, text: record };
          });

          return { results: theData, more: hasMore };
        },
      },
      initSelection: function (element, callback) {
        var data = {id: element.val(), text: element.val()};
        callback(data);
      },
    });
  }

  function initialize() {
    var self = this,
        resourceId = self.options.resourceId,
        templateFilterInputs = self.options.templateFilterInputs,
        inputFieldTemplateEl = $(templateFilterInputs).find('input[type="text"][name]'),
        filtersDiv = self.el.find(self.options.filtersSelector),
        addFilterEl = self.el.find(self.options.addFilterSelector),
        removeFilterSelector = self.options.removeFilterSelector;

    var selects = filtersDiv.find('select');
    selects.each(function (i, select) {
       applyDropdown($(select), resourceId);
    });

    addFilterEl.click(function (evt) {
      var selectField;
      evt.preventDefault();
      filtersDiv.append(templateFilterInputs);
      selectField = filtersDiv.children().last().find('select');
      applyDropdown(selectField, resourceId);
    });

    filtersDiv.on('click', removeFilterSelector, function (evt) {
      evt.preventDefault();
      $(this).parent().remove();
    });

    filtersDiv.on('change', 'select', function (evt) {
      var el = $(this),
          parentEl = el.parent(),
          inputField = parentEl.find('input'),
          select2Container = parentEl.find('.select2-container');
      evt.preventDefault();
      select2Container.remove();
      inputField.replaceWith(inputFieldTemplateEl.clone());
      applyDropdown(el, resourceId);
    });
  }

  return {
    initialize: initialize
  };
});
