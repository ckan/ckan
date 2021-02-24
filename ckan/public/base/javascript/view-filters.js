this.ckan = this.ckan || {};
this.ckan.views = this.ckan.views || {};

this.ckan.views.filters = (function (queryString) {
  'use strict';

  var api = {
    get: get,
    set: set,
    setAndRedirectTo: setAndRedirectTo,
    unset: unset,
    _searchParams: {},
    _initialize: _initialize,
    _setLocationHref: _setLocationHref,
  };

  function get(filterName) {
    var filters = api._searchParams.filters || {};

    if (filterName) {
      return filters[filterName];
    } else {
      return filters;
    }
  }

  function set(name, value) {
    var url = window.location.href;

    setAndRedirectTo(name, value, url);
  }

  function setAndRedirectTo(name, value, url) {
    api._searchParams.filters = api._searchParams.filters || {};
    api._searchParams.filters[name] = value;

    _redirectTo(url);

    return api;
  }

  function unset(name, value) {
    var thisFilters = get(name);

    if (thisFilters) {
      var originalLength = thisFilters.length;

      // value and thisFilters are strings and equal
      if (thisFilters === value || value === undefined) {
        delete api._searchParams.filters[name];
      } else if ($.isArray(thisFilters)) {
        thisFilters = _removeElementsFromArray(thisFilters, value);

        // if we end up with an empty array, delete the filters param
        if (thisFilters.length === 0) {
          delete api._searchParams.filters[name];
        } else {
          api._searchParams.filters[name] = thisFilters;
        }
      }

      var haveFiltersChanged = (get(name) === undefined ||
                                get(name).length != originalLength);
      if (haveFiltersChanged) {
        _redirectTo(window.location.href);
      }
    }

    return api;
  }

  function _redirectTo(url) {
    var urlBase = url.split('?')[0],
        urlQueryString = url.split('?')[1] || '',
        defaultParams = Qs.parse(urlQueryString, { ignoreQueryPrefix: true }),
        queryString = _encodedParams(defaultParams),
        destinationUrl;

    destinationUrl = urlBase + '?' + queryString;

    api._setLocationHref(destinationUrl);
  }

  function _encodedParams(defaultParams) {
    var params = $.extend({}, defaultParams || {}, api._searchParams);

    if (params.filters) {
      params.filters = $.map(params.filters, function (fields, filter) {
        if (!$.isArray(fields)) {
          fields = [fields];
        }

        var fieldsStr = $.map(fields, function (field) {
          return filter + ':' + field;
        });

        return fieldsStr.join('|');
      }).join('|');
    }

    return $.param(params);
  }

  function _setLocationHref(destinationUrl) {
    window.location.href = destinationUrl;
  }

  function _removeElementsFromArray(array, elements) {
    var arrayCopy = array.slice(0);

    if (!$.isArray(elements)) {
      elements = [elements];
    }

    for (var i = 0; i < elements.length; i++) {
      var index = $.inArray(elements[i], arrayCopy);
      if (index > -1) {
        arrayCopy.splice(index, 1);
      }
    }

    return arrayCopy;
  }

  function _initialize(queryString) {
    // The filters are in format 'field:value|field:value|field:value'
    var searchParams = Qs.parse(queryString, { ignoreQueryPrefix: true });

    if (searchParams.filters) {
      var filters = {},
          fieldValuesStr = String(searchParams.filters).split('|'),
          i,
          len;

      for (i = 0, len = fieldValuesStr.length; i < len; i++) {
        var fieldValue = fieldValuesStr[i].match(/([^:]+):(.*)/),
            field = fieldValue[1],
            value = fieldValue[2];

        filters[field] = filters[field] || [];
        filters[field].push(value);
      }

      searchParams.filters = filters;
    }

    api._searchParams = searchParams;
  }

  _initialize(queryString);

  return api;
})(window.location.search);
