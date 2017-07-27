/**
 * Return a new JSON object of the old string.
 * Turns:
 *      file.js?a=1&amp;b.c=3.0&b.d=four&a_false_value=false&a_null_value=null
 * Into:
 *      {"a":1,"b":{"c":3,"d":"four"},"a_false_value":false,"a_null_value":null}
 * @version 1.1.0
 * @date July 16, 2010
 * @since 1.0.0, June 30, 2010
 * @package jquery-sparkle {@link http://balupton.com/projects/jquery-sparkle}
 * @author Benjamin "balupton" Lupton {@link http://balupton.com}
 * @copyright (c) 2009-2010 Benjamin Arthur Lupton {@link http://balupton.com}
 * @license MIT License {@link http://creativecommons.org/licenses/MIT/}
 */
String.prototype.queryStringToJSON = String.prototype.queryStringToJSON || function ( )
{   // Turns a params string or url into an array of params
    // Prepare
    var params = String(this);
    // Remove url if need be
    params = params.substring(params.indexOf('?')+1);
    // params = params.substring(params.indexOf('#')+1);
    // Change + to %20, the %20 is fixed up later with the decode
    params = params.replace(/\+/g, '%20');
    // Do we have JSON string
    if ( params.substring(0,1) === '{' && params.substring(params.length-1) === '}' )
    {   // We have a JSON string
        return eval(decodeURIComponent(params));
    }
    // We have a params string
    params = params.split(/\&(amp\;)?/);
    var json = {};
    // We have params
    for ( var i = 0, n = params.length; i < n; ++i )
    {
        // Adjust
        var param = params[i] || null;
        if ( param === null ) { continue; }
        param = param.split('=');
        if ( param === null ) { continue; }
        // ^ We now have "var=blah" into ["var","blah"]

        // Get
        var key = param[0] || null;
        if ( key === null ) { continue; }
        if ( typeof param[1] === 'undefined' ) { continue; }
        var value = param[1];
        // ^ We now have the parts

        // Fix
        key = decodeURIComponent(key);
        value = decodeURIComponent(value);

        // Set
        // window.console.log({'key':key,'value':value}, split);
        var keys = key.split('.');
        if ( keys.length === 1 )
        {   // Simple
            json[key] = value;
        }
        else
        {   // Advanced (Recreating an object)
            var path = '',
                cmd = '';
            // Ensure Path Exists
            $.each(keys,function(ii,key){
                path += '["'+key.replace(/"/g,'\\"')+'"]';
                jsonCLOSUREGLOBAL = json; // we have made this a global as closure compiler struggles with evals
                cmd = 'if ( typeof jsonCLOSUREGLOBAL'+path+' === "undefined" ) jsonCLOSUREGLOBAL'+path+' = {}';
                eval(cmd);
                json = jsonCLOSUREGLOBAL;
                delete jsonCLOSUREGLOBAL;
            });
            // Apply Value
            jsonCLOSUREGLOBAL = json; // we have made this a global as closure compiler struggles with evals
            valueCLOSUREGLOBAL = value; // we have made this a global as closure compiler struggles with evals
            cmd = 'jsonCLOSUREGLOBAL'+path+' = valueCLOSUREGLOBAL';
            eval(cmd);
            json = jsonCLOSUREGLOBAL;
            delete jsonCLOSUREGLOBAL;
            delete valueCLOSUREGLOBAL;
        }
        // ^ We now have the parts added to your JSON object
    }
    return json;
};

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
        defaultParams = urlQueryString.queryStringToJSON(),
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
    var searchParams = queryString.queryStringToJSON();

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
