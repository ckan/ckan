// importScripts('lib/underscore.js'); 

onmessage = function(message) {
  
  function parseCSV(rawCSV) {
    var patterns = new RegExp((
      // Delimiters.
      "(\\,|\\r?\\n|\\r|^)" +
      // Quoted fields.
      "(?:\"([^\"]*(?:\"\"[^\"]*)*)\"|" +
      // Standard fields.
      "([^\"\\,\\r\\n]*))"
    ), "gi");

    var rows = [[]], matches = null;

    while (matches = patterns.exec(rawCSV)) {
      var delimiter = matches[1];

      if (delimiter.length && (delimiter !== ",")) rows.push([]);

      if (matches[2]) {
        var value = matches[2].replace(new RegExp("\"\"", "g"), "\"");
      } else {
        var value = matches[3];
      }
      rows[rows.length - 1].push(value);
    }

    if(_.isEqual(rows[rows.length -1], [""])) rows.pop();

    var docs = [];
    var headers = _.first(rows);
    _.each(_.rest(rows), function(row, rowIDX) {
      var doc = {};
      _.each(row, function(cell, idx) {      
        doc[headers[idx]] = cell;
      })
      docs.push(doc);
    })

    return docs;
  }
  
  var docs = parseCSV(message.data.data);
  
  var req = new XMLHttpRequest();

  req.onprogress = req.upload.onprogress = function(e) {
    if(e.lengthComputable) postMessage({ percent: (e.loaded / e.total) * 100 });
  };
  
  req.onreadystatechange = function() { if (req.readyState == 4) postMessage({done: true, response: req.responseText}) };
  req.open('POST', message.data.url);
  req.setRequestHeader('Content-Type', 'application/json');
  req.send(JSON.stringify({docs: docs}));
};
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

// ## A Dataset model
//
// A model must have the following (Backbone) attributes:
//
// * fields: (aka columns) is a FieldList listing all the fields on this
//   Dataset (this can be set explicitly, or, on fetch() of Dataset
//   information from the backend, or as is perhaps most common on the first
//   query)
// * currentDocuments: a DocumentList containing the Documents we have currently loaded for viewing (you update currentDocuments by calling getRows)
// * docCount: total number of documents in this dataset (obtained on a fetch for this Dataset)
my.Dataset = Backbone.Model.extend({
  __type__: 'Dataset',
  initialize: function(model, backend) {
    _.bindAll(this, 'query');
    this.backend = backend;
    if (backend && backend.constructor == String) {
      this.backend = my.backends[backend];
    }
    this.fields = new my.FieldList();
    this.currentDocuments = new my.DocumentList();
    this.docCount = null;
    this.queryState = new my.Query();
    this.queryState.bind('change', this.query);
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
    this.trigger('query:start');
    var self = this;
    this.queryState.set(queryObj, {silent: true});
    var dfd = $.Deferred();
    this.backend.query(this, this.queryState.toJSON()).done(function(rows) {
      var docs = _.map(rows, function(row) {
        var _doc = new my.Document(row);
        _doc.backend = self.backend;
        _doc.dataset = self;
        return _doc;
      });
      self.currentDocuments.reset(docs);
      self.trigger('query:done');
      dfd.resolve(self.currentDocuments);
    })
    .fail(function(arguments) {
      self.trigger('query:fail', arguments);
      dfd.reject(arguments);
    });
    return dfd.promise();
  },

  toTemplateJSON: function() {
    var data = this.toJSON();
    data.docCount = this.docCount;
    data.fields = this.fields.toJSON();
    return data;
  }
});

// ## A Document (aka Row)
// 
// A single entry or row in the dataset
my.Document = Backbone.Model.extend({
  __type__: 'Document'
});

// ## A Backbone collection of Documents
my.DocumentList = Backbone.Collection.extend({
  __type__: 'DocumentList',
  model: my.Document
});

// ## A Field (aka Column) on a Dataset
// 
// Following attributes as standard:
//
//  * id: a unique identifer for this field- usually this should match the key in the documents hash
//  * label: the visible label used for this field
//  * type: the type of the data
my.Field = Backbone.Model.extend({
  defaults: {
    id: null,
    label: null,
    type: 'String'
  },
  // In addition to normal backbone initialization via a Hash you can also
  // just pass a single argument representing id to the ctor
  initialize: function(data) {
    // if a hash not passed in the first argument is set as value for key 0
    if ('0' in data) {
      throw new Error('Looks like you did not pass a proper hash with id to Field constructor');
    }
    if (this.attributes.label == null) {
      this.set({label: this.id});
    }
  }
});

my.FieldList = Backbone.Collection.extend({
  model: my.Field
});

// ## A Query object storing Dataset Query state
my.Query = Backbone.Model.extend({
  defaults: {
    size: 100
    , from: 0
  }
});

// ## Backend registry
//
// Backends will register themselves by id into this registry
my.backends = {};

}(jQuery, this.recline.Model));

var util = function() {
  var templates = {
    transformActions: '<li><a data-action="transform" class="menuAction" href="JavaScript:void(0);">Global transform...</a></li>'
    , columnActions: ' \
      <li class="write-op"><a data-action="bulkEdit" class="menuAction" href="JavaScript:void(0);">Transform...</a></li> \
      <li class="write-op"><a data-action="deleteColumn" class="menuAction" href="JavaScript:void(0);">Delete this column</a></li> \
      <li><a data-action="sortAsc" class="menuAction" href="JavaScript:void(0);">Sort ascending</a></li> \
      <li><a data-action="sortDesc" class="menuAction" href="JavaScript:void(0);">Sort descending</a></li> \
      <li><a data-action="hideColumn" class="menuAction" href="JavaScript:void(0);">Hide this column</a></li> \
    '
    , rowActions: '<li><a data-action="deleteRow" class="menuAction write-op" href="JavaScript:void(0);">Delete this row</a></li>'
    , rootActions: ' \
        {{#columns}} \
        <li><a data-action="showColumn" data-column="{{.}}" class="menuAction" href="JavaScript:void(0);">Show column: {{.}}</a></li> \
        {{/columns}}'
    , cellEditor: ' \
      <div class="menu-container data-table-cell-editor"> \
        <textarea class="data-table-cell-editor-editor" bind="textarea">{{value}}</textarea> \
        <div id="data-table-cell-editor-actions"> \
          <div class="data-table-cell-editor-action"> \
            <button class="okButton btn primary">Update</button> \
            <button class="cancelButton btn danger">Cancel</button> \
          </div> \
        </div> \
      </div> \
    '
    , editPreview: ' \
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
        if (!channel) var channel = 'data';
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
		}
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
    if (target instanceof jQuery) {
      var targetDom = target;
    } else {
      var targetDom = $( "." + target + ":first" );      
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
this.recline = this.recline || {};
this.recline.View = this.recline.View || {};

(function($, my) {

// ## Graph view for a Dataset using Flot graphing library.
//
// Initialization arguments:
//
// * model: recline.Model.Dataset
// * config: (optional) graph configuration hash of form:
//
//        { 
//          group: {column name for x-axis},
//          series: [{column name for series A}, {column name series B}, ... ],
//          graphType: 'line'
//        }
//
// NB: should *not* provide an el argument to the view but must let the view
// generate the element itself (you can then append view.el to the DOM.
my.FlotGraph = Backbone.View.extend({

  tagName:  "div",
  className: "data-graph-container",

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
          <option value="line">Line</option> \
          </select> \
        </div> \
        <label>Group Column (x-axis)</label> \
        <div class="input editor-group"> \
          <select> \
          {{#fields}} \
          <option value="{{id}}">{{label}}</option> \
          {{/fields}} \
          </select> \
        </div> \
        <div class="editor-series-group"> \
          <div class="editor-series"> \
            <label>Series <span>A (y-axis)</span></label> \
            <div class="input"> \
              <select> \
              {{#fields}} \
              <option value="{{id}}">{{label}}</option> \
              {{/fields}} \
              </select> \
            </div> \
          </div> \
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
  <div class="panel graph"></div> \
</div> \
',

  events: {
    'change form select': 'onEditorSubmit'
    , 'click .editor-add': 'addSeries'
    , 'click .action-remove-series': 'removeSeries'
    , 'click .action-toggle-help': 'toggleHelp'
  },

  initialize: function(options, config) {
    var self = this;
    this.el = $(this.el);
    _.bindAll(this, 'render', 'redraw');
    // we need the model.fields to render properly
    this.model.bind('change', this.render);
    this.model.fields.bind('reset', this.render);
    this.model.fields.bind('add', this.render);
    this.model.currentDocuments.bind('add', this.redraw);
    this.model.currentDocuments.bind('reset', this.redraw);
    var configFromHash = my.parseHashQueryString().graph;
    if (configFromHash) {
      configFromHash = JSON.parse(configFromHash);
    }
    this.chartConfig = _.extend({
        group: null,
        series: [],
        graphType: 'line'
      },
      configFromHash,
      config
      );
    this.render();
  },

  render: function() {
    htmls = $.mustache(this.template, this.model.toTemplateJSON());
    $(this.el).html(htmls);
    // now set a load of stuff up
    this.$graph = this.el.find('.panel.graph');
    // for use later when adding additional series
    // could be simpler just to have a common template!
    this.$seriesClone = this.el.find('.editor-series').clone();
    this._updateSeries();
    return this;
  },

  onEditorSubmit: function(e) {
    var select = this.el.find('.editor-group select');
    this._getEditorData();
    // update navigation
    // TODO: make this less invasive (e.g. preserve other keys in query string)
    var qs = my.parseHashQueryString();
    qs['graph'] = this.chartConfig;
    my.setHashQueryString(qs);
    this.redraw();
  },

  redraw: function() {
    // There appear to be issues generating a Flot graph if either:

    // * The relevant div that graph attaches to his hidden at the moment of creating the plot -- Flot will complain with
    //
    //   Uncaught Invalid dimensions for plot, width = 0, height = 0
    // * There is no data for the plot -- either same error or may have issues later with errors like 'non-existent node-value' 
    var areWeVisible = !jQuery.expr.filters.hidden(this.el[0]);
    if ((!areWeVisible || this.model.currentDocuments.length == 0)) {
      return
    }
    // create this.plot and cache it
    if (!this.plot) {
      // only lines for the present
      options = {
        id: 'line',
        name: 'Line Chart'
      };
      this.plot = $.plot(this.$graph, this.createSeries(), options);
    } 
    this.plot.setData(this.createSeries());
    this.plot.resize();
    this.plot.setupGrid();
    this.plot.draw();
  },

  _getEditorData: function() {
    $editor = this
    var series = this.$series.map(function () {
      return $(this).val();
    });
    this.chartConfig.series = $.makeArray(series)
    this.chartConfig.group = this.el.find('.editor-group select').val();
  },

  createSeries: function () {
    var self = this;
    var series = [];
    if (this.chartConfig) {
      $.each(this.chartConfig.series, function (seriesIndex, field) {
        var points = [];
        $.each(self.model.currentDocuments.models, function (index, doc) {
          var x = doc.get(self.chartConfig.group);
          var y = doc.get(field);
          if (typeof x === 'string') {
            x = index;
          }
          points.push([x, y]);
        });
        series.push({data: points, label: field});
      });
    }
    return series;
  },

  // Public: Adds a new empty series select box to the editor.
  //
  // All but the first select box will have a remove button that allows them
  // to be removed.
  //
  // Returns itself.
  addSeries: function (e) {
    e.preventDefault();
    var element = this.$seriesClone.clone(),
        label   = element.find('label'),
        index   = this.$series.length;

    this.el.find('.editor-series-group').append(element);
    this._updateSeries();
    label.append(' [<a href="#remove" class="action-remove-series">Remove</a>]');
    label.find('span').text(String.fromCharCode(this.$series.length + 64));
    return this;
  },

  // Public: Removes a series list item from the editor.
  //
  // Also updates the labels of the remaining series elements.
  removeSeries: function (e) {
    e.preventDefault();
    var $el = $(e.target);
    $el.parent().parent().remove();
    this._updateSeries();
    this.$series.each(function (index) {
      if (index > 0) {
        var labelSpan = $(this).prev().find('span');
        labelSpan.text(String.fromCharCode(index + 65));
      }
    });
    this.onEditorSubmit();
  },

  toggleHelp: function() {
    this.el.find('.editor-info').toggleClass('editor-hide-info');
  },

  // Private: Resets the series property to reference the select elements.
  //
  // Returns itself.
  _updateSeries: function () {
    this.$series  = this.el.find('.editor-series select');
  }
});

})(jQuery, recline.View);

this.recline = this.recline || {};
this.recline.View = this.recline.View || {};

(function($, my) {
// ## DataGrid
//
// Provides a tabular view on a Dataset.
//
// Initialize it with a recline.Dataset object.
//
// Additional options passed in second arguments. Options:
//
// * cellRenderer: function used to render individual cells. See DataGridRow for more.
my.DataGrid = Backbone.View.extend({
  tagName:  "div",
  className: "data-table-container",

  initialize: function(modelEtc, options) {
    var self = this;
    this.el = $(this.el);
    _.bindAll(this, 'render');
    this.model.currentDocuments.bind('add', this.render);
    this.model.currentDocuments.bind('reset', this.render);
    this.model.currentDocuments.bind('remove', this.render);
    this.state = {};
    this.hiddenFields = [];
    this.options = options;
  },

  events: {
    'click .column-header-menu': 'onColumnHeaderClick'
    , 'click .row-header-menu': 'onRowHeaderClick'
    , 'click .root-header-menu': 'onRootHeaderClick'
    , 'click .data-table-menu li a': 'onMenuClick'
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
    this.state.currentColumn = $(e.target).closest('.column-header').attr('data-field');
    util.position('data-table-menu', e);
    util.render('columnActions', 'data-table-menu');
  },

  onRowHeaderClick: function(e) {
    this.state.currentRow = $(e.target).parents('tr:first').attr('data-id');
    util.position('data-table-menu', e);
    util.render('rowActions', 'data-table-menu');
  },
  
  onRootHeaderClick: function(e) {
    util.position('data-table-menu', e);
    util.render('rootActions', 'data-table-menu', {'columns': this.hiddenFields});
  },

  onMenuClick: function(e) {
    var self = this;
    e.preventDefault();
    var actions = {
      bulkEdit: function() { self.showTransformColumnDialog('bulkEdit', {name: self.state.currentColumn}) },
      transform: function() { self.showTransformDialog('transform') },
      sortAsc: function() { self.setColumnSort('asc') },
      sortDesc: function() { self.setColumnSort('desc') },
      hideColumn: function() { self.hideColumn() },
      showColumn: function() { self.showColumn(e) },
      // TODO: Delete or re-implement ...
      csv: function() { window.location.href = app.csvUrl },
      json: function() { window.location.href = "_rewrite/api/json" },
      urlImport: function() { showDialog('urlImport') },
      pasteImport: function() { showDialog('pasteImport') },
      uploadImport: function() { showDialog('uploadImport') },
      // END TODO
      deleteColumn: function() {
        var msg = "Are you sure? This will delete '" + self.state.currentColumn + "' from all documents.";
        // TODO:
        alert('This function needs to be re-implemented');
        return;
        if (confirm(msg)) costco.deleteColumn(self.state.currentColumn);
      },
      deleteRow: function() {
        var doc = _.find(self.model.currentDocuments.models, function(doc) {
          // important this is == as the currentRow will be string (as comes
          // from DOM) while id may be int
          return doc.id == self.state.currentRow
        });
        doc.destroy().then(function() { 
            self.model.currentDocuments.remove(doc);
            my.notify("Row deleted successfully");
          })
          .fail(function(err) {
            my.notify("Errorz! " + err)
          })
      }
    }
    util.hide('data-table-menu');
    actions[$(e.target).attr('data-action')]();
  },

  showTransformColumnDialog: function() {
    var $el = $('.dialog-content');
    util.show('dialog');
    var view = new my.ColumnTransform({
      model: this.model
    });
    view.state = this.state;
    view.render();
    $el.empty();
    $el.append(view.el);
    util.observeExit($el, function() {
      util.hide('dialog');
    })
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
    })
    $('.dialog').draggable({ handle: '.dialog-header', cursor: 'move' });
  },

  setColumnSort: function(order) {
    var sort = [{}];
    sort[0][this.state.currentColumn] = {order: order};
    this.model.query({sort: sort});
  },
  
  hideColumn: function() {
    this.hiddenFields.push(this.state.currentColumn);
    this.render();
  },
  
  showColumn: function(e) {
    this.hiddenFields = _.without(this.hiddenFields, $(e.target).data('column'));
    this.render();
  },

  // ======================================================
  // #### Templating
  template: ' \
    <div class="data-table-menu-overlay" style="display: none; z-index: 101; ">&nbsp;</div> \
    <ul class="data-table-menu"></ul> \
    <table class="data-table table-striped" cellspacing="0"> \
      <thead> \
        <tr> \
          {{#notEmpty}} \
            <th class="column-header"> \
              <div class="column-header-title"> \
                <a class="root-header-menu"></a> \
                <span class="column-header-name"></span> \
              </div> \
            </th> \
          {{/notEmpty}} \
          {{#fields}} \
            <th class="column-header {{#hidden}}hidden{{/hidden}}" data-field="{{id}}"> \
              <div class="column-header-title"> \
                <a class="column-header-menu"></a> \
                <span class="column-header-name">{{label}}</span> \
              </div> \
              </div> \
            </th> \
          {{/fields}} \
        </tr> \
      </thead> \
      <tbody></tbody> \
    </table> \
  ',

  toTemplateJSON: function() {
    var modelData = this.model.toJSON()
    modelData.notEmpty = ( this.fields.length > 0 )
    // TODO: move this sort of thing into a toTemplateJSON method on Dataset?
    modelData.fields = _.map(this.fields, function(field) { return field.toJSON() });
    return modelData;
  },
  render: function() {
    var self = this;
    this.fields = this.model.fields.filter(function(field) {
      return _.indexOf(self.hiddenFields, field.id) == -1;
    });
    var htmls = $.mustache(this.template, this.toTemplateJSON());
    this.el.html(htmls);
    this.model.currentDocuments.forEach(function(doc) {
      var tr = $('<tr />');
      self.el.find('tbody').append(tr);
      var newView = new my.DataGridRow({
          model: doc,
          el: tr,
          fields: self.fields,
        },
        self.options
        );
      newView.render();
    });
    this.el.toggleClass('no-hidden', (self.hiddenFields.length == 0));
    return this;
  }
});

// ## DataGridRow View for rendering an individual document.
//
// Since we want this to update in place it is up to creator to provider the element to attach to.
//
// In addition you *must* pass in a FieldList in the constructor options. This should be list of fields for the DataGrid.
//
// Additional options can be passed in a second hash argument. Options:
//
// * cellRenderer: function to render cells. Signature: function(value,
//   field, doc) where value is the value of this cell, field is
//   corresponding field object and document is the document object. Note
//   that implementing functions can ignore arguments (e.g.
//   function(value) would be a valid cellRenderer function).
//
// Example:
//
// <pre>
// var row = new DataGridRow({
//   model: dataset-document,
//     el: dom-element,
//     fields: mydatasets.fields // a FieldList object
//   }, {
//     cellRenderer: my-cell-renderer-function 
//   }
// );
// </pre>
my.DataGridRow = Backbone.View.extend({
  initialize: function(initData, options) {
    _.bindAll(this, 'render');
    this._fields = initData.fields;
    if (options && options.cellRenderer) {
      this._cellRenderer = options.cellRenderer;
    } else {
      this._cellRenderer = function(value) {
        return value;
      }
    }
    this.el = $(this.el);
    this.model.bind('change', this.render);
  },

  template: ' \
      <td><a class="row-header-menu"></a></td> \
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
        value: self._cellRenderer(doc.get(field.id), field, doc)
      }
    })
    return { id: this.id, cells: cellData }
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
//   views: {{page views}}
//   config: {{config options -- see below}}
// });
// </pre> 
//
// ### Parameters
// 
// **model**: (required) Dataset instance.
//
// **el**: (required) DOM element.
//
// **views**: (optional) the views (Grid, Graph etc) for DataExplorer to
// show. This is an array of view hashes. If not provided
// just initialize a DataGrid with id 'grid'. Example:
//
// <pre>
// var views = [
//   {
//     id: 'grid', // used for routing
//     label: 'Grid', // used for view switcher
//     view: new recline.View.DataGrid({
//       model: dataset
//     })
//   },
//   {
//     id: 'graph',
//     label: 'Graph',
//     view: new recline.View.FlotGraph({
//       model: dataset
//     })
//   }
// ];
// </pre>
//
// **config**: Config options like:
//
//   * readOnly: true/false (default: false) value indicating whether to
//     operate in read-only mode (hiding all editing options).
//
// NB: the element already being in the DOM is important for rendering of
// FlotGraph subview.
my.DataExplorer = Backbone.View.extend({
  template: ' \
  <div class="data-explorer"> \
    <div class="alert-messages"></div> \
    \
    <div class="header"> \
      <ul class="navigation"> \
        {{#views}} \
        <li><a href="#{{id}}" class="btn">{{label}}</a> \
        {{/views}} \
      </ul> \
      <div class="recline-results-info"> \
        Results found <span class="doc-count">{{docCount}}</span> \
      </div> \
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

  initialize: function(options) {
    var self = this;
    this.el = $(this.el);
    this.config = _.extend({
        readOnly: false
      },
      options.config);
    if (this.config.readOnly) {
      this.setReadOnly();
    }
    // Hash of 'page' views (i.e. those for whole page) keyed by page name
    if (options.views) {
      this.pageViews = options.views;
    } else {
      this.pageViews = [{
        id: 'grid',
        label: 'Grid',
        view: new my.DataGrid({
            model: this.model
          })
      }];
    }
    // this must be called after pageViews are created
    this.render();

    this.router = new Backbone.Router();
    this.setupRouting();

    this.model.bind('query:start', function() {
        my.notify('Loading data', {loader: true});
      });
    this.model.bind('query:done', function() {
        my.clearNotifications();
        self.el.find('.doc-count').text(self.model.docCount || 'Unknown');
        my.notify('Data loaded', {category: 'success'});
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
        self.el.find('.doc-count').text(self.model.docCount || 'Unknown');
        self.model.query();
      })
      .fail(function(error) {
        my.notify(error.message, {category: 'error', persist: true});
      });
  },

  setReadOnly: function() {
    this.el.addClass('read-only');
  },

  render: function() {
    var tmplData = this.model.toTemplateJSON();
    tmplData.displayCount = this.config.displayCount;
    tmplData.views = this.pageViews;
    var template = $.mustache(this.template, tmplData);
    $(this.el).html(template);
    var $dataViewContainer = this.el.find('.data-view-container');
    _.each(this.pageViews, function(view, pageName) {
      $dataViewContainer.append(view.view.el)
    });
    var queryEditor = new my.QueryEditor({
      model: this.model.queryState
    });
    this.el.find('.header').append(queryEditor.el);
  },

  setupRouting: function() {
    var self = this;
    // Default route
    this.router.route('', this.pageViews[0].id, function() {
      self.updateNav(self.pageViews[0].id);
    });
    $.each(this.pageViews, function(idx, view) {
      self.router.route(/^([^?]+)(\?.*)?/, 'view', function(viewId, queryString) {
        self.updateNav(viewId, queryString);
      });
    });
  },

  updateNav: function(pageName, queryString) {
    this.el.find('.navigation li').removeClass('active');
    this.el.find('.navigation li a').removeClass('disabled');
    var $el = this.el.find('.navigation li a[href=#' + pageName + ']');
    $el.parent().addClass('active');
    $el.addClass('disabled');
    // show the specific page
    _.each(this.pageViews, function(view, idx) {
      if (view.id === pageName) {
        view.view.el.show();
      } else {
        view.view.el.hide();
      }
    });
  }
});


my.QueryEditor = Backbone.View.extend({
  className: 'recline-query-editor', 
  template: ' \
    <form action="" method="GET" class="form-inline"> \
      <input type="text" name="q" value="{{q}}" class="text-query" /> \
      <div class="pagination"> \
        <ul> \
          <li class="prev action-pagination-update"><a>&laquo;</a></li> \
          <li class="active"><a><input name="from" type="text" value="{{from}}" /> &ndash; <input name="to" type="text" value="{{to}}" /> </a></li> \
          <li class="next action-pagination-update"><a>&raquo;</a></li> \
        </ul> \
      </div> \
      <button type="submit" class="btn" style="">Update &raquo;</button> \
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
    var newFrom = parseInt(this.el.find('input[name="from"]').val());
    var newSize = parseInt(this.el.find('input[name="to"]').val()) - newFrom;
    var query = this.el.find('.text-query').val();
    this.model.set({size: newSize, from: newFrom, q: query});
  },
  onPaginationUpdate: function(e) {
    e.preventDefault();
    var $el = $(e.target);
    if ($el.parent().hasClass('prev')) {
      var newFrom = this.model.get('from') - Math.max(0, this.model.get('size'));
    } else {
      var newFrom = this.model.get('from') + this.model.get('size');
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


/* ========================================================== */
// ## Miscellaneous Utilities

var urlPathRegex = /^([^?]+)(\?.*)?/;

// Parse the Hash section of a URL into path and query string
my.parseHashUrl = function(hashUrl) {
  var parsed = urlPathRegex.exec(hashUrl);
  if (parsed == null) {
    return {};
  } else {
    return {
      path: parsed[1],
      query: parsed[2] || ''
    }
  }
}

// Parse a URL query string (?xyz=abc...) into a dictionary.
my.parseQueryString = function(q) {
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
}

// Parse the query string out of the URL hash
my.parseHashQueryString = function() {
  q = my.parseHashUrl(window.location.hash).query;
  return my.parseQueryString(q);
}

// Compse a Query String
my.composeQueryString = function(queryParams) {
  var queryString = '?';
  var items = [];
  $.each(queryParams, function(key, value) {
    items.push(key + '=' + JSON.stringify(value));
  });
  queryString += items.join('&');
  return queryString;
}

my.setHashQueryString = function(queryParams) {
  window.location.hash = window.location.hash.split('?')[0] + my.composeQueryString(queryParams);
}

// ## notify
//
// Create a notification (a div.alert in div.alert-messsages) using provide messages and options. Options are:
//
// * category: warning (default), success, error
// * persist: if true alert is persistent, o/w hidden after 3s (default = false)
// * loader: if true show loading spinner
my.notify = function(message, options) {
  if (!options) var options = {};
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
  _templated = $(_templated).appendTo($('.data-explorer .alert-messages'));
  if (!options.persist) {
    setTimeout(function() {
      $(_templated).fadeOut(1000, function() {
        $(this).remove();
      });
    }, 1000);
  }
}

// ## clearNotifications
//
// Clear all existing notifications
my.clearNotifications = function() {
  var $notifications = $('.data-explorer .alert-messages .alert');
  $notifications.remove();
}

})(jQuery, recline.View);

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
    'click .okButton': 'onSubmit'
    , 'keydown .expression-preview-code': 'onEditorKeydown'
  },

  initialize: function() {
    this.el = $(this.el);
  },

  render: function() {
    var htmls = $.mustache(this.template, 
      {name: this.state.currentColumn}
      )
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
      realDoc.save().then(onCompletedUpdate).fail(onCompletedUpdate)
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
// # Recline Backends
//
// Backends are connectors to backend data sources and stores
//
// This is just the base module containing various convenience methods.
this.recline = this.recline || {};
this.recline.Backend = this.recline.Backend || {};

(function($, my) {
  // ## Backbone.sync
  //
  // Override Backbone.sync to hand off to sync function in relevant backend
  Backbone.sync = function(method, model, options) {
    return model.backend.sync(method, model, options);
  }

  // ## wrapInTimeout
  // 
  // Crude way to catch backend errors
  // Many of backends use JSONP and so will not get error messages and this is
  // a crude way to catch those errors.
  my.wrapInTimeout = function(ourFunction) {
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
  my.DataProxy = Backbone.Model.extend({
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
      var base = this.get('dataproxy_url');
      var data = {
        url: dataset.get('url')
        , 'max-results':  queryObj.size
        , type: dataset.get('format')
      };
      var jqxhr = $.ajax({
        url: base
        , data: data
        , dataType: 'jsonp'
      });
      var dfd = $.Deferred();
      my.wrapInTimeout(jqxhr).done(function(results) {
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
        dfd.resolve(_out);
      })
      .fail(function(arguments) {
        dfd.reject(arguments);
      });
      return dfd.promise();
    }
  });
  recline.Model.backends['dataproxy'] = new my.DataProxy();


}(jQuery, this.recline.Backend));
this.recline = this.recline || {};
this.recline.Backend = this.recline.Backend || {};

(function($, my) {
  // ## ElasticSearch Backend
  //
  // Connecting to [ElasticSearch](http://www.elasticsearch.org/).
  //
  // To use this backend ensure your Dataset has one of the following
  // attributes (first one found is used):
  //
  // <pre>
  // elasticsearch_url
  // webstore_url
  // url
  // </pre>
  //
  // This should point to the ES type url. E.G. for ES running on
  // localhost:9200 with index twitter and type tweet it would be
  //
  // <pre>http://localhost:9200/twitter/tweet</pre>
  my.ElasticSearch = Backbone.Model.extend({
    _getESUrl: function(dataset) {
      var out = dataset.get('elasticsearch_url');
      if (out) return out;
      out = dataset.get('webstore_url');
      if (out) return out;
      out = dataset.get('url');
      return out;
    },
    sync: function(method, model, options) {
      var self = this;
      if (method === "read") {
        if (model.__type__ == 'Dataset') {
          var base = self._getESUrl(model);
          var schemaUrl = base + '/_mapping';
          var jqxhr = $.ajax({
            url: schemaUrl,
            dataType: 'jsonp'
          });
          var dfd = $.Deferred();
          my.wrapInTimeout(jqxhr).done(function(schema) {
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
        }
      } else {
        alert('This backend currently only supports read operations');
      }
    },
    _normalizeQuery: function(queryObj) {
      if (queryObj.toJSON) {
        var out = queryObj.toJSON();
      } else {
        var out = _.extend({}, queryObj);
      }
      if (out.q != undefined && out.q.trim() === '') {
        delete out.q;
      }
      if (!out.q) {
        out.query = {
          match_all: {}
        }
      } else {
        out.query = {
          query_string: {
            query: out.q
          }
        }
        delete out.q;
      }
      return out;
    },
    query: function(model, queryObj) {
      var queryNormalized = this._normalizeQuery(queryObj);
      var data = {source: JSON.stringify(queryNormalized)};
      var base = this._getESUrl(model);
      var jqxhr = $.ajax({
        url: base + '/_search',
        data: data,
        dataType: 'jsonp'
      });
      var dfd = $.Deferred();
      // TODO: fail case
      jqxhr.done(function(results) {
        model.docCount = results.hits.total;
        var docs = _.map(results.hits.hits, function(result) {
          var _out = result._source;
          _out.id = result._id;
          return _out;
        });
        dfd.resolve(docs);
      });
      return dfd.promise();
    }
  });
  recline.Model.backends['elasticsearch'] = new my.ElasticSearch();

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
  my.GDoc = Backbone.Model.extend({
    sync: function(method, model, options) {
      var self = this;
      if (method === "read") { 
        var dfd = $.Deferred(); 
        var dataset = model;

        $.getJSON(model.get('url'), function(d) {
          result = self.gdocsToJavascript(d);
          model.fields.reset(_.map(result.field, function(fieldId) {
              return {id: fieldId};
            })
          );
          // cache data onto dataset (we have loaded whole gdoc it seems!)
          model._dataCache = result.data;
          dfd.resolve(model);
        })
        return dfd.promise(); }
    },

    query: function(dataset, queryObj) { 
      var dfd = $.Deferred();
      var fields = _.pluck(dataset.fields.toJSON(), 'id');

      // zip the fields with the data rows to produce js objs
      // TODO: factor this out as a common method with other backends
      var objs = _.map(dataset._dataCache, function (d) { 
        var obj = {};
        _.each(_.zip(fields, d), function (x) { obj[x[0]] = x[1]; })
        return obj;
      });
      dfd.resolve(objs);
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
              var col = k.substr(4)
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
  recline.Model.backends['gdocs'] = new my.GDoc();

}(jQuery, this.recline.Backend));

this.recline = this.recline || {};
this.recline.Backend = this.recline.Backend || {};

(function($, my) {
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
  my.Memory = Backbone.Model.extend({
    initialize: function() {
      this.datasets = {};
    },
    addDataset: function(data) {
      this.datasets[data.metadata.id] = $.extend(true, {}, data);
    },
    sync: function(method, model, options) {
      var self = this;
      if (method === "read") {
        var dfd = $.Deferred();
        if (model.__type__ == 'Dataset') {
          var rawDataset = this.datasets[model.id];
          model.set(rawDataset.metadata);
          model.fields.reset(rawDataset.fields);
          model.docCount = rawDataset.documents.length;
          dfd.resolve(model);
        }
        return dfd.promise();
      } else if (method === 'update') {
        var dfd = $.Deferred();
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
        var dfd = $.Deferred();
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
      var numRows = queryObj.size;
      var start = queryObj.from;
      var dfd = $.Deferred();
      results = this.datasets[model.id].documents;
      // not complete sorting!
      _.each(queryObj.sort, function(sortObj) {
        var fieldName = _.keys(sortObj)[0];
        results = _.sortBy(results, function(doc) {
          var _out = doc[fieldName];
          return (sortObj[fieldName].order == 'asc') ? _out : -1*_out;
        });
      });
      var results = results.slice(start, start+numRows);
      dfd.resolve(results);
      return dfd.promise();
    }
  });
  recline.Model.backends['memory'] = new my.Memory();

}(jQuery, this.recline.Backend));
this.recline = this.recline || {};
this.recline.Backend = this.recline.Backend || {};

(function($, my) {
  // ## Webstore Backend
  //
  // Connecting to [Webstores](http://github.com/okfn/webstore)
  //
  // To use this backend ensure your Dataset has a webstore_url in its attributes.
  my.Webstore = Backbone.Model.extend({
    sync: function(method, model, options) {
      if (method === "read") {
        if (model.__type__ == 'Dataset') {
          var base = model.get('webstore_url');
          var schemaUrl = base + '/schema.json';
          var jqxhr = $.ajax({
            url: schemaUrl,
              dataType: 'jsonp',
              jsonp: '_callback'
          });
          var dfd = $.Deferred();
          my.wrapInTimeout(jqxhr).done(function(schema) {
            var fieldData = _.map(schema.data, function(item) {
              item.id = item.name;
              delete item.name;
              return item;
            });
            model.fields.reset(fieldData);
            model.docCount = schema.count;
            dfd.resolve(model, jqxhr);
          })
          .fail(function(arguments) {
            dfd.reject(arguments);
          });
          return dfd.promise();
        }
      }
    },
    query: function(model, queryObj) {
      var base = model.get('webstore_url');
      var data = {
        _limit:  queryObj.size
        , _offset: queryObj.from
      };
      var jqxhr = $.ajax({
        url: base + '.json',
        data: data,
        dataType: 'jsonp',
        jsonp: '_callback',
        cache: true
      });
      var dfd = $.Deferred();
      jqxhr.done(function(results) {
        dfd.resolve(results.data);
      });
      return dfd.promise();
    }
  });
  recline.Model.backends['webstore'] = new my.Webstore();

}(jQuery, this.recline.Backend));
