// # Recline Backbone Models
this.recline = this.recline || {};
this.recline.Model = this.recline.Model || {};

(function(my) {
  "use strict";

// use either jQuery or Underscore Deferred depending on what is available
var Deferred = (typeof jQuery !== "undefined" && jQuery.Deferred) || _.Deferred;

// ## <a id="dataset">Dataset</a>
my.Dataset = Backbone.Model.extend({
  constructor: function Dataset() {
    Backbone.Model.prototype.constructor.apply(this, arguments);
  },

  // ### initialize
  initialize: function() {
    var self = this;
    _.bindAll(this, 'query');
    this.backend = null;
    if (this.get('backend')) {
      this.backend = this._backendFromString(this.get('backend'));
    } else { // try to guess backend ...
      if (this.get('records')) {
        this.backend = recline.Backend.Memory;
      }
    }
    this.fields = new my.FieldList();
    this.records = new my.RecordList();
    this._changes = {
      deletes: [],
      updates: [],
      creates: []
    };
    this.facets = new my.FacetList();
    this.recordCount = null;
    this.queryState = new my.Query();
    this.queryState.bind('change facet:add', function () {
      self.query(); // We want to call query() without any arguments.
    });
    // store is what we query and save against
    // store will either be the backend or be a memory store if Backend fetch
    // tells us to use memory store
    this._store = this.backend;

    // if backend has a handleQueryResultFunction, use that
    this._handleResult = (this.backend != null && _.has(this.backend, 'handleQueryResult')) ? 
      this.backend.handleQueryResult : this._handleQueryResult;
    if (this.backend == recline.Backend.Memory) {
      this.fetch();
    }
  },

  sync: function(method, model, options) {
    return this.backend.sync(method, model, options);
  },

  // ### fetch
  //
  // Retrieve dataset and (some) records from the backend.
  fetch: function() {
    var self = this;
    var dfd = new Deferred();

    if (this.backend !== recline.Backend.Memory) {
      this.backend.fetch(this.toJSON())
        .done(handleResults)
        .fail(function(args) {
          dfd.reject(args);
        });
    } else {
      // special case where we have been given data directly
      handleResults({
        records: this.get('records'),
        fields: this.get('fields'),
        useMemoryStore: true
      });
    }

    function handleResults(results) {
      // if explicitly given the fields
      // (e.g. var dataset = new Dataset({fields: fields, ...})
      // use that field info over anything we get back by parsing the data
      // (results.fields)
      var fields = self.get('fields') || results.fields;

      var out = self._normalizeRecordsAndFields(results.records, fields);
      if (results.useMemoryStore) {
        self._store = new recline.Backend.Memory.Store(out.records, out.fields);
      }

      self.set(results.metadata);
      self.fields.reset(out.fields);
      self.query()
        .done(function() {
          dfd.resolve(self);
        })
        .fail(function(args) {
          dfd.reject(args);
        });
    }

    return dfd.promise();
  },

  // ### _normalizeRecordsAndFields
  // 
  // Get a proper set of fields and records from incoming set of fields and records either of which may be null or arrays or objects
  //
  // e.g. fields = ['a', 'b', 'c'] and records = [ [1,2,3] ] =>
  // fields = [ {id: a}, {id: b}, {id: c}], records = [ {a: 1}, {b: 2}, {c: 3}]
  _normalizeRecordsAndFields: function(records, fields) {
    // if no fields get them from records
    if (!fields && records && records.length > 0) {
      // records is array then fields is first row of records ...
      if (records[0] instanceof Array) {
        fields = records[0];
        records = records.slice(1);
      } else {
        fields = _.map(_.keys(records[0]), function(key) {
          return {id: key};
        });
      }
    } 

    // fields is an array of strings (i.e. list of field headings/ids)
    if (fields && fields.length > 0 && (fields[0] === null || typeof(fields[0]) != 'object')) {
      // Rename duplicate fieldIds as each field name needs to be
      // unique.
      var seen = {};
      fields = _.map(fields, function(field, index) {
        if (field === null) {
          field = '';
        } else {
          field = field.toString();
        }
        // cannot use trim as not supported by IE7
        var fieldId = field.replace(/^\s+|\s+$/g, '');
        if (fieldId === '') {
          fieldId = '_noname_';
          field = fieldId;
        }
        while (fieldId in seen) {
          seen[field] += 1;
          fieldId = field + seen[field];
        }
        if (!(field in seen)) {
          seen[field] = 0;
        }
        // TODO: decide whether to keep original name as label ...
        // return { id: fieldId, label: field || fieldId }
        return { id: fieldId };
      });
    }
    // records is provided as arrays so need to zip together with fields
    // NB: this requires you to have fields to match arrays
    if (records && records.length > 0 && records[0] instanceof Array) {
      records = _.map(records, function(doc) {
        var tmp = {};
        _.each(fields, function(field, idx) {
          tmp[field.id] = doc[idx];
        });
        return tmp;
      });
    }
    return {
      fields: fields,
      records: records
    };
  },

  save: function() {
    var self = this;
    // TODO: need to reset the changes ...
    return this._store.save(this._changes, this.toJSON());
  },

  // ### query
  //
  // AJAX method with promise API to get records from the backend.
  //
  // It will query based on current query state (given by this.queryState)
  // updated by queryObj (if provided).
  //
  // Resulting RecordList are used to reset this.records and are
  // also returned.
  query: function(queryObj) {
    var self = this;
    var dfd = new Deferred();
    this.trigger('query:start');

    if (queryObj) {
      var attributes = queryObj;
      if (queryObj instanceof my.Query) {
        attributes = queryObj.toJSON();
      }
      this.queryState.set(attributes, {silent: true});
    }
    var actualQuery = this.queryState.toJSON();

    this._store.query(actualQuery, this.toJSON())
      .done(function(queryResult) {
        self._handleResult(queryResult);
        self.trigger('query:done');
        dfd.resolve(self.records);
      })
      .fail(function(args) {
        self.trigger('query:fail', args);
        dfd.reject(args);
      });
    return dfd.promise();
  },

  _handleQueryResult: function(queryResult) {
    var self = this;
    self.recordCount = queryResult.total;
    var docs = _.map(queryResult.hits, function(hit) {
      var _doc = new my.Record(hit);
      _doc.fields = self.fields;
      _doc.bind('change', function(doc) {
        self._changes.updates.push(doc.toJSON());
      });
      _doc.bind('destroy', function(doc) {
        self._changes.deletes.push(doc.toJSON());
      });
      return _doc;
    });
    self.records.reset(docs);
    if (queryResult.facets) {
      var facets = _.map(queryResult.facets, function(facetResult, facetId) {
        facetResult.id = facetId;
        return new my.Facet(facetResult);
      });
      self.facets.reset(facets);
    }
  },

  toTemplateJSON: function() {
    var data = this.toJSON();
    data.recordCount = this.recordCount;
    data.fields = this.fields.toJSON();
    return data;
  },

  // ### getFieldsSummary
  //
  // Get a summary for each field in the form of a `Facet`.
  // 
  // @return null as this is async function. Provides deferred/promise interface.
  getFieldsSummary: function() {
    var self = this;
    var query = new my.Query();
    query.set({size: 0});
    this.fields.each(function(field) {
      query.addFacet(field.id);
    });
    var dfd = new Deferred();
    this._store.query(query.toJSON(), this.toJSON()).done(function(queryResult) {
      if (queryResult.facets) {
        _.each(queryResult.facets, function(facetResult, facetId) {
          facetResult.id = facetId;
          var facet = new my.Facet(facetResult);
          // TODO: probably want replace rather than reset (i.e. just replace the facet with this id)
          self.fields.get(facetId).facets.reset(facet);
        });
      }
      dfd.resolve(queryResult);
    });
    return dfd.promise();
  },

  // Deprecated (as of v0.5) - use record.summary()
  recordSummary: function(record) {
    return record.summary();
  },

  // ### _backendFromString(backendString)
  //
  // Look up a backend module from a backend string (look in recline.Backend)
  _backendFromString: function(backendString) {
    var backend = null;
    if (recline && recline.Backend) {
      _.each(_.keys(recline.Backend), function(name) {
        if (name.toLowerCase() === backendString.toLowerCase()) {
          backend = recline.Backend[name];
        }
      });
    }
    return backend;
  }
});


// ## <a id="record">A Record</a>
// 
// A single record (or row) in the dataset
my.Record = Backbone.Model.extend({
  constructor: function Record() {
    Backbone.Model.prototype.constructor.apply(this, arguments);
  },

  // ### initialize
  // 
  // Create a Record
  //
  // You usually will not do this directly but will have records created by
  // Dataset e.g. in query method
  //
  // Certain methods require presence of a fields attribute (identical to that on Dataset)
  initialize: function() {
    _.bindAll(this, 'getFieldValue');
  },

  // ### getFieldValue
  //
  // For the provided Field get the corresponding rendered computed data value
  // for this record.
  //
  // NB: if field is undefined a default '' value will be returned
  getFieldValue: function(field) {
    var val = this.getFieldValueUnrendered(field);
    if (field && !_.isUndefined(field.renderer)) {
      val = field.renderer(val, field, this.toJSON());
    }
    return val;
  },

  // ### getFieldValueUnrendered
  //
  // For the provided Field get the corresponding computed data value
  // for this record.
  //
  // NB: if field is undefined a default '' value will be returned
  getFieldValueUnrendered: function(field) {
    if (!field) {
      return '';
    }
    var val = this.get(field.id);
    if (field.deriver) {
      val = field.deriver(val, field, this);
    }
    return val;
  },

  // ### summary
  //
  // Get a simple html summary of this record in form of key/value list
  summary: function(record) {
    var self = this;
    var html = '<div class="recline-record-summary">';
    this.fields.each(function(field) { 
      if (field.id != 'id') {
        html += '<div class="' + field.id + '"><strong>' + field.get('label') + '</strong>: ' + self.getFieldValue(field) + '</div>';
      }
    });
    html += '</div>';
    return html;
  },

  // Override Backbone save, fetch and destroy so they do nothing
  // Instead, Dataset object that created this Record should take care of
  // handling these changes (discovery will occur via event notifications)
  // WARNING: these will not persist *unless* you call save on Dataset
  fetch: function() {},
  save: function() {},
  destroy: function() { this.trigger('destroy', this); }
});


// ## A Backbone collection of Records
my.RecordList = Backbone.Collection.extend({
  constructor: function RecordList() {
    Backbone.Collection.prototype.constructor.apply(this, arguments);
  },
  model: my.Record
});


// ## <a id="field">A Field (aka Column) on a Dataset</a>
my.Field = Backbone.Model.extend({
  constructor: function Field() {
    Backbone.Model.prototype.constructor.apply(this, arguments);
  },
  // ### defaults - define default values
  defaults: {
    label: null,
    type: 'string',
    format: null,
    is_derived: false
  },
  // ### initialize
  //
  // @param {Object} data: standard Backbone model attributes
  //
  // @param {Object} options: renderer and/or deriver functions.
  initialize: function(data, options) {
    // if a hash not passed in the first argument throw error
    if ('0' in data) {
      throw new Error('Looks like you did not pass a proper hash with id to Field constructor');
    }
    if (this.attributes.label === null) {
      this.set({label: this.id});
    }
    if (this.attributes.type.toLowerCase() in this._typeMap) {
      this.attributes.type = this._typeMap[this.attributes.type.toLowerCase()];
    }
    if (options) {
      this.renderer = options.renderer;
      this.deriver = options.deriver;
    }
    if (!this.renderer) {
      this.renderer = this.defaultRenderers[this.get('type')];
    }
    this.facets = new my.FacetList();
  },
  _typeMap: {
    'text': 'string',
    'double': 'number',
    'float': 'number',
    'numeric': 'number',
    'int': 'integer',
    'datetime': 'date-time',
    'bool': 'boolean',
    'timestamp': 'date-time',
    'json': 'object'
  },
  defaultRenderers: {
    object: function(val, field, doc) {
      return JSON.stringify(val);
    },
    geo_point: function(val, field, doc) {
      return JSON.stringify(val);
    },
    'number': function(val, field, doc) {
      var format = field.get('format'); 
      if (format === 'percentage') {
        return val + '%';
      }
      return val;
    },
    'string': function(val, field, doc) {
      var format = field.get('format');
      if (format === 'markdown') {
        if (typeof Showdown !== 'undefined') {
          var showdown = new Showdown.converter();
          out = showdown.makeHtml(val);
          return out;
        } else {
          return val;
        }
      } else if (format == 'plain') {
        return val;
      } else {
        // as this is the default and default type is string may get things
        // here that are not actually strings
        if (val && typeof val === 'string') {
          val = val.replace(/(https?:\/\/[^ ]+)/g, '<a href="$1">$1</a>');
        }
        return val;
      }
    }
  }
});

my.FieldList = Backbone.Collection.extend({
  constructor: function FieldList() {
    Backbone.Collection.prototype.constructor.apply(this, arguments);
  },
  model: my.Field
});

// ## <a id="query">Query</a>
my.Query = Backbone.Model.extend({
  constructor: function Query() {
    Backbone.Model.prototype.constructor.apply(this, arguments);
  },
  defaults: function() {
    return {
      size: 100,
      from: 0,
      q: '',
      facets: {},
      filters: []
    };
  },
  _filterTemplates: {
    term: {
      type: 'term',
      // TODO do we need this attribute here?
      field: '',
      term: ''
    },
    range: {
      type: 'range',
      from: '',
      to: ''
    },
    geo_distance: {
      type: 'geo_distance',
      distance: 10,
      unit: 'km',
      point: {
        lon: 0,
        lat: 0
      }
    }
  },  
  // ### addFilter(filter)
  //
  // Add a new filter specified by the filter hash and append to the list of filters
  //
  // @param filter an object specifying the filter - see _filterTemplates for examples. If only type is provided will generate a filter by cloning _filterTemplates
  addFilter: function(filter) {
    // crude deep copy
    var ourfilter = JSON.parse(JSON.stringify(filter));
    // not fully specified so use template and over-write
    if (_.keys(filter).length <= 3) {
      ourfilter = _.defaults(ourfilter, this._filterTemplates[filter.type]);
    }
    var filters = this.get('filters');
    filters.push(ourfilter);
    this.trigger('change:filters:new-blank');
  },
  replaceFilter: function(filter) {
    // delete filter on the same field, then add
    var filters = this.get('filters');
    var idx = -1;
    _.each(this.get('filters'), function(f, key, list) {
      if (filter.field == f.field) {
        idx = key;
      }
    });
    // trigger just one event (change:filters:new-blank) instead of one for remove and 
    // one for add
    if (idx >= 0) {
      filters.splice(idx, 1);
      this.set({filters: filters});
    }
    this.addFilter(filter);
  },
  updateFilter: function(index, value) {
  },
  // ### removeFilter
  //
  // Remove a filter from filters at index filterIndex
  removeFilter: function(filterIndex) {
    var filters = this.get('filters');
    filters.splice(filterIndex, 1);
    this.set({filters: filters});
    this.trigger('change');
  },
  // ### addFacet
  //
  // Add a Facet to this query
  //
  // See <http://www.elasticsearch.org/guide/reference/api/search/facets/>
  addFacet: function(fieldId, size, silent) {
    var facets = this.get('facets');
    // Assume id and fieldId should be the same (TODO: this need not be true if we want to add two different type of facets on same field)
    if (_.contains(_.keys(facets), fieldId)) {
      return;
    }
    facets[fieldId] = {
      terms: { field: fieldId }
    };
    if (!_.isUndefined(size)) {
      facets[fieldId].terms.size = size;
    }
    this.set({facets: facets}, {silent: true});
    if (!silent) {
      this.trigger('facet:add', this);
    }
  },
  addHistogramFacet: function(fieldId) {
    var facets = this.get('facets');
    facets[fieldId] = {
      date_histogram: {
        field: fieldId,
        interval: 'day'
      }
    };
    this.set({facets: facets}, {silent: true});
    this.trigger('facet:add', this);
  },
  removeFacet: function(fieldId) {
    var facets = this.get('facets');
    // Assume id and fieldId should be the same (TODO: this need not be true if we want to add two different type of facets on same field)
    if (!_.contains(_.keys(facets), fieldId)) {
      return;
    }
    delete facets[fieldId];
    this.set({facets: facets}, {silent: true});
    this.trigger('facet:remove', this);
  },
  clearFacets: function() {
    var facets = this.get('facets');
    _.each(_.keys(facets), function(fieldId) {
      delete facets[fieldId];
    });
    this.trigger('facet:remove', this);
  },
  // trigger a facet add; use this to trigger a single event after adding
  // multiple facets
  refreshFacets: function() {
    this.trigger('facet:add', this);
  }

});


// ## <a id="facet">A Facet (Result)</a>
my.Facet = Backbone.Model.extend({
  constructor: function Facet() {
    Backbone.Model.prototype.constructor.apply(this, arguments);
  },
  defaults: function() {
    return {
      _type: 'terms',
      total: 0,
      other: 0,
      missing: 0,
      terms: []
    };
  }
});

// ## A Collection/List of Facets
my.FacetList = Backbone.Collection.extend({
  constructor: function FacetList() {
    Backbone.Collection.prototype.constructor.apply(this, arguments);
  },
  model: my.Facet
});

// ## Object State
//
// Convenience Backbone model for storing (configuration) state of objects like Views.
my.ObjectState = Backbone.Model.extend({
});


// ## Backbone.sync
//
// Override Backbone.sync to hand off to sync function in relevant backend
// Backbone.sync = function(method, model, options) {
//   return model.backend.sync(method, model, options);
// };

}(this.recline.Model));

this.recline = this.recline || {};
this.recline.Backend = this.recline.Backend || {};
this.recline.Backend.Memory = this.recline.Backend.Memory || {};

(function(my) {
  "use strict";
  my.__type__ = 'memory';

  // private data - use either jQuery or Underscore Deferred depending on what is available
  var Deferred = (typeof jQuery !== "undefined" && jQuery.Deferred) || _.Deferred;

  // ## Data Wrapper
  //
  // Turn a simple array of JS objects into a mini data-store with
  // functionality like querying, faceting, updating (by ID) and deleting (by
  // ID).
  //
  // @param records list of hashes for each record/row in the data ({key:
  // value, key: value})
  // @param fields (optional) list of field hashes (each hash defining a field
  // as per recline.Model.Field). If fields not specified they will be taken
  // from the data.
  my.Store = function(records, fields) {
    var self = this;
    this.records = records;
    // backwards compatability (in v0.5 records was named data)
    this.data = this.records;
    if (fields) {
      this.fields = fields;
    } else {
      if (records) {
        this.fields = _.map(records[0], function(value, key) {
          return {id: key, type: 'string'};
        });
      }
    }

    this.update = function(doc) {
      _.each(self.records, function(internalDoc, idx) {
        if(doc.id === internalDoc.id) {
          self.records[idx] = doc;
        }
      });
    };

    this.remove = function(doc) {
      var newdocs = _.reject(self.records, function(internalDoc) {
        return (doc.id === internalDoc.id);
      });
      this.records = newdocs;
    };

    this.save = function(changes, dataset) {
      var self = this;
      var dfd = new Deferred();
      // TODO _.each(changes.creates) { ... }
      _.each(changes.updates, function(record) {
        self.update(record);
      });
      _.each(changes.deletes, function(record) {
        self.remove(record);
      });
      dfd.resolve();
      return dfd.promise();
    },

    this.query = function(queryObj) {
      var dfd = new Deferred();
      var numRows = queryObj.size || this.records.length;
      var start = queryObj.from || 0;
      var results = this.records;
      
      results = this._applyFilters(results, queryObj);
      results = this._applyFreeTextQuery(results, queryObj);

      // TODO: this is not complete sorting!
      // What's wrong is we sort on the *last* entry in the sort list if there are multiple sort criteria
      _.each(queryObj.sort, function(sortObj) {
        var fieldName = sortObj.field;
        results = _.sortBy(results, function(doc) {
          var _out = doc[fieldName];
          return _out;
        });
        if (sortObj.order == 'desc') {
          results.reverse();
        }
      });
      var facets = this.computeFacets(results, queryObj);
      var out = {
        total: results.length,
        hits: results.slice(start, start+numRows),
        facets: facets
      };
      dfd.resolve(out);
      return dfd.promise();
    };

    // in place filtering
    this._applyFilters = function(results, queryObj) {
      var filters = queryObj.filters;
      // register filters
      var filterFunctions = {
        term         : term,
        terms        : terms,
        range        : range,
        geo_distance : geo_distance
      };
      var dataParsers = {
        integer: function (e) { return parseFloat(e, 10); },
        'float': function (e) { return parseFloat(e, 10); },
        number: function (e) { return parseFloat(e, 10); },
        string : function (e) { return e.toString(); },
        date   : function (e) { return moment(e).valueOf(); },
        datetime   : function (e) { return new Date(e).valueOf(); }
      };
      var keyedFields = {};
      _.each(self.fields, function(field) {
        keyedFields[field.id] = field;
      });
      function getDataParser(filter) {
        var fieldType = keyedFields[filter.field].type || 'string';
        return dataParsers[fieldType];
      }

      // filter records
      return _.filter(results, function (record) {
        var passes = _.map(filters, function (filter) {
          return filterFunctions[filter.type](record, filter);
        });

        // return only these records that pass all filters
        return _.all(passes, _.identity);
      });

      // filters definitions
      function term(record, filter) {
        var parse = getDataParser(filter);
        var value = parse(record[filter.field]);
        var term  = parse(filter.term);

        return (value === term);
      }

      function terms(record, filter) {
        var parse = getDataParser(filter);
        var value = parse(record[filter.field]);
        var terms  = parse(filter.terms).split(",");

        return (_.indexOf(terms, value) >= 0);
      }

      function range(record, filter) {
        var fromnull = (_.isUndefined(filter.from) || filter.from === null || filter.from === '');
        var tonull = (_.isUndefined(filter.to) || filter.to === null || filter.to === '');
        var parse = getDataParser(filter);
        var value = parse(record[filter.field]);
        var from = parse(fromnull ? '' : filter.from);
        var to  = parse(tonull ? '' : filter.to);

        // if at least one end of range is set do not allow '' to get through
        // note that for strings '' <= {any-character} e.g. '' <= 'a'
        if ((!fromnull || !tonull) && value === '') {
          return false;
        }
        return ((fromnull || value >= from) && (tonull || value <= to));
      }

      function geo_distance() {
        // TODO code here
      }
    };

    // we OR across fields but AND across terms in query string
    this._applyFreeTextQuery = function(results, queryObj) {
      if (queryObj.q) {
        var terms = queryObj.q.split(' ');
        var patterns=_.map(terms, function(term) {
          return new RegExp(term.toLowerCase());
        });
        results = _.filter(results, function(rawdoc) {
          var matches = true;
          _.each(patterns, function(pattern) {
            var foundmatch = false;
            _.each(self.fields, function(field) {
              var value = rawdoc[field.id];
              if ((value !== null) && (value !== undefined)) { 
                value = value.toString();
              } else {
                // value can be null (apparently in some cases)
                value = '';
              }
              // TODO regexes?
              foundmatch = foundmatch || (pattern.test(value.toLowerCase()));
              // TODO: early out (once we are true should break to spare unnecessary testing)
              // if (foundmatch) return true;
            });
            matches = matches && foundmatch;
            // TODO: early out (once false should break to spare unnecessary testing)
            // if (!matches) return false;
          });
          return matches;
        });
      }
      return results;
    };

    this.computeFacets = function(records, queryObj) {
      var facetResults = {};
      if (!queryObj.facets) {
        return facetResults;
      }
      _.each(queryObj.facets, function(query, facetId) {
        // TODO: remove dependency on recline.Model
        facetResults[facetId] = new recline.Model.Facet({id: facetId}).toJSON();
        facetResults[facetId].termsall = {};
      });
      // faceting
      _.each(records, function(doc) {
        _.each(queryObj.facets, function(query, facetId) {
          var fieldId = query.terms.field;
          var val = doc[fieldId];
          var tmp = facetResults[facetId];
          if (val) {
            tmp.termsall[val] = tmp.termsall[val] ? tmp.termsall[val] + 1 : 1;
          } else {
            tmp.missing = tmp.missing + 1;
          }
        });
      });
      _.each(queryObj.facets, function(query, facetId) {
        var tmp = facetResults[facetId];
        var terms = _.map(tmp.termsall, function(count, term) {
          return { term: term, count: count };
        });
        tmp.terms = _.sortBy(terms, function(item) {
          // want descending order
          return -item.count;
        });
        tmp.terms = tmp.terms.slice(0, 10);
      });
      return facetResults;
    };
  };

}(this.recline.Backend.Memory));
