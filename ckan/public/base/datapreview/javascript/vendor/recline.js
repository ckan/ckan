// adapted from https://github.com/harthur/costco. heather rules

var costco = function() {
  
  function evalFunction(funcString) {
    try {
      eval("var editFunc = " + funcString);
    } catch(e) {
      return {errorMessage: e+""};
    }
    return editFunc;
  }
  
  function previewTransform(docs, editFunc, currentColumn) {
    var preview = [];
    var updated = mapDocs($.extend(true, {}, docs), editFunc);
    for (var i = 0; i < updated.docs.length; i++) {      
      var before = docs[i]
        , after = updated.docs[i]
        ;
      if (!after) after = {};
      if (currentColumn) {
        preview.push({before: JSON.stringify(before[currentColumn]), after: JSON.stringify(after[currentColumn])});      
      } else {
        preview.push({before: JSON.stringify(before), after: JSON.stringify(after)});      
      }
    }
    return preview;
  }

  function mapDocs(docs, editFunc) {
    var edited = []
      , deleted = []
      , failed = []
      ;
    
    var updatedDocs = _.map(docs, function(doc) {
      try {
        var updated = editFunc(_.clone(doc));
      } catch(e) {
        failed.push(doc);
        return;
      }
      if(updated === null) {
        updated = {_deleted: true};
        edited.push(updated);
        deleted.push(doc);
      }
      else if(updated && !_.isEqual(updated, doc)) {
        edited.push(updated);
      }
      return updated;      
    });
    
    return {
      edited: edited, 
      docs: updatedDocs, 
      deleted: deleted, 
      failed: failed
    };
  }
  
  return {
    evalFunction: evalFunction,
    previewTransform: previewTransform,
    mapDocs: mapDocs
  };
}();
// # Recline Backbone Models
this.recline = this.recline || {};
this.recline.Model = this.recline.Model || {};

(function($, my) {

// ## <a id="dataset">A Dataset model</a>
//
// A model has the following (non-Backbone) attributes:
//
// @property {FieldList} fields: (aka columns) is a `FieldList` listing all the
// fields on this Dataset (this can be set explicitly, or, will be set by
// Dataset.fetch() or Dataset.query()
//
// @property {DocumentList} currentDocuments: a `DocumentList` containing the
// Documents we have currently loaded for viewing (updated by calling query
// method)
//
// @property {number} docCount: total number of documents in this dataset
//
// @property {Backend} backend: the Backend (instance) for this Dataset.
//
// @property {Query} queryState: `Query` object which stores current
// queryState. queryState may be edited by other components (e.g. a query
// editor view) changes will trigger a Dataset query.
//
// @property {FacetList} facets: FacetList object containing all current
// Facets.
my.Dataset = Backbone.Model.extend({
  __type__: 'Dataset',

  // ### initialize
  // 
  // Sets up instance properties (see above)
  //
  // @param {Object} model: standard set of model attributes passed to Backbone models
  //
  // @param {Object or String} backend: Backend instance (see
  // `recline.Backend.Base`) or a string specifying that instance. The
  // string specifying may be a full class path e.g.
  // 'recline.Backend.ElasticSearch' or a simple name e.g.
  // 'elasticsearch' or 'ElasticSearch' (in this case must be a Backend in
  // recline.Backend module)
  initialize: function(model, backend) {
    _.bindAll(this, 'query');
    this.backend = backend;
    if (typeof(backend) === 'string') {
      this.backend = this._backendFromString(backend);
    }
    this.fields = new my.FieldList();
    this.currentDocuments = new my.DocumentList();
    this.facets = new my.FacetList();
    this.docCount = null;
    this.queryState = new my.Query();
    this.queryState.bind('change', this.query);
    this.queryState.bind('facet:add', this.query);
  },

  // ### query
  //
  // AJAX method with promise API to get documents from the backend.
  //
  // It will query based on current query state (given by this.queryState)
  // updated by queryObj (if provided).
  //
  // Resulting DocumentList are used to reset this.currentDocuments and are
  // also returned.
  query: function(queryObj) {
    var self = this;
    this.trigger('query:start');
    var actualQuery = self._prepareQuery(queryObj);
    var dfd = $.Deferred();
    this.backend.query(this, actualQuery).done(function(queryResult) {
      self.docCount = queryResult.total;
      var docs = _.map(queryResult.hits, function(hit) {
        var _doc = new my.Document(hit._source);
        _doc.backend = self.backend;
        _doc.dataset = self;
        return _doc;
      });
      self.currentDocuments.reset(docs);
      if (queryResult.facets) {
        var facets = _.map(queryResult.facets, function(facetResult, facetId) {
          facetResult.id = facetId;
          return new my.Facet(facetResult);
        });
        self.facets.reset(facets);
      }
      self.trigger('query:done');
      dfd.resolve(self.currentDocuments);
    })
    .fail(function(arguments) {
      self.trigger('query:fail', arguments);
      dfd.reject(arguments);
    });
    return dfd.promise();
  },

  _prepareQuery: function(newQueryObj) {
    if (newQueryObj) {
      this.queryState.set(newQueryObj);
    }
    var out = this.queryState.toJSON();
    return out;
  },

  toTemplateJSON: function() {
    var data = this.toJSON();
    data.docCount = this.docCount;
    data.fields = this.fields.toJSON();
    return data;
  },

  // ### _backendFromString(backendString)
  //
  // See backend argument to initialize for details
  _backendFromString: function(backendString) {
    var parts = backendString.split('.');
    // walk through the specified path xxx.yyy.zzz to get the final object which should be backend class
    var current = window;
    for(ii=0;ii<parts.length;ii++) {
      if (!current) {
        break;
      }
      current = current[parts[ii]];
    }
    if (current) {
      return new current();
    }

    // alternatively we just had a simple string
    var backend = null;
    if (recline && recline.Backend) {
      _.each(_.keys(recline.Backend), function(name) {
        if (name.toLowerCase() === backendString.toLowerCase()) {
          backend = new recline.Backend[name]();
        }
      });
    }
    return backend;
  }
});


// ### Dataset.restore
//
// Restore a Dataset instance from a serialized state. Serialized state for a
// Dataset is an Object like:
// 
// <pre>
// {
//   backend: {backend type - i.e. value of dataset.backend.__type__}
//   dataset: {dataset info needed for loading -- result of dataset.toJSON() would be sufficient but can be simpler }
//   // convenience - if url provided and dataste not this be used as dataset url
//   url: {dataset url}
//   ...
// }
my.Dataset.restore = function(state) {
  // hack-y - restoring a memory dataset does not mean much ...
  var dataset = null;
  if (state.url && !state.dataset) {
    state.dataset = {url: state.url};
  }
  if (state.backend === 'memory') {
    dataset = recline.Backend.createDataset(
      [{stub: 'this is a stub dataset because we do not restore memory datasets'}],
      [],
      state.dataset // metadata
    );
  } else {
    dataset = new recline.Model.Dataset(
      state.dataset,
      state.backend
    );
  }
  return dataset;
};

// ## <a id="document">A Document (aka Row)</a>
// 
// A single entry or row in the dataset
my.Document = Backbone.Model.extend({
  __type__: 'Document',
  initialize: function() {
    _.bindAll(this, 'getFieldValue');
  },

  // ### getFieldValue
  //
  // For the provided Field get the corresponding rendered computed data value
  // for this document.
  getFieldValue: function(field) {
    var val = this.get(field.id);
    if (field.deriver) {
      val = field.deriver(val, field, this);
    }
    if (field.renderer) {
      val = field.renderer(val, field, this);
    }
    return val;
  }
});

// ## A Backbone collection of Documents
my.DocumentList = Backbone.Collection.extend({
  __type__: 'DocumentList',
  model: my.Document
});

// ## <a id="field">A Field (aka Column) on a Dataset</a>
// 
// Following (Backbone) attributes as standard:
//
// * id: a unique identifer for this field- usually this should match the key in the documents hash
// * label: (optional: defaults to id) the visible label used for this field
// * type: (optional: defaults to string) the type of the data in this field. Should be a string as per type names defined by ElasticSearch - see Types list on <http://www.elasticsearch.org/guide/reference/mapping/>
// * format: (optional) used to indicate how the data should be formatted. For example:
//   * type=date, format=yyyy-mm-dd
//   * type=float, format=percentage
//   * type=string, format=link (render as hyperlink)
//   * type=string, format=markdown (render as markdown if Showdown available)
// * is_derived: (default: false) attribute indicating this field has no backend data but is just derived from other fields (see below).
// 
// Following additional instance properties:
// 
// @property {Function} renderer: a function to render the data for this field.
// Signature: function(value, field, doc) where value is the value of this
// cell, field is corresponding field object and document is the document
// object. Note that implementing functions can ignore arguments (e.g.
// function(value) would be a valid formatter function).
// 
// @property {Function} deriver: a function to derive/compute the value of data
// in this field as a function of this field's value (if any) and the current
// document, its signature and behaviour is the same as for renderer.  Use of
// this function allows you to define an entirely new value for data in this
// field. This provides support for a) 'derived/computed' fields: i.e. fields
// whose data are functions of the data in other fields b) transforming the
// value of this field prior to rendering.
my.Field = Backbone.Model.extend({
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
    if (options) {
      this.renderer = options.renderer;
      this.deriver = options.deriver;
    }
    if (!this.renderer) {
      this.renderer = this.defaultRenderers[this.get('type')];
    }
  },
  defaultRenderers: {
    object: function(val, field, doc) {
      return JSON.stringify(val);
    },
    'float': function(val, field, doc) {
      var format = field.get('format'); 
      if (format === 'percentage') {
        return val + '%';
      }
      return val;
    },
    'string': function(val, field, doc) {
      var format = field.get('format');
      if (format === 'link') {
        return '<a href="VAL">VAL</a>'.replace(/VAL/g, val);
      } else if (format === 'markdown') {
        if (typeof Showdown !== 'undefined') {
          var showdown = new Showdown.converter();
          out = showdown.makeHtml(val);
          return out;
        } else {
          return val;
        }
      }
      return val;
    }
  }
});

my.FieldList = Backbone.Collection.extend({
  model: my.Field
});

// ## <a id="query">Query</a>
//
// Query instances encapsulate a query to the backend (see <a
// href="backend/base.html">query method on backend</a>). Useful both
// for creating queries and for storing and manipulating query state -
// e.g. from a query editor).
//
// **Query Structure and format**
//
// Query structure should follow that of [ElasticSearch query
// language](http://www.elasticsearch.org/guide/reference/api/search/).
//
// **NB: It is up to specific backends how to implement and support this query
// structure. Different backends might choose to implement things differently
// or not support certain features. Please check your backend for details.**
//
// Query object has the following key attributes:
// 
//  * size (=limit): number of results to return
//  * from (=offset): offset into result set - http://www.elasticsearch.org/guide/reference/api/search/from-size.html
//  * sort: sort order - <http://www.elasticsearch.org/guide/reference/api/search/sort.html>
//  * query: Query in ES Query DSL <http://www.elasticsearch.org/guide/reference/api/search/query.html>
//  * filter: See filters and <a href="http://www.elasticsearch.org/guide/reference/query-dsl/filtered-query.html">Filtered Query</a>
//  * fields: set of fields to return - http://www.elasticsearch.org/guide/reference/api/search/fields.html
//  * facets: specification of facets - see http://www.elasticsearch.org/guide/reference/api/search/facets/
// 
// Additions:
// 
//  * q: either straight text or a hash will map directly onto a [query_string
//  query](http://www.elasticsearch.org/guide/reference/query-dsl/query-string-query.html)
//  in backend
//
//   * Of course this can be re-interpreted by different backends. E.g. some
//   may just pass this straight through e.g. for an SQL backend this could be
//   the full SQL query
//
//  * filters: dict of ElasticSearch filters. These will be and-ed together for
//  execution.
// 
// **Examples**
// 
// <pre>
// {
//    q: 'quick brown fox',
//    filters: [
//      { term: { 'owner': 'jones' } }
//    ]
// }
// </pre>
my.Query = Backbone.Model.extend({
  defaults: function() {
    return {
      size: 100,
      from: 0,
      facets: {},
      // <http://www.elasticsearch.org/guide/reference/query-dsl/and-filter.html>
      // , filter: {}
      filters: []
    };
  },
  // #### addTermFilter
  // 
  // Set (update or add) a terms filter to filters
  //
  // See <http://www.elasticsearch.org/guide/reference/query-dsl/terms-filter.html>
  addTermFilter: function(fieldId, value) {
    var filters = this.get('filters');
    var filter = { term: {} };
    filter.term[fieldId] = value;
    filters.push(filter);
    this.set({filters: filters});
    // change does not seem to be triggered automatically
    if (value) {
      this.trigger('change');
    } else {
      // adding a new blank filter and do not want to trigger a new query
      this.trigger('change:filters:new-blank');
    }
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
  addFacet: function(fieldId) {
    var facets = this.get('facets');
    // Assume id and fieldId should be the same (TODO: this need not be true if we want to add two different type of facets on same field)
    if (_.contains(_.keys(facets), fieldId)) {
      return;
    }
    facets[fieldId] = {
      terms: { field: fieldId }
    };
    this.set({facets: facets}, {silent: true});
    this.trigger('facet:add', this);
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
  }
});


// ## <a id="facet">A Facet (Result)</a>
//
// Object to store Facet information, that is summary information (e.g. values
// and counts) about a field obtained by some faceting method on the
// backend.
//
// Structure of a facet follows that of Facet results in ElasticSearch, see:
// <http://www.elasticsearch.org/guide/reference/api/search/facets/>
//
// Specifically the object structure of a facet looks like (there is one
// addition compared to ElasticSearch: the "id" field which corresponds to the
// key used to specify this facet in the facet query):
//
// <pre>
// {
//   "id": "id-of-facet",
//   // type of this facet (terms, range, histogram etc)
//   "_type" : "terms",
//   // total number of tokens in the facet
//   "total": 5,
//   // @property {number} number of documents which have no value for the field
//   "missing" : 0,
//   // number of facet values not included in the returned facets
//   "other": 0,
//   // term object ({term: , count: ...})
//   "terms" : [ {
//       "term" : "foo",
//       "count" : 2
//     }, {
//       "term" : "bar",
//       "count" : 2
//     }, {
//       "term" : "baz",
//       "count" : 1
//     }
//   ]
// }
// </pre>
my.Facet = Backbone.Model.extend({
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
  model: my.Facet
});

// ## Object State
//
// Convenience Backbone model for storing (configuration) state of objects like Views.
my.ObjectState = Backbone.Model.extend({
});


// ## Backend registry
//
// Backends will register themselves by id into this registry
my.backends = {};

}(jQuery, this.recline.Model));

/*jshint multistr:true */

var util = function() {
  var templates = {
    transformActions: '<li><a data-action="transform" class="menuAction" href="JavaScript:void(0);">Global transform...</a></li>',
    cellEditor: ' \
      <div class="menu-container data-table-cell-editor"> \
        <textarea class="data-table-cell-editor-editor" bind="textarea">{{value}}</textarea> \
        <div id="data-table-cell-editor-actions"> \
          <div class="data-table-cell-editor-action"> \
            <button class="okButton btn primary">Update</button> \
            <button class="cancelButton btn danger">Cancel</button> \
          </div> \
        </div> \
      </div> \
    ',
    editPreview: ' \
      <div class="expression-preview-table-wrapper"> \
        <table> \
        <thead> \
        <tr> \
          <th class="expression-preview-heading"> \
            before \
          </th> \
          <th class="expression-preview-heading"> \
            after \
          </th> \
        </tr> \
        </thead> \
        <tbody> \
        {{#rows}} \
        <tr> \
          <td class="expression-preview-value"> \
            {{before}} \
          </td> \
          <td class="expression-preview-value"> \
            {{after}} \
          </td> \
        </tr> \
        {{/rows}} \
        </tbody> \
        </table> \
      </div> \
    '
  };

  $.fn.serializeObject = function() {
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
      if (o[this.name]) {
        if (!o[this.name].push) {
          o[this.name] = [o[this.name]];
        }
        o[this.name].push(this.value || '');
      } else {
        o[this.name] = this.value || '';
      }
    });
    return o;
  };

  function registerEmitter() {
    var Emitter = function(obj) {
      this.emit = function(obj, channel) { 
        if (!channel) channel = 'data';
        this.trigger(channel, obj); 
      };
    };
    MicroEvent.mixin(Emitter);
    return new Emitter();
  }
  
  function listenFor(keys) {
    var shortcuts = { // from jquery.hotkeys.js
			8: "backspace", 9: "tab", 13: "return", 16: "shift", 17: "ctrl", 18: "alt", 19: "pause",
			20: "capslock", 27: "esc", 32: "space", 33: "pageup", 34: "pagedown", 35: "end", 36: "home",
			37: "left", 38: "up", 39: "right", 40: "down", 45: "insert", 46: "del", 
			96: "0", 97: "1", 98: "2", 99: "3", 100: "4", 101: "5", 102: "6", 103: "7",
			104: "8", 105: "9", 106: "*", 107: "+", 109: "-", 110: ".", 111 : "/", 
			112: "f1", 113: "f2", 114: "f3", 115: "f4", 116: "f5", 117: "f6", 118: "f7", 119: "f8", 
			120: "f9", 121: "f10", 122: "f11", 123: "f12", 144: "numlock", 145: "scroll", 191: "/", 224: "meta"
		};
    window.addEventListener("keyup", function(e) { 
      var pressed = shortcuts[e.keyCode];
      if(_.include(keys, pressed)) app.emitter.emit("keyup", pressed); 
    }, false);
  }
  
  function observeExit(elem, callback) {
    var cancelButton = elem.find('.cancelButton');
    // TODO: remove (commented out as part of Backbon-i-fication
    // app.emitter.on('esc', function() { 
    //  cancelButton.click();
    //  app.emitter.clear('esc');
    // });
    cancelButton.click(callback);
  }
  
  function show( thing ) {
    $('.' + thing ).show();
    $('.' + thing + '-overlay').show();
  }

  function hide( thing ) {
    $('.' + thing ).hide();
    $('.' + thing + '-overlay').hide();
    // TODO: remove or replace (commented out as part of Backbon-i-fication
    // if (thing === "dialog") app.emitter.clear('esc'); // todo more elegant solution
  }
  
  function position( thing, elem, offset ) {
    var position = $(elem.target).position();
    if (offset) {
      if (offset.top) position.top += offset.top;
      if (offset.left) position.left += offset.left;
    }
    $('.' + thing + '-overlay').show().click(function(e) {
      $(e.target).hide();
      $('.' + thing).hide();
    });
    $('.' + thing).show().css({top: position.top + $(elem.target).height(), left: position.left});
  }

  function render( template, target, options ) {
    if ( !options ) options = {data: {}};
    if ( !options.data ) options = {data: options};
    var html = $.mustache( templates[template], options.data );
    var targetDom = null;
    if (target instanceof jQuery) {
      targetDom = target;
    } else {
      targetDom = $( "." + target + ":first" );      
    }
    if( options.append ) {
      targetDom.append( html );
    } else {
      targetDom.html( html );
    }
    // TODO: remove (commented out as part of Backbon-i-fication
    // if (template in app.after) app.after[template]();
  }

  return {
    registerEmitter: registerEmitter,
    listenFor: listenFor,
    show: show,
    hide: hide,
    position: position,
    render: render,
    observeExit: observeExit
  };
}();
/*jshint multistr:true */

this.recline = this.recline || {};
this.recline.View = this.recline.View || {};

(function($, my) {

// ## Graph view for a Dataset using Flot graphing library.
//
// Initialization arguments (in a hash in first parameter):
//
// * model: recline.Model.Dataset
// * state: (optional) configuration hash of form:
//
//        { 
//          group: {column name for x-axis},
//          series: [{column name for series A}, {column name series B}, ... ],
//          graphType: 'line'
//        }
//
// NB: should *not* provide an el argument to the view but must let the view
// generate the element itself (you can then append view.el to the DOM.
my.Graph = Backbone.View.extend({

  tagName:  "div",
  className: "recline-graph",

  template: ' \
  <div class="editor"> \
    <div class="editor-info editor-hide-info"> \
      <h3 class="action-toggle-help">Help &raquo;</h3> \
      <p>To create a chart select a column (group) to use as the x-axis \
         then another column (Series A) to plot against it.</p> \
      <p>You can add add \
         additional series by clicking the "Add series" button</p> \
    </div> \
    <form class="form-stacked"> \
      <div class="clearfix"> \
        <label>Graph Type</label> \
        <div class="input editor-type"> \
          <select> \
          <option value="lines-and-points">Lines and Points</option> \
          <option value="lines">Lines</option> \
          <option value="points">Points</option> \
          <option value="bars">Bars</option> \
          </select> \
        </div> \
        <label>Group Column (x-axis)</label> \
        <div class="input editor-group"> \
          <select> \
          <option value="">Please choose ...</option> \
          {{#fields}} \
          <option value="{{id}}">{{label}}</option> \
          {{/fields}} \
          </select> \
        </div> \
        <div class="editor-series-group"> \
        </div> \
      </div> \
      <div class="editor-buttons"> \
        <button class="btn editor-add">Add Series</button> \
      </div> \
      <div class="editor-buttons editor-submit" comment="hidden temporarily" style="display: none;"> \
        <button class="editor-save">Save</button> \
        <input type="hidden" class="editor-id" value="chart-1" /> \
      </div> \
    </form> \
  </div> \
  <div class="panel graph"> \
    <div class="js-temp-notice alert alert-block"> \
      <h3 class="alert-heading">Hey there!</h3> \
      <p>There\'s no graph here yet because we don\'t know what fields you\'d like to see plotted.</p> \
      <p>Please tell us by <strong>using the menu on the right</strong> and a graph will automatically appear.</p> \
    </div> \
  </div> \
</div> \
',
  templateSeriesEditor: ' \
    <div class="editor-series js-series-{{seriesIndex}}"> \
      <label>Series <span>{{seriesName}} (y-axis)</span> \
        [<a href="#remove" class="action-remove-series">Remove</a>] \
      </label> \
      <div class="input"> \
        <select> \
        <option value="">Please choose ...</option> \
        {{#fields}} \
        <option value="{{id}}">{{label}}</option> \
        {{/fields}} \
        </select> \
      </div> \
    </div> \
  ',

  events: {
    'change form select': 'onEditorSubmit',
    'click .editor-add': '_onAddSeries',
    'click .action-remove-series': 'removeSeries',
    'click .action-toggle-help': 'toggleHelp'
  },

  initialize: function(options) {
    var self = this;
    this.el = $(this.el);
    _.bindAll(this, 'render', 'redraw');
    // we need the model.fields to render properly
    this.model.bind('change', this.render);
    this.model.fields.bind('reset', this.render);
    this.model.fields.bind('add', this.render);
    this.model.currentDocuments.bind('add', this.redraw);
    this.model.currentDocuments.bind('reset', this.redraw);
    var stateData = _.extend({
        group: null,
        // so that at least one series chooser box shows up
        series: [""],
        graphType: 'lines-and-points'
      },
      options.state
    );
    this.state = new recline.Model.ObjectState(stateData);
    this.render();
  },

  render: function() {
    var self = this;
    var tmplData = this.model.toTemplateJSON();
    var htmls = $.mustache(this.template, tmplData);
    $(this.el).html(htmls);
    this.$graph = this.el.find('.panel.graph');

    // set up editor from state
    if (this.state.get('graphType')) {
      this._selectOption('.editor-type', this.state.get('graphType'));
    }
    if (this.state.get('group')) {
      this._selectOption('.editor-group', this.state.get('group'));
    }
    _.each(this.state.get('series'), function(series, idx) {
      self.addSeries(idx);
      self._selectOption('.editor-series.js-series-' + idx, series);
    });
    return this;
  },

  // Private: Helper function to select an option from a select list
  //
  _selectOption: function(id,value){
    var options = this.el.find(id + ' select > option');
    if (options) {
      options.each(function(opt){
        if (this.value == value) {
          $(this).attr('selected','selected');
          return false;
        }
      });
    }
  },

  onEditorSubmit: function(e) {
    var select = this.el.find('.editor-group select');
    var $editor = this;
    var $series  = this.el.find('.editor-series select');
    var series = $series.map(function () {
      return $(this).val();
    });
    var updatedState = {
      series: $.makeArray(series),
      group: this.el.find('.editor-group select').val(),
      graphType: this.el.find('.editor-type select').val()
    };
    this.state.set(updatedState);
    this.redraw();
  },

  redraw: function() {
    // There appear to be issues generating a Flot graph if either:

    // * The relevant div that graph attaches to his hidden at the moment of creating the plot -- Flot will complain with
    //
    //   Uncaught Invalid dimensions for plot, width = 0, height = 0
    // * There is no data for the plot -- either same error or may have issues later with errors like 'non-existent node-value' 
    var areWeVisible = !jQuery.expr.filters.hidden(this.el[0]);
    if ((!areWeVisible || this.model.currentDocuments.length === 0)) {
      return;
    }
    var series = this.createSeries();
    var options = this.getGraphOptions(this.state.attributes.graphType);
    this.plot = $.plot(this.$graph, series, options);
    this.setupTooltips();
    // create this.plot and cache it
//    if (!this.plot) {
//      this.plot = $.plot(this.$graph, series, options);
//    } else {
//      this.plot.parseOptions(options);
//      this.plot.setData(this.createSeries());
//      this.plot.resize();
//      this.plot.setupGrid();
//      this.plot.draw();
//    }
  },

  // ### getGraphOptions
  //
  // Get options for Flot Graph
  //
  // needs to be function as can depend on state
  //
  // @param typeId graphType id (lines, lines-and-points etc)
  getGraphOptions: function(typeId) { 
    var self = this;
    // special tickformatter to show labels rather than numbers
    // TODO: we should really use tickFormatter and 1 interval ticks if (and
    // only if) x-axis values are non-numeric
    // However, that is non-trivial to work out from a dataset (datasets may
    // have no field type info). Thus at present we only do this for bars.
    var tickFormatter = function (val) {
      if (self.model.currentDocuments.models[val]) {
        var out = self.model.currentDocuments.models[val].get(self.state.attributes.group);
        // if the value was in fact a number we want that not the 
        if (typeof(out) == 'number') {
          return val;
        } else {
          return out;
        }
      }
      return val;
    };

    var xaxis = {};
    // check for time series on x-axis
    if (this.model.fields.get(this.state.get('group')).get('type') === 'date') {
      xaxis.mode = 'time';
      xaxis.timeformat = '%y-%b';
    }
    var optionsPerGraphType = { 
      lines: {
        series: { 
          lines: { show: true }
        },
        xaxis: xaxis
      },
      points: {
        series: {
          points: { show: true }
        },
        xaxis: xaxis,
        grid: { hoverable: true, clickable: true }
      },
      'lines-and-points': {
        series: {
          points: { show: true },
          lines: { show: true }
        },
        xaxis: xaxis,
        grid: { hoverable: true, clickable: true }
      },
      bars: {
        series: {
          lines: {show: false},
          bars: {
            show: true,
            barWidth: 1,
            align: "center",
            fill: true,
            horizontal: true
          }
        },
        grid: { hoverable: true, clickable: true },
        yaxis: {
          tickSize: 1,
          tickLength: 1,
          tickFormatter: tickFormatter,
          min: -0.5,
          max: self.model.currentDocuments.length - 0.5
        }
      }
    };
    return optionsPerGraphType[typeId];
  },

  setupTooltips: function() {
    var self = this;
    function showTooltip(x, y, contents) {
      $('<div id="flot-tooltip">' + contents + '</div>').css( {
        position: 'absolute',
        display: 'none',
        top: y + 5,
        left: x + 5,
        border: '1px solid #fdd',
        padding: '2px',
        'background-color': '#fee',
        opacity: 0.80
      }).appendTo("body").fadeIn(200);
    }

    var previousPoint = null;
    this.$graph.bind("plothover", function (event, pos, item) {
      if (item) {
        if (previousPoint != item.datapoint) {
          previousPoint = item.datapoint;
          
          $("#flot-tooltip").remove();
          var x = item.datapoint[0];
          var y = item.datapoint[1];
          // convert back from 'index' value on x-axis (e.g. in cases where non-number values)
          if (self.model.currentDocuments.models[x]) {
            x = self.model.currentDocuments.models[x].get(self.state.attributes.group);
          } else {
            x = x.toFixed(2);
          }
          y = y.toFixed(2);
          
          var content = _.template('<%= group %> = <%= x %>, <%= series %> = <%= y %>', {
            group: self.state.attributes.group,
            x: x,
            series: item.series.label,
            y: y
          });
          showTooltip(item.pageX, item.pageY, content);
        }
      }
      else {
        $("#flot-tooltip").remove();
        previousPoint = null;            
      }
    });
  },

  createSeries: function () {
    var self = this;
    var series = [];
    _.each(this.state.attributes.series, function(field) {
      var points = [];
      _.each(self.model.currentDocuments.models, function(doc, index) {
        var xfield = self.model.fields.get(self.state.attributes.group);
        var x = doc.getFieldValue(xfield);
        // time series
        var isDateTime = xfield.get('type') === 'date';
        if (isDateTime) {
          x = new Date(x);
        }
        var yfield = self.model.fields.get(field);
        var y = doc.getFieldValue(yfield);
        if (typeof x === 'string') {
          x = index;
        }
        // horizontal bar chart
        if (self.state.attributes.graphType == 'bars') {
          points.push([y, x]);
        } else {
          points.push([x, y]);
        }
      });
      series.push({data: points, label: field});
    });
    return series;
  },

  // Public: Adds a new empty series select box to the editor.
  //
  // @param [int] idx index of this series in the list of series
  //
  // Returns itself.
  addSeries: function (idx) {
    var data = _.extend({
      seriesIndex: idx,
      seriesName: String.fromCharCode(idx + 64 + 1),
    }, this.model.toTemplateJSON());

    var htmls = $.mustache(this.templateSeriesEditor, data);
    this.el.find('.editor-series-group').append(htmls);
    return this;
  },

  _onAddSeries: function(e) {
    e.preventDefault();
    this.addSeries(this.state.get('series').length);
  },

  // Public: Removes a series list item from the editor.
  //
  // Also updates the labels of the remaining series elements.
  removeSeries: function (e) {
    e.preventDefault();
    var $el = $(e.target);
    $el.parent().parent().remove();
    this.onEditorSubmit();
  },

  toggleHelp: function() {
    this.el.find('.editor-info').toggleClass('editor-hide-info');
  },
});

})(jQuery, recline.View);

/*jshint multistr:true */

this.recline = this.recline || {};
this.recline.View = this.recline.View || {};

(function($, my) {
// ## (Data) Grid Dataset View
//
// Provides a tabular view on a Dataset.
//
// Initialize it with a `recline.Model.Dataset`.
my.Grid = Backbone.View.extend({
  tagName:  "div",
  className: "recline-grid-container",

  initialize: function(modelEtc) {
    var self = this;
    this.el = $(this.el);
    _.bindAll(this, 'render');
    this.model.currentDocuments.bind('add', this.render);
    this.model.currentDocuments.bind('reset', this.render);
    this.model.currentDocuments.bind('remove', this.render);
    this.tempState = {};
    var state = _.extend({
        hiddenFields: []
      }, modelEtc.state
    ); 
    this.state = new recline.Model.ObjectState(state);
  },

  events: {
    'click .column-header-menu .data-table-menu li a': 'onColumnHeaderClick',
    'click .row-header-menu': 'onRowHeaderClick',
    'click .root-header-menu': 'onRootHeaderClick',
    'click .data-table-menu li a': 'onMenuClick'
  },

  // TODO: delete or re-enable (currently this code is not used from anywhere except deprecated or disabled methods (see above)).
  // showDialog: function(template, data) {
  //   if (!data) data = {};
  //   util.show('dialog');
  //   util.render(template, 'dialog-content', data);
  //   util.observeExit($('.dialog-content'), function() {
  //     util.hide('dialog');
  //   })
  //   $('.dialog').draggable({ handle: '.dialog-header', cursor: 'move' });
  // },


  // ======================================================
  // Column and row menus

  onColumnHeaderClick: function(e) {
    this.tempState.currentColumn = $(e.target).closest('.column-header').attr('data-field');
  },

  onRowHeaderClick: function(e) {
    this.tempState.currentRow = $(e.target).parents('tr:first').attr('data-id');
  },
  
  onRootHeaderClick: function(e) {
    var tmpl = ' \
        {{#columns}} \
        <li><a data-action="showColumn" data-column="{{.}}" href="JavaScript:void(0);">Show column: {{.}}</a></li> \
        {{/columns}}';
    var tmp = $.mustache(tmpl, {'columns': this.state.get('hiddenFields')});
    this.el.find('.root-header-menu .dropdown-menu').html(tmp);
  },

  onMenuClick: function(e) {
    var self = this;
    e.preventDefault();
    var actions = {
      bulkEdit: function() { self.showTransformColumnDialog('bulkEdit', {name: self.tempState.currentColumn}); },
      facet: function() { 
        self.model.queryState.addFacet(self.tempState.currentColumn);
      },
      facet_histogram: function() {
        self.model.queryState.addHistogramFacet(self.tempState.currentColumn);
      },
      filter: function() {
        self.model.queryState.addTermFilter(self.tempState.currentColumn, '');
      },
      transform: function() { self.showTransformDialog('transform'); },
      sortAsc: function() { self.setColumnSort('asc'); },
      sortDesc: function() { self.setColumnSort('desc'); },
      hideColumn: function() { self.hideColumn(); },
      showColumn: function() { self.showColumn(e); },
      deleteRow: function() {
        var doc = _.find(self.model.currentDocuments.models, function(doc) {
          // important this is == as the currentRow will be string (as comes
          // from DOM) while id may be int
          return doc.id == self.tempState.currentRow;
        });
        doc.destroy().then(function() { 
            self.model.currentDocuments.remove(doc);
            my.notify("Row deleted successfully");
          }).fail(function(err) {
            my.notify("Errorz! " + err);
          });
      }
    };
    actions[$(e.target).attr('data-action')]();
  },

  showTransformColumnDialog: function() {
    var $el = $('.dialog-content');
    util.show('dialog');
    var view = new my.ColumnTransform({
      model: this.model
    });
    view.state = this.tempState;
    view.render();
    $el.empty();
    $el.append(view.el);
    util.observeExit($el, function() {
      util.hide('dialog');
    });
    $('.dialog').draggable({ handle: '.dialog-header', cursor: 'move' });
  },

  showTransformDialog: function() {
    var $el = $('.dialog-content');
    util.show('dialog');
    var view = new recline.View.DataTransform({
    });
    view.render();
    $el.empty();
    $el.append(view.el);
    util.observeExit($el, function() {
      util.hide('dialog');
    });
    $('.dialog').draggable({ handle: '.dialog-header', cursor: 'move' });
  },

  setColumnSort: function(order) {
    var sort = [{}];
    sort[0][this.tempState.currentColumn] = {order: order};
    this.model.query({sort: sort});
  },
  
  hideColumn: function() {
    var hiddenFields = this.state.get('hiddenFields');
    hiddenFields.push(this.tempState.currentColumn);
    this.state.set({hiddenFields: hiddenFields});
    // change event not being triggered (because it is an array?) so trigger manually
    this.state.trigger('change');
    this.render();
  },
  
  showColumn: function(e) {
    var hiddenFields = _.without(this.state.get('hiddenFields'), $(e.target).data('column'));
    this.state.set({hiddenFields: hiddenFields});
    this.render();
  },

  // ======================================================
  // #### Templating
  template: ' \
    <table class="recline-grid table-striped table-condensed" cellspacing="0"> \
      <thead> \
        <tr> \
          {{#notEmpty}} \
            <th class="column-header"> \
              <div class="btn-group root-header-menu"> \
                <a class="btn dropdown-toggle" data-toggle="dropdown"><span class="caret"></span></a> \
                <ul class="dropdown-menu data-table-menu"> \
                </ul> \
              </div> \
              <span class="column-header-name"></span> \
            </th> \
          {{/notEmpty}} \
          {{#fields}} \
            <th class="column-header {{#hidden}}hidden{{/hidden}}" data-field="{{id}}"> \
              <div class="btn-group column-header-menu"> \
                <a class="btn dropdown-toggle" data-toggle="dropdown"><i class="icon-cog"></i><span class="caret"></span></a> \
                <ul class="dropdown-menu data-table-menu pull-right"> \
                  <li><a data-action="facet" href="JavaScript:void(0);">Term Facet</a></li> \
                  <li><a data-action="facet_histogram" href="JavaScript:void(0);">Date Histogram Facet</a></li> \
                  <li><a data-action="filter" href="JavaScript:void(0);">Text Filter</a></li> \
                  <li class="divider"></li> \
                  <li><a data-action="sortAsc" href="JavaScript:void(0);">Sort ascending</a></li> \
                  <li><a data-action="sortDesc" href="JavaScript:void(0);">Sort descending</a></li> \
                  <li class="divider"></li> \
                  <li><a data-action="hideColumn" href="JavaScript:void(0);">Hide this column</a></li> \
                  <li class="divider"></li> \
                  <li class="write-op"><a data-action="bulkEdit" href="JavaScript:void(0);">Transform...</a></li> \
                </ul> \
              </div> \
              <span class="column-header-name">{{label}}</span> \
            </th> \
          {{/fields}} \
        </tr> \
      </thead> \
      <tbody></tbody> \
    </table> \
  ',

  toTemplateJSON: function() {
    var modelData = this.model.toJSON();
    modelData.notEmpty = ( this.fields.length > 0 );
    // TODO: move this sort of thing into a toTemplateJSON method on Dataset?
    modelData.fields = _.map(this.fields, function(field) { return field.toJSON(); });
    return modelData;
  },
  render: function() {
    var self = this;
    this.fields = this.model.fields.filter(function(field) {
      return _.indexOf(self.state.get('hiddenFields'), field.id) == -1;
    });
    var htmls = $.mustache(this.template, this.toTemplateJSON());
    this.el.html(htmls);
    this.model.currentDocuments.forEach(function(doc) {
      var tr = $('<tr />');
      self.el.find('tbody').append(tr);
      var newView = new my.GridRow({
          model: doc,
          el: tr,
          fields: self.fields
        });
      newView.render();
    });
    this.el.toggleClass('no-hidden', (self.state.get('hiddenFields').length === 0));
    return this;
  }
});

// ## GridRow View for rendering an individual document.
//
// Since we want this to update in place it is up to creator to provider the element to attach to.
//
// In addition you *must* pass in a FieldList in the constructor options. This should be list of fields for the Grid.
//
// Example:
//
// <pre>
// var row = new GridRow({
//   model: dataset-document,
//     el: dom-element,
//     fields: mydatasets.fields // a FieldList object
//   });
// </pre>
my.GridRow = Backbone.View.extend({
  initialize: function(initData) {
    _.bindAll(this, 'render');
    this._fields = initData.fields;
    this.el = $(this.el);
    this.model.bind('change', this.render);
  },

  template: ' \
      <td> \
        <div class="btn-group row-header-menu"> \
          <a class="btn dropdown-toggle" data-toggle="dropdown"><span class="caret"></span></a> \
          <ul class="dropdown-menu data-table-menu"> \
            <li class="write-op"><a data-action="deleteRow" href="JavaScript:void(0);">Delete this row</a></li> \
          </ul> \
        </div> \
      </td> \
      {{#cells}} \
      <td data-field="{{field}}"> \
        <div class="data-table-cell-content"> \
          <a href="javascript:{}" class="data-table-cell-edit" title="Edit this cell">&nbsp;</a> \
          <div class="data-table-cell-value">{{{value}}}</div> \
        </div> \
      </td> \
      {{/cells}} \
    ',
  events: {
    'click .data-table-cell-edit': 'onEditClick',
    'click .data-table-cell-editor .okButton': 'onEditorOK',
    'click .data-table-cell-editor .cancelButton': 'onEditorCancel'
  },
  
  toTemplateJSON: function() {
    var self = this;
    var doc = this.model;
    var cellData = this._fields.map(function(field) {
      return {
        field: field.id,
        value: doc.getFieldValue(field)
      };
    });
    return { id: this.id, cells: cellData };
  },

  render: function() {
    this.el.attr('data-id', this.model.id);
    var html = $.mustache(this.template, this.toTemplateJSON());
    $(this.el).html(html);
    return this;
  },

  // ===================
  // Cell Editor methods
  onEditClick: function(e) {
    var editing = this.el.find('.data-table-cell-editor-editor');
    if (editing.length > 0) {
      editing.parents('.data-table-cell-value').html(editing.text()).siblings('.data-table-cell-edit').removeClass("hidden");
    }
    $(e.target).addClass("hidden");
    var cell = $(e.target).siblings('.data-table-cell-value');
    cell.data("previousContents", cell.text());
    util.render('cellEditor', cell, {value: cell.text()});
  },

  onEditorOK: function(e) {
    var cell = $(e.target);
    var rowId = cell.parents('tr').attr('data-id');
    var field = cell.parents('td').attr('data-field');
    var newValue = cell.parents('.data-table-cell-editor').find('.data-table-cell-editor-editor').val();
    var newData = {};
    newData[field] = newValue;
    this.model.set(newData);
    my.notify("Updating row...", {loader: true});
    this.model.save().then(function(response) {
        my.notify("Row updated successfully", {category: 'success'});
      })
      .fail(function() {
        my.notify('Error saving row', {
          category: 'error',
          persist: true
        });
      });
  },

  onEditorCancel: function(e) {
    var cell = $(e.target).parents('.data-table-cell-value');
    cell.html(cell.data('previousContents')).siblings('.data-table-cell-edit').removeClass("hidden");
  }
});

})(jQuery, recline.View);
/*jshint multistr:true */

this.recline = this.recline || {};
this.recline.View = this.recline.View || {};

(function($, my) {

// ## Map view for a Dataset using Leaflet mapping library.
//
// This view allows to plot gereferenced documents on a map. The location
// information can be provided either via a field with
// [GeoJSON](http://geojson.org) objects or two fields with latitude and
// longitude coordinates.
//
// Initialization arguments are as standard for Dataset Views. State object may
// have the following (optional) configuration options:
//
// <pre>
//   {
//     // geomField if specified will be used in preference to lat/lon
//     geomField: {id of field containing geometry in the dataset}
//     lonField: {id of field containing longitude in the dataset}
//     latField: {id of field containing latitude in the dataset}
//   }
// </pre>
my.Map = Backbone.View.extend({

  tagName:  'div',
  className: 'recline-map',

  template: ' \
  <div class="editor"> \
    <form class="form-stacked"> \
      <div class="clearfix"> \
        <div class="editor-field-type"> \
            <label class="radio"> \
              <input type="radio" id="editor-field-type-latlon" name="editor-field-type" value="latlon" checked="checked"/> \
              Latitude / Longitude fields</label> \
            <label class="radio"> \
              <input type="radio" id="editor-field-type-geom" name="editor-field-type" value="geom" /> \
              GeoJSON field</label> \
        </div> \
        <div class="editor-field-type-latlon"> \
          <label>Latitude field</label> \
          <div class="input editor-lat-field"> \
            <select> \
            <option value=""></option> \
            {{#fields}} \
            <option value="{{id}}">{{label}}</option> \
            {{/fields}} \
            </select> \
          </div> \
          <label>Longitude field</label> \
          <div class="input editor-lon-field"> \
            <select> \
            <option value=""></option> \
            {{#fields}} \
            <option value="{{id}}">{{label}}</option> \
            {{/fields}} \
            </select> \
          </div> \
        </div> \
        <div class="editor-field-type-geom" style="display:none"> \
          <label>Geometry field (GeoJSON)</label> \
          <div class="input editor-geom-field"> \
            <select> \
            <option value=""></option> \
            {{#fields}} \
            <option value="{{id}}">{{label}}</option> \
            {{/fields}} \
            </select> \
          </div> \
        </div> \
      </div> \
      <div class="editor-buttons"> \
        <button class="btn editor-update-map">Update</button> \
      </div> \
      <div class="editor-options" > \
        <label class="checkbox"> \
          <input type="checkbox" id="editor-auto-zoom" checked="checked" /> \
          Auto zoom to features</label> \
      </div> \
      <input type="hidden" class="editor-id" value="map-1" /> \
      </div> \
    </form> \
  </div> \
<div class="panel map"> \
</div> \
',

  // These are the default field names that will be used if found.
  // If not found, the user will need to define the fields via the editor.
  latitudeFieldNames: ['lat','latitude'],
  longitudeFieldNames: ['lon','longitude'],
  geometryFieldNames: ['geom','the_geom','geometry','spatial','location'],

  // Define here events for UI elements
  events: {
    'click .editor-update-map': 'onEditorSubmit',
    'change .editor-field-type': 'onFieldTypeChange',
    'change #editor-auto-zoom': 'onAutoZoomChange'
  },

  initialize: function(options) {
    var self = this;
    this.el = $(this.el);

    // Listen to changes in the fields
    this.model.fields.bind('change', function() {
      self._setupGeometryField();
    });
    this.model.fields.bind('add', this.render);
    this.model.fields.bind('reset', function(){
      self._setupGeometryField()
      self.render()
    });

    // Listen to changes in the documents
    this.model.currentDocuments.bind('add', function(doc){self.redraw('add',doc)});
    this.model.currentDocuments.bind('change', function(doc){
        self.redraw('remove',doc);
        self.redraw('add',doc);
    });
    this.model.currentDocuments.bind('remove', function(doc){self.redraw('remove',doc)});
    this.model.currentDocuments.bind('reset', function(){self.redraw('reset')});

    this.bind('view:show',function(){
      // If the div was hidden, Leaflet needs to recalculate some sizes
      // to display properly
      if (self.map){
        self.map.invalidateSize();
        if (self._zoomPending && self.autoZoom) {
          self._zoomToFeatures();
          self._zoomPending = false;
        }
      }
      self.visible = true;
    });
    this.bind('view:hide',function(){
      self.visible = false;
    });

    var stateData = _.extend({
        geomField: null,
        lonField: null,
        latField: null
      },
      options.state
    );
    this.state = new recline.Model.ObjectState(stateData);

    this.autoZoom = true;
    this.mapReady = false;
    this.render();
  },

  // Public: Adds the necessary elements to the page.
  //
  // Also sets up the editor fields and the map if necessary.
  render: function() {

    var self = this;

    htmls = $.mustache(this.template, this.model.toTemplateJSON());

    $(this.el).html(htmls);
    this.$map = this.el.find('.panel.map');

    if (this.geomReady && this.model.fields.length){
      if (this.state.get('geomField')){
        this._selectOption('editor-geom-field',this.state.get('geomField'));
        $('#editor-field-type-geom').attr('checked','checked').change();
      } else{
        this._selectOption('editor-lon-field',this.state.get('lonField'));
        this._selectOption('editor-lat-field',this.state.get('latField'));
        $('#editor-field-type-latlon').attr('checked','checked').change();
      }
    }

    this.model.bind('query:done', function() {
      if (!self.geomReady){
        self._setupGeometryField();
      }

      if (!self.mapReady){
        self._setupMap();
      }
      self.redraw();
    });

    return this;
  },

  // Public: Redraws the features on the map according to the action provided
  //
  // Actions can be:
  //
  // * reset: Clear all features
  // * add: Add one or n features (documents)
  // * remove: Remove one or n features (documents)
  // * refresh: Clear existing features and add all current documents
  //
  redraw: function(action,doc){
    var self = this;
    action = action || 'refresh';

    if (this.geomReady && this.mapReady){
      if (action == 'reset'){
        this.features.clearLayers();
      } else if (action == 'add' && doc){
        this._add(doc);
      } else if (action == 'remove' && doc){
        this._remove(doc);
      } else if (action == 'refresh'){
        this.features.clearLayers();
        this._add(this.model.currentDocuments.models);
      }
      if (action != 'reset' && this.autoZoom){
        if (this.visible){
          this._zoomToFeatures();
        } else {
          this._zoomPending = true;
        }
      }
    }
  },

  //
  // UI Event handlers
  //

  // Public: Update map with user options
  //
  // Right now the only configurable option is what field(s) contains the
  // location information.
  //
  onEditorSubmit: function(e){
    e.preventDefault();
    if ($('#editor-field-type-geom').attr('checked')){
      this.state.set({
        geomField: $('.editor-geom-field > select > option:selected').val(),
        lonField: null,
        latField: null
      });
    } else {
      this.state.set({
        geomField: null,
        lonField: $('.editor-lon-field > select > option:selected').val(),
        latField: $('.editor-lat-field > select > option:selected').val()
      });
    }
    this.geomReady = (this.state.get('geomField') || (this.state.get('latField') && this.state.get('lonField')));
    this.redraw();

    return false;
  },

  // Public: Shows the relevant select lists depending on the location field
  // type selected.
  //
  onFieldTypeChange: function(e){
    if (e.target.value == 'geom'){
        $('.editor-field-type-geom').show();
        $('.editor-field-type-latlon').hide();
    } else {
        $('.editor-field-type-geom').hide();
        $('.editor-field-type-latlon').show();
    }
  },

  onAutoZoomChange: function(e){
    this.autoZoom = !this.autoZoom;
  },

  // Private: Add one or n features to the map
  //
  // For each document passed, a GeoJSON geometry will be extracted and added
  // to the features layer. If an exception is thrown, the process will be
  // stopped and an error notification shown.
  //
  // Each feature will have a popup associated with all the document fields.
  //
  _add: function(docs){

    var self = this;

    if (!(docs instanceof Array)) docs = [docs];

    var count = 0;
    var wrongSoFar = 0;
    _.every(docs,function(doc){
      count += 1;
      var feature = self._getGeometryFromDocument(doc);
      if (typeof feature === 'undefined' || feature === null){
        // Empty field
        return true;
      } else if (feature instanceof Object){
        // Build popup contents
        // TODO: mustache?
        html = ''
        for (key in doc.attributes){
          if (!(self.state.get('geomField') && key == self.state.get('geomField'))){
            html += '<div><strong>' + key + '</strong>: '+ doc.attributes[key] + '</div>';
          }
        }
        feature.properties = {popupContent: html};

        // Add a reference to the model id, which will allow us to
        // link this Leaflet layer to a Recline doc
        feature.properties.cid = doc.cid;

        try {
          self.features.addGeoJSON(feature);
        } catch (except) {
          wrongSoFar += 1;
          var msg = 'Wrong geometry value';
          if (except.message) msg += ' (' + except.message + ')';
          if (wrongSoFar <= 10) {
            my.notify(msg,{category:'error'});
          }
        }
      } else {
        wrongSoFar += 1
        if (wrongSoFar <= 10) {
          my.notify('Wrong geometry value',{category:'error'});
        }
      }
      return true;
    });
  },

  // Private: Remove one or n features to the map
  //
  _remove: function(docs){

    var self = this;

    if (!(docs instanceof Array)) docs = [docs];

    _.each(docs,function(doc){
      for (key in self.features._layers){
        if (self.features._layers[key].cid == doc.cid){
          self.features.removeLayer(self.features._layers[key]);
        }
      }
    });

  },

  // Private: Return a GeoJSON geomtry extracted from the document fields
  //
  _getGeometryFromDocument: function(doc){
    if (this.geomReady){
      if (this.state.get('geomField')){
        var value = doc.get(this.state.get('geomField'));
        if (typeof(value) === 'string'){
          // We have a GeoJSON string representation
          return $.parseJSON(value);
        } else {
          // We assume that the contents of the field are a valid GeoJSON object
          return value;
        }
      } else if (this.state.get('lonField') && this.state.get('latField')){
        // We'll create a GeoJSON like point object from the two lat/lon fields
        var lon = doc.get(this.state.get('lonField'));
        var lat = doc.get(this.state.get('latField'));
        if (!isNaN(parseFloat(lon)) && !isNaN(parseFloat(lat))) {
          return {
            type: 'Point',
            coordinates: [lon,lat]
          };
        }
      }
      return null;
    }
  },

  // Private: Check if there is a field with GeoJSON geometries or alternatively,
  // two fields with lat/lon values.
  //
  // If not found, the user can define them via the UI form.
  _setupGeometryField: function(){
    var geomField, latField, lonField;
    this.geomReady = (this.state.get('geomField') || (this.state.get('latField') && this.state.get('lonField')));
    // should not overwrite if we have already set this (e.g. explicitly via state)
    if (!this.geomReady) {
      this.state.set({
        geomField: this._checkField(this.geometryFieldNames),
        latField: this._checkField(this.latitudeFieldNames),
        lonField: this._checkField(this.longitudeFieldNames)
      });
      this.geomReady = (this.state.get('geomField') || (this.state.get('latField') && this.state.get('lonField')));
    }
  },

  // Private: Check if a field in the current model exists in the provided
  // list of names.
  //
  //
  _checkField: function(fieldNames){
    var field;
    var modelFieldNames = this.model.fields.pluck('id');
    for (var i = 0; i < fieldNames.length; i++){
      for (var j = 0; j < modelFieldNames.length; j++){
        if (modelFieldNames[j].toLowerCase() == fieldNames[i].toLowerCase())
          return modelFieldNames[j];
      }
    }
    return null;
  },

  // Private: Zoom to map to current features extent if any, or to the full
  // extent if none.
  //
  _zoomToFeatures: function(){
    var bounds = this.features.getBounds();
    if (bounds){
      this.map.fitBounds(bounds);
    } else {
      this.map.setView(new L.LatLng(0, 0), 2);
    }
  },

  // Private: Sets up the Leaflet map control and the features layer.
  //
  // The map uses a base layer from [MapQuest](http://www.mapquest.com) based
  // on [OpenStreetMap](http://openstreetmap.org).
  //
  _setupMap: function(){

    this.map = new L.Map(this.$map.get(0));

    var mapUrl = "http://otile{s}.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png";
    var osmAttribution = 'Map data &copy; 2011 OpenStreetMap contributors, Tiles Courtesy of <a href="http://www.mapquest.com/" target="_blank">MapQuest</a> <img src="http://developer.mapquest.com/content/osm/mq_logo.png">';
    var bg = new L.TileLayer(mapUrl, {maxZoom: 18, attribution: osmAttribution ,subdomains: '1234'});
    this.map.addLayer(bg);

    this.features = new L.GeoJSON();
    this.features.on('featureparse', function (e) {
      if (e.properties && e.properties.popupContent){
        e.layer.bindPopup(e.properties.popupContent);
       }
      if (e.properties && e.properties.cid){
        e.layer.cid = e.properties.cid;
       }

    });

    // This will be available in the next Leaflet stable release.
    // In the meantime we add it manually to our layer.
    this.features.getBounds = function(){
      var bounds = new L.LatLngBounds();
      this._iterateLayers(function (layer) {
        if (layer instanceof L.Marker){
          bounds.extend(layer.getLatLng());
        } else {
          if (layer.getBounds){
            bounds.extend(layer.getBounds().getNorthEast());
            bounds.extend(layer.getBounds().getSouthWest());
          }
        }
      }, this);
      return (typeof bounds.getNorthEast() !== 'undefined') ? bounds : null;
    }

    this.map.addLayer(this.features);

    this.map.setView(new L.LatLng(0, 0), 2);

    this.mapReady = true;
  },

  // Private: Helper function to select an option from a select list
  //
  _selectOption: function(id,value){
    var options = $('.' + id + ' > select > option');
    if (options){
      options.each(function(opt){
        if (this.value == value) {
          $(this).attr('selected','selected');
          return false;
        }
      });
    }
  }

 });

})(jQuery, recline.View);

/*jshint multistr:true */

this.recline = this.recline || {};
this.recline.View = this.recline.View || {};

// Views module following classic module pattern
(function($, my) {

// View (Dialog) for doing data transformations on whole dataset.
my.DataTransform = Backbone.View.extend({
  className: 'transform-view',
  template: ' \
    <div class="dialog-header"> \
      Recursive transform on all rows \
    </div> \
    <div class="dialog-body"> \
      <div class="grid-layout layout-full"> \
        <p class="info">Traverse and transform objects by visiting every node on a recursive walk using <a href="https://github.com/substack/js-traverse">js-traverse</a>.</p> \
        <table> \
        <tbody> \
        <tr> \
          <td colspan="4"> \
            <div class="grid-layout layout-tight layout-full"> \
              <table rows="4" cols="4"> \
              <tbody> \
              <tr style="vertical-align: bottom;"> \
                <td colspan="4"> \
                  Expression \
                </td> \
              </tr> \
              <tr> \
                <td colspan="3"> \
                  <div class="input-container"> \
                    <textarea class="expression-preview-code"></textarea> \
                  </div> \
                </td> \
                <td class="expression-preview-parsing-status" width="150" style="vertical-align: top;"> \
                  No syntax error. \
                </td> \
              </tr> \
              <tr> \
                <td colspan="4"> \
                  <div id="expression-preview-tabs" class="refine-tabs ui-tabs ui-widget ui-widget-content ui-corner-all"> \
                    <span>Preview</span> \
                    <div id="expression-preview-tabs-preview" class="ui-tabs-panel ui-widget-content ui-corner-bottom"> \
                      <div class="expression-preview-container" style="width: 652px; "> \
                      </div> \
                    </div> \
                  </div> \
                </td> \
              </tr> \
              </tbody> \
              </table> \
            </div> \
          </td> \
        </tr> \
        </tbody> \
        </table> \
      </div> \
    </div> \
    <div class="dialog-footer"> \
      <button class="okButton button">&nbsp;&nbsp;Update All&nbsp;&nbsp;</button> \
      <button class="cancelButton button">Cancel</button> \
    </div> \
  ',

  initialize: function() {
    this.el = $(this.el);
  },

  render: function() {
    this.el.html(this.template);
  }
});


// View (Dialog) for doing data transformations (on columns of data).
my.ColumnTransform = Backbone.View.extend({
  className: 'transform-column-view',
  template: ' \
    <div class="dialog-header"> \
      Functional transform on column {{name}} \
    </div> \
    <div class="dialog-body"> \
      <div class="grid-layout layout-tight layout-full"> \
        <table> \
        <tbody> \
        <tr> \
          <td colspan="4"> \
            <div class="grid-layout layout-tight layout-full"> \
              <table rows="4" cols="4"> \
              <tbody> \
              <tr style="vertical-align: bottom;"> \
                <td colspan="4"> \
                  Expression \
                </td> \
              </tr> \
              <tr> \
                <td colspan="3"> \
                  <div class="input-container"> \
                    <textarea class="expression-preview-code"></textarea> \
                  </div> \
                </td> \
                <td class="expression-preview-parsing-status" width="150" style="vertical-align: top;"> \
                  No syntax error. \
                </td> \
              </tr> \
              <tr> \
                <td colspan="4"> \
                  <div id="expression-preview-tabs" class="refine-tabs ui-tabs ui-widget ui-widget-content ui-corner-all"> \
                    <span>Preview</span> \
                    <div id="expression-preview-tabs-preview" class="ui-tabs-panel ui-widget-content ui-corner-bottom"> \
                      <div class="expression-preview-container" style="width: 652px; "> \
                      </div> \
                    </div> \
                  </div> \
                </td> \
              </tr> \
              </tbody> \
              </table> \
            </div> \
          </td> \
        </tr> \
        </tbody> \
        </table> \
      </div> \
    </div> \
    <div class="dialog-footer"> \
      <button class="okButton btn primary">&nbsp;&nbsp;Update All&nbsp;&nbsp;</button> \
      <button class="cancelButton btn danger">Cancel</button> \
    </div> \
  ',

  events: {
    'click .okButton': 'onSubmit',
    'keydown .expression-preview-code': 'onEditorKeydown'
  },

  initialize: function() {
    this.el = $(this.el);
  },

  render: function() {
    var htmls = $.mustache(this.template, 
      {name: this.state.currentColumn}
      );
    this.el.html(htmls);
    // Put in the basic (identity) transform script
    // TODO: put this into the template?
    var editor = this.el.find('.expression-preview-code');
    editor.val("function(doc) {\n  doc['"+ this.state.currentColumn+"'] = doc['"+ this.state.currentColumn+"'];\n  return doc;\n}");
    editor.focus().get(0).setSelectionRange(18, 18);
    editor.keydown();
  },

  onSubmit: function(e) {
    var self = this;
    var funcText = this.el.find('.expression-preview-code').val();
    var editFunc = costco.evalFunction(funcText);
    if (editFunc.errorMessage) {
      my.notify("Error with function! " + editFunc.errorMessage);
      return;
    }
    util.hide('dialog');
    my.notify("Updating all visible docs. This could take a while...", {persist: true, loader: true});
      var docs = self.model.currentDocuments.map(function(doc) {
       return doc.toJSON();
      });
    // TODO: notify about failed docs? 
    var toUpdate = costco.mapDocs(docs, editFunc).edited;
    var totalToUpdate = toUpdate.length;
    function onCompletedUpdate() {
      totalToUpdate += -1;
      if (totalToUpdate === 0) {
        my.notify(toUpdate.length + " documents updated successfully");
        alert('WARNING: We have only updated the docs in this view. (Updating of all docs not yet implemented!)');
        self.remove();
      }
    }
    // TODO: Very inefficient as we search through all docs every time!
    _.each(toUpdate, function(editedDoc) {
      var realDoc = self.model.currentDocuments.get(editedDoc.id);
      realDoc.set(editedDoc);
      realDoc.save().then(onCompletedUpdate).fail(onCompletedUpdate);
    });
  },

  onEditorKeydown: function(e) {
    var self = this;
    // if you don't setTimeout it won't grab the latest character if you call e.target.value
    window.setTimeout( function() {
      var errors = self.el.find('.expression-preview-parsing-status');
      var editFunc = costco.evalFunction(e.target.value);
      if (!editFunc.errorMessage) {
        errors.text('No syntax error.');
        var docs = self.model.currentDocuments.map(function(doc) {
          return doc.toJSON();
        });
        var previewData = costco.previewTransform(docs, editFunc, self.state.currentColumn);
        util.render('editPreview', 'expression-preview-container', {rows: previewData});
      } else {
        errors.text(editFunc.errorMessage);
      }
    }, 1, true);
  }
});

})(jQuery, recline.View);
/*jshint multistr:true */

// # Recline Views
//
// Recline Views are Backbone Views and in keeping with normal Backbone views
// are Widgets / Components displaying something in the DOM. Like all Backbone
// views they have a pointer to a model or a collection and is bound to an
// element.
//
// Views provided by core Recline are crudely divided into two types:
//
// * Dataset Views: a View intended for displaying a recline.Model.Dataset
//   in some fashion. Examples are the Grid, Graph and Map views.
// * Widget Views: a widget used for displaying some specific (and
//   smaller) aspect of a dataset or the application. Examples are
//   QueryEditor and FilterEditor which both provide a way for editing (a
//   part of) a `recline.Model.Query` associated to a Dataset.
//
// ## Dataset View
//
// These views are just Backbone views with a few additional conventions:
//
// 1. The model passed to the View should always be a recline.Model.Dataset instance
// 2. Views should generate their own root element rather than having it passed
//    in.
// 3. Views should apply a css class named 'recline-{view-name-lower-cased} to
//    the root element (and for all CSS for this view to be qualified using this
//    CSS class)
// 4. Read-only mode: CSS for this view should respect/utilize
//    recline-read-only class to trigger read-only behaviour (this class will
//    usually be set on some parent element of the view's root element.
// 5. State: state (configuration) information for the view should be stored on
//    an attribute named state that is an instance of a Backbone Model (or, more
//    speficially, be an instance of `recline.Model.ObjectState`). In addition,
//    a state attribute may be specified in the Hash passed to a View on
//    iniitialization and this information should be used to set the initial
//    state of the view.
//
//    Example of state would be the set of fields being plotted in a graph
//    view.
//
//    More information about State can be found below.
//
// To summarize some of this, the initialize function for a Dataset View should
// look like:
//
// <pre>
//    initialize: {
//        model: {a recline.Model.Dataset instance}
//        // el: {do not specify - instead view should create}
//        state: {(optional) Object / Hash specifying initial state}
//        ...
//    }
// </pre>
//
// Note: Dataset Views in core Recline have a common layout on disk as
// follows, where ViewName is the named of View class:
//
// <pre>
// src/view-{lower-case-ViewName}.js
// css/{lower-case-ViewName}.css
// test/view-{lower-case-ViewName}.js
// </pre>
//
// ### State
//
// State information exists in order to support state serialization into the
// url or elsewhere and reloading of application from a stored state.
//
// State is available not only for individual views (as described above) but
// for the dataset (e.g. the current query). For an example of pulling together
// state from across multiple components see `recline.View.DataExplorer`.
// 
// ### Writing your own Views
//
// See the existing Views.
//
// ----

// Standard JS module setup
this.recline = this.recline || {};
this.recline.View = this.recline.View || {};

(function($, my) {
// ## DataExplorer
//
// The primary view for the entire application. Usage:
// 
// <pre>
// var myExplorer = new model.recline.DataExplorer({
//   model: {{recline.Model.Dataset instance}}
//   el: {{an existing dom element}}
//   views: {{dataset views}}
//   state: {{state configuration -- see below}}
// });
// </pre> 
//
// ### Parameters
// 
// **model**: (required) recline.model.Dataset instance.
//
// **el**: (required) DOM element to bind to. NB: the element already
// being in the DOM is important for rendering of some subviews (e.g.
// Graph).
//
// **views**: (optional) the dataset views (Grid, Graph etc) for
// DataExplorer to show. This is an array of view hashes. If not provided
// initialize with (recline.View.)Grid, Graph, and Map views (with obvious id
// and labels!).
//
// <pre>
// var views = [
//   {
//     id: 'grid', // used for routing
//     label: 'Grid', // used for view switcher
//     view: new recline.View.Grid({
//       model: dataset
//     })
//   },
//   {
//     id: 'graph',
//     label: 'Graph',
//     view: new recline.View.Graph({
//       model: dataset
//     })
//   }
// ];
// </pre>
//
// **state**: standard state config for this view. This state is slightly
//  special as it includes config of many of the subviews.
//
// <pre>
// state = {
//     query: {dataset query state - see dataset.queryState object}
//     view-{id1}: {view-state for this view}
//     view-{id2}: {view-state for }
//     ...
//     // Explorer
//     currentView: id of current view (defaults to first view if not specified)
//     readOnly: (default: false) run in read-only mode
// }
// </pre>
//
// Note that at present we do *not* serialize information about the actual set
// of views in use -- e.g. those specified by the views argument -- but instead 
// expect either that the default views are fine or that the client to have
// initialized the DataExplorer with the relevant views themselves.
my.DataExplorer = Backbone.View.extend({
  template: ' \
  <div class="recline-data-explorer"> \
    <div class="alert-messages"></div> \
    \
    <div class="header"> \
      <ul class="navigation"> \
        {{#views}} \
        <li><a href="#{{id}}" data-view="{{id}}" class="btn">{{label}}</a> \
        {{/views}} \
      </ul> \
      <div class="recline-results-info"> \
        Results found <span class="doc-count">{{docCount}}</span> \
      </div> \
      <div class="menu-right"> \
        <a href="#" class="btn" data-action="filters">Filters</a> \
        <a href="#" class="btn" data-action="facets">Facets</a> \
      </div> \
      <div class="query-editor-here" style="display:inline;"></div> \
      <div class="clearfix"></div> \
    </div> \
    <div class="data-view-container"></div> \
    <div class="dialog-overlay" style="display: none; z-index: 101; ">&nbsp;</div> \
    <div class="dialog ui-draggable" style="display: none; z-index: 102; top: 101px; "> \
      <div class="dialog-frame" style="width: 700px; visibility: visible; "> \
        <div class="dialog-content dialog-border"></div> \
      </div> \
    </div> \
  </div> \
  ',
  events: {
    'click .menu-right a': '_onMenuClick',
    'click .navigation a': '_onSwitchView'
  },

  initialize: function(options) {
    var self = this;
    this.el = $(this.el);
    this._setupState(options.state);
    // Hash of 'page' views (i.e. those for whole page) keyed by page name
    if (options.views) {
      this.pageViews = options.views;
    } else {
      this.pageViews = [{
        id: 'grid',
        label: 'Grid',
        view: new my.Grid({
          model: this.model,
          state: this.state.get('view-grid')
        }),
      }, {
        id: 'graph',
        label: 'Graph',
        view: new my.Graph({
          model: this.model,
          state: this.state.get('view-graph')
        }),
      }, {
        id: 'map',
        label: 'Map',
        view: new my.Map({
          model: this.model,
          state: this.state.get('view-map')
        }),
      }];
    }
    // these must be called after pageViews are created
    this.render();
    this._bindStateChanges();
    // now do updates based on state (need to come after render)
    if (this.state.get('readOnly')) {
      this.setReadOnly();
    }
    if (this.state.get('currentView')) {
      this.updateNav(this.state.get('currentView'));
    } else {
      this.updateNav(this.pageViews[0].id);
    }

    this.router = new Backbone.Router();
    this.setupRouting();

    this.model.bind('query:start', function() {
        my.notify('Loading data', {loader: true});
      });
    this.model.bind('query:done', function() {
        my.clearNotifications();
        self.el.find('.doc-count').text(self.model.docCount || 'Unknown');
        my.notify('Data loaded', {category: 'success'});
        // update navigation
        var qs = my.parseHashQueryString();
        qs.reclineQuery = JSON.stringify(self.model.queryState.toJSON());
        var out = my.getNewHashForQueryString(qs);
        // self.router.navigate(out);
      });
    this.model.bind('query:fail', function(error) {
        my.clearNotifications();
        var msg = '';
        if (typeof(error) == 'string') {
          msg = error;
        } else if (typeof(error) == 'object') {
          if (error.title) {
            msg = error.title + ': ';
          }
          if (error.message) {
            msg += error.message;
          }
        } else {
          msg = 'There was an error querying the backend';
        }
        my.notify(msg, {category: 'error', persist: true});
      });

    // retrieve basic data like fields etc
    // note this.model and dataset returned are the same
    this.model.fetch()
      .done(function(dataset) {
        self.model.query(self.state.get('query'));
      })
      .fail(function(error) {
        my.notify(error.message, {category: 'error', persist: true});
      });
  },

  setReadOnly: function() {
    this.el.addClass('recline-read-only');
  },

  render: function() {
    var tmplData = this.model.toTemplateJSON();
    tmplData.views = this.pageViews;
    var template = $.mustache(this.template, tmplData);
    $(this.el).html(template);
    var $dataViewContainer = this.el.find('.data-view-container');
    _.each(this.pageViews, function(view, pageName) {
      $dataViewContainer.append(view.view.el);
    });
    var queryEditor = new my.QueryEditor({
      model: this.model.queryState
    });
    this.el.find('.query-editor-here').append(queryEditor.el);
    var filterEditor = new my.FilterEditor({
      model: this.model.queryState
    });
    this.$filterEditor = filterEditor.el;
    this.el.find('.header').append(filterEditor.el);
    var facetViewer = new my.FacetViewer({
      model: this.model
    });
    this.$facetViewer = facetViewer.el;
    this.el.find('.header').append(facetViewer.el);
  },

  setupRouting: function() {
    var self = this;
    // Default route
//    this.router.route(/^(\?.*)?$/, this.pageViews[0].id, function(queryString) {
//      self.updateNav(self.pageViews[0].id, queryString);
//    });
//    $.each(this.pageViews, function(idx, view) {
//      self.router.route(/^([^?]+)(\?.*)?/, 'view', function(viewId, queryString) {
//        self.updateNav(viewId, queryString);
//      });
//    });
    this.router.route(/.*/, 'view', function() {
    });
  },

  updateNav: function(pageName) {
    this.el.find('.navigation li').removeClass('active');
    this.el.find('.navigation li a').removeClass('disabled');
    var $el = this.el.find('.navigation li a[data-view="' + pageName + '"]');
    $el.parent().addClass('active');
    $el.addClass('disabled');
    // show the specific page
    _.each(this.pageViews, function(view, idx) {
      if (view.id === pageName) {
        view.view.el.show();
        view.view.trigger('view:show');
      } else {
        view.view.el.hide();
        view.view.trigger('view:hide');
      }
    });
  },

  _onMenuClick: function(e) {
    e.preventDefault();
    var action = $(e.target).attr('data-action');
    if (action === 'filters') {
      this.$filterEditor.show();
    } else if (action === 'facets') {
      this.$facetViewer.show();
    }
  },

  _onSwitchView: function(e) {
    e.preventDefault();
    var viewName = $(e.target).attr('data-view');
    this.updateNav(viewName);
    this.state.set({currentView: viewName});
  },

  // create a state object for this view and do the job of
  // 
  // a) initializing it from both data passed in and other sources (e.g. hash url)
  //
  // b) ensure the state object is updated in responese to changes in subviews, query etc.
  _setupState: function(initialState) {
    var self = this;
    // get data from the query string / hash url plus some defaults
    var qs = my.parseHashQueryString();
    var query = qs.reclineQuery;
    query = query ? JSON.parse(query) : self.model.queryState.toJSON();
    // backwards compatability (now named view-graph but was named graph)
    var graphState = qs['view-graph'] || qs.graph;
    graphState = graphState ? JSON.parse(graphState) : {};

    // now get default data + hash url plus initial state and initial our state object with it
    var stateData = _.extend({
        query: query,
        'view-graph': graphState,
        backend: this.model.backend.__type__,
        dataset: this.model.toJSON(),
        currentView: null,
        readOnly: false
      },
      initialState);
    this.state = new recline.Model.ObjectState(stateData);
  },

  _bindStateChanges: function() {
    var self = this;
    // finally ensure we update our state object when state of sub-object changes so that state is always up to date
    this.model.queryState.bind('change', function() {
      self.state.set({query: self.model.queryState.toJSON()});
    });
    _.each(this.pageViews, function(pageView) {
      if (pageView.view.state && pageView.view.state.bind) {
        var update = {};
        update['view-' + pageView.id] = pageView.view.state.toJSON();
        self.state.set(update);
        pageView.view.state.bind('change', function() {
          var update = {};
          update['view-' + pageView.id] = pageView.view.state.toJSON();
          // had problems where change not being triggered for e.g. grid view so let's do it explicitly
          self.state.set(update, {silent: true});
          self.state.trigger('change');
        });
      }
    });
  }
});

// ### DataExplorer.restore
//
// Restore a DataExplorer instance from a serialized state including the associated dataset
my.DataExplorer.restore = function(state) {
  var dataset = recline.Model.Dataset.restore(state);
  var explorer = new my.DataExplorer({
    model: dataset,
    state: state
  });
  return explorer;
}

my.QueryEditor = Backbone.View.extend({
  className: 'recline-query-editor', 
  template: ' \
    <form action="" method="GET" class="form-inline"> \
      <div class="input-prepend text-query"> \
        <span class="add-on"><i class="icon-search"></i></span> \
        <input type="text" name="q" value="{{q}}" class="span2" placeholder="Search data ..." class="search-query" /> \
      </div> \
      <div class="pagination"> \
        <ul> \
          <li class="prev action-pagination-update"><a href="">&laquo;</a></li> \
          <li class="active"><a><input name="from" type="text" value="{{from}}" /> &ndash; <input name="to" type="text" value="{{to}}" /> </a></li> \
          <li class="next action-pagination-update"><a href="">&raquo;</a></li> \
        </ul> \
      </div> \
      <button type="submit" class="btn">Go &raquo;</button> \
    </form> \
  ',

  events: {
    'submit form': 'onFormSubmit',
    'click .action-pagination-update': 'onPaginationUpdate'
  },

  initialize: function() {
    _.bindAll(this, 'render');
    this.el = $(this.el);
    this.model.bind('change', this.render);
    this.render();
  },
  onFormSubmit: function(e) {
    e.preventDefault();
    var query = this.el.find('.text-query input').val();
    var newFrom = parseInt(this.el.find('input[name="from"]').val());
    var newSize = parseInt(this.el.find('input[name="to"]').val()) - newFrom;
    this.model.set({size: newSize, from: newFrom, q: query});
  },
  onPaginationUpdate: function(e) {
    e.preventDefault();
    var $el = $(e.target);
    var newFrom = 0;
    if ($el.parent().hasClass('prev')) {
      newFrom = this.model.get('from') - Math.max(0, this.model.get('size'));
    } else {
      newFrom = this.model.get('from') + this.model.get('size');
    }
    this.model.set({from: newFrom});
  },
  render: function() {
    var tmplData = this.model.toJSON();
    tmplData.to = this.model.get('from') + this.model.get('size');
    var templated = $.mustache(this.template, tmplData);
    this.el.html(templated);
  }
});

my.FilterEditor = Backbone.View.extend({
  className: 'recline-filter-editor well', 
  template: ' \
    <a class="close js-hide" href="#">&times;</a> \
    <div class="row filters"> \
      <div class="span1"> \
        <h3>Filters</h3> \
      </div> \
      <div class="span11"> \
        <form class="form-horizontal"> \
          <div class="row"> \
            <div class="span6"> \
              {{#termFilters}} \
              <div class="control-group filter-term filter" data-filter-id={{id}}> \
                <label class="control-label" for="">{{label}}</label> \
                <div class="controls"> \
                  <div class="input-append"> \
                    <input type="text" value="{{value}}" name="{{fieldId}}" class="span4" data-filter-field="{{fieldId}}" data-filter-id="{{id}}" data-filter-type="term" /> \
                    <a class="btn js-remove-filter"><i class="icon-remove"></i></a> \
                  </div> \
                </div> \
              </div> \
              {{/termFilters}} \
            </div> \
          <div class="span4"> \
            <p>To add a filter use the column menu in the grid view.</p> \
            <button type="submit" class="btn">Update</button> \
          </div> \
        </form> \
      </div> \
    </div> \
  ',
  events: {
    'click .js-hide': 'onHide',
    'click .js-remove-filter': 'onRemoveFilter',
    'submit form': 'onTermFiltersUpdate'
  },
  initialize: function() {
    this.el = $(this.el);
    _.bindAll(this, 'render');
    this.model.bind('change', this.render);
    this.model.bind('change:filters:new-blank', this.render);
    this.render();
  },
  render: function() {
    var tmplData = $.extend(true, {}, this.model.toJSON());
    // we will use idx in list as there id ...
    tmplData.filters = _.map(tmplData.filters, function(filter, idx) {
      filter.id = idx;
      return filter;
    });
    tmplData.termFilters = _.filter(tmplData.filters, function(filter) {
      return filter.term !== undefined;
    });
    tmplData.termFilters = _.map(tmplData.termFilters, function(filter) {
      var fieldId = _.keys(filter.term)[0];
      return {
        id: filter.id,
        fieldId: fieldId,
        label: fieldId,
        value: filter.term[fieldId]
      };
    });
    var out = $.mustache(this.template, tmplData);
    this.el.html(out);
    // are there actually any facets to show?
    if (this.model.get('filters').length > 0) {
      this.el.show();
    } else {
      this.el.hide();
    }
  },
  onHide: function(e) {
    e.preventDefault();
    this.el.hide();
  },
  onRemoveFilter: function(e) {
    e.preventDefault();
    var $target = $(e.target);
    var filterId = $target.closest('.filter').attr('data-filter-id');
    this.model.removeFilter(filterId);
  },
  onTermFiltersUpdate: function(e) {
   var self = this;
    e.preventDefault();
    var filters = self.model.get('filters');
    var $form = $(e.target);
    _.each($form.find('input'), function(input) {
      var $input = $(input);
      var filterIndex = parseInt($input.attr('data-filter-id'));
      var value = $input.val();
      var fieldId = $input.attr('data-filter-field');
      filters[filterIndex].term[fieldId] = value;
    });
    self.model.set({filters: filters});
    self.model.trigger('change');
  }
});

my.FacetViewer = Backbone.View.extend({
  className: 'recline-facet-viewer well', 
  template: ' \
    <a class="close js-hide" href="#">&times;</a> \
    <div class="facets row"> \
      <div class="span1"> \
        <h3>Facets</h3> \
      </div> \
      {{#facets}} \
      <div class="facet-summary span2 dropdown" data-facet="{{id}}"> \
        <a class="btn dropdown-toggle" data-toggle="dropdown" href="#"><i class="icon-chevron-down"></i> {{id}} {{label}}</a> \
        <ul class="facet-items dropdown-menu"> \
        {{#terms}} \
          <li><a class="facet-choice js-facet-filter" data-value="{{term}}">{{term}} ({{count}})</a></li> \
        {{/terms}} \
        {{#entries}} \
          <li><a class="facet-choice js-facet-filter" data-value="{{time}}">{{term}} ({{count}})</a></li> \
        {{/entries}} \
        </ul> \
      </div> \
      {{/facets}} \
    </div> \
  ',

  events: {
    'click .js-hide': 'onHide',
    'click .js-facet-filter': 'onFacetFilter'
  },
  initialize: function(model) {
    _.bindAll(this, 'render');
    this.el = $(this.el);
    this.model.facets.bind('all', this.render);
    this.model.fields.bind('all', this.render);
    this.render();
  },
  render: function() {
    var tmplData = {
      facets: this.model.facets.toJSON(),
      fields: this.model.fields.toJSON()
    };
    tmplData.facets = _.map(tmplData.facets, function(facet) {
      if (facet._type === 'date_histogram') {
        facet.entries = _.map(facet.entries, function(entry) {
          entry.term = new Date(entry.time).toDateString();
          return entry;
        });
      }
      return facet;
    });
    var templated = $.mustache(this.template, tmplData);
    this.el.html(templated);
    // are there actually any facets to show?
    if (this.model.facets.length > 0) {
      this.el.show();
    } else {
      this.el.hide();
    }
  },
  onHide: function(e) {
    e.preventDefault();
    this.el.hide();
  },
  onFacetFilter: function(e) {
    var $target= $(e.target);
    var fieldId = $target.closest('.facet-summary').attr('data-facet');
    var value = $target.attr('data-value');
    this.model.queryState.addTermFilter(fieldId, value);
  }
});

/* ========================================================== */
// ## Miscellaneous Utilities

var urlPathRegex = /^([^?]+)(\?.*)?/;

// Parse the Hash section of a URL into path and query string
my.parseHashUrl = function(hashUrl) {
  var parsed = urlPathRegex.exec(hashUrl);
  if (parsed === null) {
    return {};
  } else {
    return {
      path: parsed[1],
      query: parsed[2] || ''
    };
  }
};

// Parse a URL query string (?xyz=abc...) into a dictionary.
my.parseQueryString = function(q) {
  if (!q) {
    return {};
  }
  var urlParams = {},
    e, d = function (s) {
      return unescape(s.replace(/\+/g, " "));
    },
    r = /([^&=]+)=?([^&]*)/g;

  if (q && q.length && q[0] === '?') {
    q = q.slice(1);
  }
  while (e = r.exec(q)) {
    // TODO: have values be array as query string allow repetition of keys
    urlParams[d(e[1])] = d(e[2]);
  }
  return urlParams;
};

// Parse the query string out of the URL hash
my.parseHashQueryString = function() {
  q = my.parseHashUrl(window.location.hash).query;
  return my.parseQueryString(q);
};

// Compse a Query String
my.composeQueryString = function(queryParams) {
  var queryString = '?';
  var items = [];
  $.each(queryParams, function(key, value) {
    if (typeof(value) === 'object') {
      value = JSON.stringify(value);
    }
    items.push(key + '=' + value);
  });
  queryString += items.join('&');
  return queryString;
};

my.getNewHashForQueryString = function(queryParams) {
  var queryPart = my.composeQueryString(queryParams);
  if (window.location.hash) {
    // slice(1) to remove # at start
    return window.location.hash.split('?')[0].slice(1) + queryPart;
  } else {
    return queryPart;
  }
};

my.setHashQueryString = function(queryParams) {
  window.location.hash = my.getNewHashForQueryString(queryParams);
};

// ## notify
//
// Create a notification (a div.alert in div.alert-messsages) using provide messages and options. Options are:
//
// * category: warning (default), success, error
// * persist: if true alert is persistent, o/w hidden after 3s (default = false)
// * loader: if true show loading spinner
my.notify = function(message, options) {
  if (!options) options = {};
  var tmplData = _.extend({
    msg: message,
    category: 'warning'
    },
    options);
  var _template = ' \
    <div class="alert alert-{{category}} fade in" data-alert="alert"><a class="close" data-dismiss="alert" href="#">×</a> \
      {{msg}} \
        {{#loader}} \
        <span class="notification-loader">&nbsp;</span> \
        {{/loader}} \
    </div>';
  var _templated = $.mustache(_template, tmplData); 
  _templated = $(_templated).appendTo($('.recline-data-explorer .alert-messages'));
  if (!options.persist) {
    setTimeout(function() {
      $(_templated).fadeOut(1000, function() {
        $(this).remove();
      });
    }, 1000);
  }
};

// ## clearNotifications
//
// Clear all existing notifications
my.clearNotifications = function() {
  var $notifications = $('.recline-data-explorer .alert-messages .alert');
  $notifications.remove();
};

})(jQuery, recline.View);

// # Recline Backends
//
// Backends are connectors to backend data sources and stores
//
// This is just the base module containing a template Base class and convenience methods.
this.recline = this.recline || {};
this.recline.Backend = this.recline.Backend || {};

(function($, my) {
  // ## Backbone.sync
  //
  // Override Backbone.sync to hand off to sync function in relevant backend
  Backbone.sync = function(method, model, options) {
    return model.backend.sync(method, model, options);
  };

  // ## recline.Backend.Base
  //
  // Base class for backends providing a template and convenience functions.
  // You do not have to inherit from this class but even when not it does
  // provide guidance on the functions you must implement.
  //
  // Note also that while this (and other Backends) are implemented as Backbone models this is just a convenience.
  my.Base = Backbone.Model.extend({
    // ### __type__
    //
    // 'type' of this backend. This should be either the class path for this
    // object as a string (e.g. recline.Backend.Memory) or for Backends within
    // recline.Backend module it may be their class name.
    //
    // This value is used as an identifier for this backend when initializing
    // backends (see recline.Model.Dataset.initialize).
    __type__: 'base',


    // ### readonly
    //
    // Class level attribute indicating that this backend is read-only (that
    // is, cannot be written to).
    readonly: true,

    // ### sync
    //
    // An implementation of Backbone.sync that will be used to override
    // Backbone.sync on operations for Datasets and Documents which are using this backend.
    //
    // For read-only implementations you will need only to implement read method
    // for Dataset models (and even this can be a null operation). The read method
    // should return relevant metadata for the Dataset. We do not require read support
    // for Documents because they are loaded in bulk by the query method.
    //
    // For backends supporting write operations you must implement update and delete support for Document objects.
    //
    // All code paths should return an object conforming to the jquery promise API.
    sync: function(method, model, options) {
    },
    
    // ### query
    //
    // Query the backend for documents returning them in bulk. This method will
    // be used by the Dataset.query method to search the backend for documents,
    // retrieving the results in bulk.
    //
    // @param {recline.model.Dataset} model: Dataset model.
    //
    // @param {Object} queryObj: object describing a query (usually produced by
    // using recline.Model.Query and calling toJSON on it).
    //
    // The structure of data in the Query object or
    // Hash should follow that defined in <a
    // href="http://github.com/okfn/recline/issues/34">issue 34</a>.
    // (Of course, if you are writing your own backend, and hence
    // have control over the interpretation of the query object, you
    // can use whatever structure you like).
    //
    // @returns {Promise} promise API object. The promise resolve method will
    // be called on query completion with a QueryResult object.
    // 
    // A QueryResult has the following structure (modelled closely on
    // ElasticSearch - see <a
    // href="https://github.com/okfn/recline/issues/57">this issue for more
    // details</a>):
    //
    // <pre>
    // {
    //   total: // (required) total number of results (can be null)
    //   hits: [ // (required) one entry for each result document
    //     {
    //        _score:   // (optional) match score for document
    //        _type: // (optional) document type
    //        _source: // (required) document/row object
    //     } 
    //   ],
    //   facets: { // (optional) 
    //     // facet results (as per <http://www.elasticsearch.org/guide/reference/api/search/facets/>)
    //   }
    // }
    // </pre>
    query: function(model, queryObj) {
    },

    // ### _makeRequest
    // 
    // Just $.ajax but in any headers in the 'headers' attribute of this
    // Backend instance. Example:
    //
    // <pre>
    // var jqxhr = this._makeRequest({
    //   url: the-url
    // });
    // </pre>
    _makeRequest: function(data) {
      var headers = this.get('headers');
      var extras = {};
      if (headers) {
        extras = {
          beforeSend: function(req) {
            _.each(headers, function(value, key) {
              req.setRequestHeader(key, value);
            });
          }
        };
      }
      var data = _.extend(extras, data);
      return $.ajax(data);
    },

    // convenience method to convert simple set of documents / rows to a QueryResult
    _docsToQueryResult: function(rows) {
      var hits = _.map(rows, function(row) {
        return { _source: row };
      });
      return {
        total: null,
        hits: hits
      };
    },

    // ## _wrapInTimeout
    // 
    // Convenience method providing a crude way to catch backend errors on JSONP calls.
    // Many of backends use JSONP and so will not get error messages and this is
    // a crude way to catch those errors.
    _wrapInTimeout: function(ourFunction) {
      var dfd = $.Deferred();
      var timeout = 5000;
      var timer = setTimeout(function() {
        dfd.reject({
          message: 'Request Error: Backend did not respond after ' + (timeout / 1000) + ' seconds'
        });
      }, timeout);
      ourFunction.done(function(arguments) {
          clearTimeout(timer);
          dfd.resolve(arguments);
        })
        .fail(function(arguments) {
          clearTimeout(timer);
          dfd.reject(arguments);
        })
        ;
      return dfd.promise();
    }
  });

}(jQuery, this.recline.Backend));

this.recline = this.recline || {};
this.recline.Backend = this.recline.Backend || {};

(function($, my) {
  // ## DataProxy Backend
  // 
  // For connecting to [DataProxy-s](http://github.com/okfn/dataproxy).
  //
  // When initializing the DataProxy backend you can set the following attributes:
  //
  // * dataproxy: {url-to-proxy} (optional). Defaults to http://jsonpdataproxy.appspot.com
  //
  // Datasets using using this backend should set the following attributes:
  //
  // * url: (required) url-of-data-to-proxy
  // * format: (optional) csv | xls (defaults to csv if not specified)
  //
  // Note that this is a **read-only** backend.
  my.DataProxy = my.Base.extend({
    __type__: 'dataproxy',
    readonly: true,
    defaults: {
      dataproxy_url: 'http://jsonpdataproxy.appspot.com'
    },
    sync: function(method, model, options) {
      var self = this;
      if (method === "read") {
        if (model.__type__ == 'Dataset') {
          // Do nothing as we will get fields in query step (and no metadata to
          // retrieve)
          var dfd = $.Deferred();
          dfd.resolve(model);
          return dfd.promise();
        }
      } else {
        alert('This backend only supports read operations');
      }
    },
    query: function(dataset, queryObj) {
      var self = this;
      var base = this.get('dataproxy_url');
      var data = {
        url: dataset.get('url'),
        'max-results':  queryObj.size,
        type: dataset.get('format')
      };
      var jqxhr = $.ajax({
        url: base,
        data: data,
        dataType: 'jsonp'
      });
      var dfd = $.Deferred();
      this._wrapInTimeout(jqxhr).done(function(results) {
        if (results.error) {
          dfd.reject(results.error);
        }
        dataset.fields.reset(_.map(results.fields, function(fieldId) {
          return {id: fieldId};
          })
        );
        var _out = _.map(results.data, function(doc) {
          var tmp = {};
          _.each(results.fields, function(key, idx) {
            tmp[key] = doc[idx];
          });
          return tmp;
        });
        dfd.resolve(self._docsToQueryResult(_out));
      })
      .fail(function(arguments) {
        dfd.reject(arguments);
      });
      return dfd.promise();
    }
  });

}(jQuery, this.recline.Backend));
this.recline = this.recline || {};
this.recline.Backend = this.recline.Backend || {};

(function($, my) {
  // ## ElasticSearch Backend
  //
  // Connecting to [ElasticSearch](http://www.elasticsearch.org/).
  //
  // Usage:
  //
  // <pre>
  // var backend = new recline.Backend.ElasticSearch({
  //   // optional as can also be provided by Dataset/Document
  //   url: {url to ElasticSearch endpoint i.e. ES 'type/table' url - more info below}
  //   // optional
  //   headers: {dict of headers to add to each request}
  // });
  //
  // @param {String} url: url for ElasticSearch type/table, e.g. for ES running
  // on localhost:9200 with index // twitter and type tweet it would be:
  // 
  // <pre>http://localhost:9200/twitter/tweet</pre>
  //
  // This url is optional since the ES endpoint url may be specified on the the
  // dataset (and on a Document by the document having a dataset attribute) by
  // having one of the following (see also `_getESUrl` function):
  //
  // <pre>
  // elasticsearch_url
  // webstore_url
  // url
  // </pre>
  my.ElasticSearch = my.Base.extend({
    __type__: 'elasticsearch',
    readonly: false,
    sync: function(method, model, options) {
      var self = this;
      if (method === "read") {
        if (model.__type__ == 'Dataset') {
          var schemaUrl = self._getESUrl(model) + '/_mapping';
          var jqxhr = this._makeRequest({
            url: schemaUrl,
            dataType: 'jsonp'
          });
          var dfd = $.Deferred();
          this._wrapInTimeout(jqxhr).done(function(schema) {
            // only one top level key in ES = the type so we can ignore it
            var key = _.keys(schema)[0];
            var fieldData = _.map(schema[key].properties, function(dict, fieldName) {
              dict.id = fieldName;
              return dict;
            });
            model.fields.reset(fieldData);
            dfd.resolve(model, jqxhr);
          })
          .fail(function(arguments) {
            dfd.reject(arguments);
          });
          return dfd.promise();
        } else if (model.__type__ == 'Document') {
          var base = this._getESUrl(model.dataset) + '/' + model.id;
          return this._makeRequest({
            url: base,
            dataType: 'json'
          });
        }
      } else if (method === 'update') {
        if (model.__type__ == 'Document') {
          return this.upsert(model.toJSON(), this._getESUrl(model.dataset));
        }
      } else if (method === 'delete') {
        if (model.__type__ == 'Document') {
          var url = this._getESUrl(model.dataset);
          return this.delete(model.id, url);
        }
      }
    },

    // ### upsert
    //
    // create / update a document to ElasticSearch backend
    //
    // @param {Object} doc an object to insert to the index.
    // @param {string} url (optional) url for ElasticSearch endpoint (if not
    // defined called this._getESUrl()
    upsert: function(doc, url) {
      var data = JSON.stringify(doc);
      url = url ? url : this._getESUrl();
      if (doc.id) {
        url += '/' + doc.id;
      }
      return this._makeRequest({
        url: url,
        type: 'POST',
        data: data,
        dataType: 'json'
      });
    },

    // ### delete
    //
    // Delete a document from the ElasticSearch backend.
    //
    // @param {Object} id id of object to delete
    // @param {string} url (optional) url for ElasticSearch endpoint (if not
    // provided called this._getESUrl()
    delete: function(id, url) {
      url = url ? url : this._getESUrl();
      url += '/' + id;
      return this._makeRequest({
        url: url,
        type: 'DELETE',
        dataType: 'json'
      });
    },

    // ### _getESUrl
    //
    // get url to ElasticSearch endpoint (see above)
    _getESUrl: function(dataset) {
      if (dataset) {
        var out = dataset.get('elasticsearch_url');
        if (out) return out;
        out = dataset.get('webstore_url');
        if (out) return out;
        out = dataset.get('url');
        return out;
      }
      return this.get('url');
    },
    _normalizeQuery: function(queryObj) {
      var out = queryObj.toJSON ? queryObj.toJSON() : _.extend({}, queryObj);
      if (out.q !== undefined && out.q.trim() === '') {
        delete out.q;
      }
      if (!out.q) {
        out.query = {
          match_all: {}
        };
      } else {
        out.query = {
          query_string: {
            query: out.q
          }
        };
        delete out.q;
      }
      // now do filters (note the *plural*)
      if (out.filters && out.filters.length) {
        if (!out.filter) {
          out.filter = {};
        }
        if (!out.filter.and) {
          out.filter.and = [];
        }
        out.filter.and = out.filter.and.concat(out.filters);
      }
      if (out.filters !== undefined) {
        delete out.filters;
      }
      return out;
    },
    query: function(model, queryObj) {
      var queryNormalized = this._normalizeQuery(queryObj);
      var data = {source: JSON.stringify(queryNormalized)};
      var base = this._getESUrl(model);
      var jqxhr = this._makeRequest({
        url: base + '/_search',
        data: data,
        dataType: 'jsonp'
      });
      var dfd = $.Deferred();
      // TODO: fail case
      jqxhr.done(function(results) {
        _.each(results.hits.hits, function(hit) {
          if (!('id' in hit._source) && hit._id) {
            hit._source.id = hit._id;
          }
        });
        if (results.facets) {
          results.hits.facets = results.facets;
        }
        dfd.resolve(results.hits);
      });
      return dfd.promise();
    }
  });

}(jQuery, this.recline.Backend));

this.recline = this.recline || {};
this.recline.Backend = this.recline.Backend || {};

(function($, my) {
  // ## Google spreadsheet backend
  // 
  // Connect to Google Docs spreadsheet.
  //
  // Dataset must have a url attribute pointing to the Gdocs
  // spreadsheet's JSON feed e.g.
  //
  // <pre>
  // var dataset = new recline.Model.Dataset({
  //     url: 'https://spreadsheets.google.com/feeds/list/0Aon3JiuouxLUdDQwZE1JdV94cUd6NWtuZ0IyWTBjLWc/od6/public/values?alt=json'
  //   },
  //   'gdocs'
  // );
  // </pre>
  my.GDoc = my.Base.extend({
    __type__: 'gdoc',
    readonly: true,
    getUrl: function(dataset) {
      var url = dataset.get('url');
      if (url.indexOf('feeds/list') != -1) {
        return url;
      } else {
        // https://docs.google.com/spreadsheet/ccc?key=XXXX#gid=0
        var regex = /.*spreadsheet\/ccc?.*key=([^#?&+]+).*/;
        var matches = url.match(regex);
        if (matches) {
          var key = matches[1];
          var worksheet = 1;
          var out = 'https://spreadsheets.google.com/feeds/list/' + key + '/' + worksheet + '/public/values?alt=json';
          return out;
        } else {
          alert('Failed to extract gdocs key from ' + url);
        }
      }
    },
    sync: function(method, model, options) {
      var self = this;
      if (method === "read") { 
        var dfd = $.Deferred(); 
        var dataset = model;

        var url = this.getUrl(model);

        $.getJSON(url, function(d) {
          result = self.gdocsToJavascript(d);
          model.fields.reset(_.map(result.field, function(fieldId) {
              return {id: fieldId};
            })
          );
          // cache data onto dataset (we have loaded whole gdoc it seems!)
          model._dataCache = result.data;
          dfd.resolve(model);
        });
        return dfd.promise();
      }
    },

    query: function(dataset, queryObj) { 
      var dfd = $.Deferred();
      var fields = _.pluck(dataset.fields.toJSON(), 'id');

      // zip the fields with the data rows to produce js objs
      // TODO: factor this out as a common method with other backends
      var objs = _.map(dataset._dataCache, function (d) { 
        var obj = {};
        _.each(_.zip(fields, d), function (x) {
          obj[x[0]] = x[1];
        });
        return obj;
      });
      dfd.resolve(this._docsToQueryResult(objs));
      return dfd;
    },
    gdocsToJavascript:  function(gdocsSpreadsheet) {
      /*
         :options: (optional) optional argument dictionary:
         columnsToUse: list of columns to use (specified by field names)
         colTypes: dictionary (with column names as keys) specifying types (e.g. range, percent for use in conversion).
         :return: tabular data object (hash with keys: field and data).

         Issues: seems google docs return columns in rows in random order and not even sure whether consistent across rows.
         */
      var options = {};
      if (arguments.length > 1) {
        options = arguments[1];
      }
      var results = {
        'field': [],
        'data': []
      };
      // default is no special info on type of columns
      var colTypes = {};
      if (options.colTypes) {
        colTypes = options.colTypes;
      }
      // either extract column headings from spreadsheet directly, or used supplied ones
      if (options.columnsToUse) {
        // columns set to subset supplied
        results.field = options.columnsToUse;
      } else {
        // set columns to use to be all available
        if (gdocsSpreadsheet.feed.entry.length > 0) {
          for (var k in gdocsSpreadsheet.feed.entry[0]) {
            if (k.substr(0, 3) == 'gsx') {
              var col = k.substr(4);
              results.field.push(col);
            }
          }
        }
      }

      // converts non numberical values that should be numerical (22.3%[string] -> 0.223[float])
      var rep = /^([\d\.\-]+)\%$/;
      $.each(gdocsSpreadsheet.feed.entry, function (i, entry) {
        var row = [];
        for (var k in results.field) {
          var col = results.field[k];
          var _keyname = 'gsx$' + col;
          var value = entry[_keyname]['$t'];
          // if labelled as % and value contains %, convert
          if (colTypes[col] == 'percent') {
            if (rep.test(value)) {
              var value2 = rep.exec(value);
              var value3 = parseFloat(value2);
              value = value3 / 100;
            }
          }
          row.push(value);
        }
        results.data.push(row);
      });
      return results;
    }
  });

}(jQuery, this.recline.Backend));

this.recline = this.recline || {};
this.recline.Backend = this.recline.Backend || {};

(function($, my) {
  my.loadFromCSVFile = function(file, callback, options) {
    var encoding = options.encoding || 'UTF-8';
    
    var metadata = {
      id: file.name,
      file: file
    };
    var reader = new FileReader();
    // TODO
    reader.onload = function(e) {
      var dataset = my.csvToDataset(e.target.result, options);
      callback(dataset);
    };
    reader.onerror = function (e) {
      alert('Failed to load file. Code: ' + e.target.error.code);
    };
    reader.readAsText(file, encoding);
  };

  my.csvToDataset = function(csvString, options) {
    var out = my.parseCSV(csvString, options);
    fields = _.map(out[0], function(cell) {
      return { id: cell, label: cell };
    });
    var data = _.map(out.slice(1), function(row) {
      var _doc = {};
      _.each(out[0], function(fieldId, idx) {
        _doc[fieldId] = row[idx];
      });
      return _doc;
    });
    var dataset = recline.Backend.createDataset(data, fields);
    return dataset;
  };

  // Converts a Comma Separated Values string into an array of arrays.
  // Each line in the CSV becomes an array.
  //
  // Empty fields are converted to nulls and non-quoted numbers are converted to integers or floats.
  //
  // @return The CSV parsed as an array
  // @type Array
  // 
  // @param {String} s The string to convert
  // @param {Object} options Options for loading CSV including
  // 	@param {Boolean} [trim=false] If set to True leading and trailing whitespace is stripped off of each non-quoted field as it is imported
  //	@param {String} [separator=','] Separator for CSV file
  // Heavily based on uselesscode's JS CSV parser (MIT Licensed):
  // thttp://www.uselesscode.org/javascript/csv/
  my.parseCSV= function(s, options) {
    // Get rid of any trailing \n
    s = chomp(s);

    var options = options || {};
    var trm = options.trim;
    var separator = options.separator || ',';
    var delimiter = options.delimiter || '"';


    var cur = '', // The character we are currently processing.
      inQuote = false,
      fieldQuoted = false,
      field = '', // Buffer for building up the current field
      row = [],
      out = [],
      i,
      processField;

    processField = function (field) {
      if (fieldQuoted !== true) {
        // If field is empty set to null
        if (field === '') {
          field = null;
        // If the field was not quoted and we are trimming fields, trim it
        } else if (trm === true) {
          field = trim(field);
        }

        // Convert unquoted numbers to their appropriate types
        if (rxIsInt.test(field)) {
          field = parseInt(field, 10);
        } else if (rxIsFloat.test(field)) {
          field = parseFloat(field, 10);
        }
      }
      return field;
    };

    for (i = 0; i < s.length; i += 1) {
      cur = s.charAt(i);

      // If we are at a EOF or EOR
      if (inQuote === false && (cur === separator || cur === "\n")) {
	field = processField(field);
        // Add the current field to the current row
        row.push(field);
        // If this is EOR append row to output and flush row
        if (cur === "\n") {
          out.push(row);
          row = [];
        }
        // Flush the field buffer
        field = '';
        fieldQuoted = false;
      } else {
        // If it's not a delimiter, add it to the field buffer
        if (cur !== delimiter) {
          field += cur;
        } else {
          if (!inQuote) {
            // We are not in a quote, start a quote
            inQuote = true;
            fieldQuoted = true;
          } else {
            // Next char is delimiter, this is an escaped delimiter
            if (s.charAt(i + 1) === delimiter) {
              field += delimiter;
              // Skip the next char
              i += 1;
            } else {
              // It's not escaping, so end quote
              inQuote = false;
            }
          }
        }
      }
    }

    // Add the last field
    field = processField(field);
    row.push(field);
    out.push(row);

    return out;
  };

  var rxIsInt = /^\d+$/,
    rxIsFloat = /^\d*\.\d+$|^\d+\.\d*$/,
    // If a string has leading or trailing space,
    // contains a comma double quote or a newline
    // it needs to be quoted in CSV output
    rxNeedsQuoting = /^\s|\s$|,|"|\n/,
    trim = (function () {
      // Fx 3.1 has a native trim function, it's about 10x faster, use it if it exists
      if (String.prototype.trim) {
        return function (s) {
          return s.trim();
        };
      } else {
        return function (s) {
          return s.replace(/^\s*/, '').replace(/\s*$/, '');
        };
      }
    }());

  function chomp(s) {
    if (s.charAt(s.length - 1) !== "\n") {
      // Does not end with \n, just return string
      return s;
    } else {
      // Remove the \n
      return s.substring(0, s.length - 1);
    }
  }


}(jQuery, this.recline.Backend));
this.recline = this.recline || {};
this.recline.Backend = this.recline.Backend || {};

(function($, my) {
  // ## createDataset
  //
  // Convenience function to create a simple 'in-memory' dataset in one step.
  //
  // @param data: list of hashes for each document/row in the data ({key:
  // value, key: value})
  // @param fields: (optional) list of field hashes (each hash defining a hash
  // as per recline.Model.Field). If fields not specified they will be taken
  // from the data.
  // @param metadata: (optional) dataset metadata - see recline.Model.Dataset.
  // If not defined (or id not provided) id will be autogenerated.
  my.createDataset = function(data, fields, metadata) {
    if (!metadata) {
      metadata = {};
    }
    if (!metadata.id) {
      metadata.id = String(Math.floor(Math.random() * 100000000) + 1);
    }
    var backend = new recline.Backend.Memory();
    var datasetInfo = {
      documents: data,
      metadata: metadata
    };
    if (fields) {
      datasetInfo.fields = fields;
    } else {
      if (data) {
        datasetInfo.fields = _.map(data[0], function(value, key) {
          return {id: key};
        });
      }
    }
    backend.addDataset(datasetInfo);
    var dataset = new recline.Model.Dataset({id: metadata.id}, backend);
    dataset.fetch();
    return dataset;
  };


  // ## Memory Backend - uses in-memory data
  //
  // To use it you should provide in your constructor data:
  // 
  //   * metadata (including fields array)
  //   * documents: list of hashes, each hash being one doc. A doc *must* have an id attribute which is unique.
  //
  // Example:
  // 
  //  <pre>
  //  // Backend setup
  //  var backend = recline.Backend.Memory();
  //  backend.addDataset({
  //    metadata: {
  //      id: 'my-id',
  //      title: 'My Title'
  //    },
  //    fields: [{id: 'x'}, {id: 'y'}, {id: 'z'}],
  //    documents: [
  //        {id: 0, x: 1, y: 2, z: 3},
  //        {id: 1, x: 2, y: 4, z: 6}
  //      ]
  //  });
  //  // later ...
  //  var dataset = Dataset({id: 'my-id'}, 'memory');
  //  dataset.fetch();
  //  etc ...
  //  </pre>
  my.Memory = my.Base.extend({
    __type__: 'memory',
    readonly: false,
    initialize: function() {
      this.datasets = {};
    },
    addDataset: function(data) {
      this.datasets[data.metadata.id] = $.extend(true, {}, data);
    },
    sync: function(method, model, options) {
      var self = this;
      var dfd = $.Deferred();
      if (method === "read") {
        if (model.__type__ == 'Dataset') {
          var rawDataset = this.datasets[model.id];
          model.set(rawDataset.metadata);
          model.fields.reset(rawDataset.fields);
          model.docCount = rawDataset.documents.length;
          dfd.resolve(model);
        }
        return dfd.promise();
      } else if (method === 'update') {
        if (model.__type__ == 'Document') {
          _.each(self.datasets[model.dataset.id].documents, function(doc, idx) {
            if(doc.id === model.id) {
              self.datasets[model.dataset.id].documents[idx] = model.toJSON();
            }
          });
          dfd.resolve(model);
        }
        return dfd.promise();
      } else if (method === 'delete') {
        if (model.__type__ == 'Document') {
          var rawDataset = self.datasets[model.dataset.id];
          var newdocs = _.reject(rawDataset.documents, function(doc) {
            return (doc.id === model.id);
          });
          rawDataset.documents = newdocs;
          dfd.resolve(model);
        }
        return dfd.promise();
      } else {
        alert('Not supported: sync on Memory backend with method ' + method + ' and model ' + model);
      }
    },
    query: function(model, queryObj) {
      var dfd = $.Deferred();
      var out = {};
      var numRows = queryObj.size;
      var start = queryObj.from;
      var results = this.datasets[model.id].documents;
      results = this._applyFilters(results, queryObj);
      results = this._applyFreeTextQuery(model, results, queryObj);
      // not complete sorting!
      _.each(queryObj.sort, function(sortObj) {
        var fieldName = _.keys(sortObj)[0];
        results = _.sortBy(results, function(doc) {
          var _out = doc[fieldName];
          return (sortObj[fieldName].order == 'asc') ? _out : -1*_out;
        });
      });
      out.facets = this._computeFacets(results, queryObj);
      var total = results.length;
      resultsObj = this._docsToQueryResult(results.slice(start, start+numRows));
      _.extend(out, resultsObj);
      out.total = total;
      dfd.resolve(out);
      return dfd.promise();
    },

    // in place filtering
    _applyFilters: function(results, queryObj) {
      _.each(queryObj.filters, function(filter) {
        results = _.filter(results, function(doc) {
          var fieldId = _.keys(filter.term)[0];
          return (doc[fieldId] == filter.term[fieldId]);
        });
      });
      return results;
    },

    // we OR across fields but AND across terms in query string
    _applyFreeTextQuery: function(dataset, results, queryObj) {
      if (queryObj.q) {
        var terms = queryObj.q.split(' ');
        results = _.filter(results, function(rawdoc) {
          var matches = true;
          _.each(terms, function(term) {
            var foundmatch = false;
            dataset.fields.each(function(field) {
              var value = rawdoc[field.id];
              if (value !== null) { value = value.toString(); }
              // TODO regexes?
              foundmatch = foundmatch || (value === term);
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
    },

    _computeFacets: function(documents, queryObj) {
      var facetResults = {};
      if (!queryObj.facets) {
        return facetsResults;
      }
      _.each(queryObj.facets, function(query, facetId) {
        facetResults[facetId] = new recline.Model.Facet({id: facetId}).toJSON();
        facetResults[facetId].termsall = {};
      });
      // faceting
      _.each(documents, function(doc) {
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
    }
  });

}(jQuery, this.recline.Backend));
