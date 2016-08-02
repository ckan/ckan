ckan.module('resource-view-filters-form', function (jQuery) {
  'use strict';

  function applyDropdown(selectField, resourceId) {
    var inputField = selectField.parent().find('input'),
        filterName = selectField.val(),
        queryLimit = 20;

    inputField.select2({
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
              plain: false,
              resource_id: resourceId,
              limit: queryLimit,
              offset: offset,
              fields: filterName,
              distinct: true,
              sort: filterName
            };

            if (term !== '') {
              var q = {};
              q[filterName] = term + ':*';
              query.q = JSON.stringify(q);
            }

            return query;
        },
        results: function (data, page) {
          var records = data.result.records,
              hasMore = (records.length < data.result.total),
              results;

          results = $.map(records, function (record) {
            return { id: record[filterName], text: String(record[filterName]) };
          });

          return { results: results, more: hasMore };
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
