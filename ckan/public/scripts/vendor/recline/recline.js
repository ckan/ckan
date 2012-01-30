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
  
  function updateDocs(editFunc) {
    var dfd = $.Deferred();
    util.notify("Download entire database into Recline. This could take a while...", {persist: true, loader: true});
    couch.request({url: app.baseURL + "api/json"}).then(function(docs) {
      util.notify("Updating " + docs.docs.length + " documents. This could take a while...", {persist: true, loader: true});
      var toUpdate = costco.mapDocs(docs.docs, editFunc).edited;
      costco.uploadDocs(toUpdate).then(
        function(updatedDocs) { 
          util.notify(updatedDocs.length + " documents updated successfully");
          recline.initializeTable(app.offset);
          dfd.resolve(updatedDocs);
        },
        function(err) {
          util.notify("Errorz! " + err);
          dfd.reject(err);
        }
      );
    });
    return dfd.promise();
  }
  
  function updateDoc(doc) {
    return couch.request({type: "PUT", url: app.baseURL + "api/" + doc._id, data: JSON.stringify(doc)})    
  }

  function uploadDocs(docs) {
    var dfd = $.Deferred();
    if(!docs.length) dfd.resolve("Failed: No docs specified");
    couch.request({url: app.baseURL + "api/_bulk_docs", type: "POST", data: JSON.stringify({docs: docs})})
      .then(
        function(resp) {ensureCommit().then(function() { 
          var error = couch.responseError(resp);
          if (error) {
            dfd.reject(error);
          } else {
            dfd.resolve(resp);            
          }
        })}, 
        function(err) { dfd.reject(err.responseText) }
      );
    return dfd.promise();
  }
  
  function ensureCommit() {
    return couch.request({url: app.baseURL + "api/_ensure_full_commit", type:'POST', data: "''"});
  }
  
  function deleteColumn(name) {
    var deleteFunc = function(doc) {
      delete doc[name];
      return doc;
    }
    return updateDocs(deleteFunc);
  }
  
  function uploadCSV() {
    var file = $('#file')[0].files[0];
    if (file) {
      var reader = new FileReader();
      reader.readAsText(file);
      reader.onload = function(event) {
        var payload = {
          url: window.location.href + "/api/_bulk_docs", // todo more robust url composition
          data: event.target.result
        };
        var worker = new Worker('script/costco-csv-worker.js');
        worker.onmessage = function(event) {
          var message = event.data;
          if (message.done) {
            var error = couch.responseError(JSON.parse(message.response))
            console.log('e',error)
            if (error) {
              app.emitter.emit(error, 'error');
            } else {
              util.notify("Data uploaded successfully!");
              recline.initializeTable(app.offset);
            }
            util.hide('dialog');
          } else if (message.percent) {
            if (message.percent === 100) {
              util.notify("Waiting for CouchDB...", {persist: true, loader: true})
            } else {
              util.notify("Uploading... " + message.percent + "%");            
            }
          } else {
            util.notify(JSON.stringify(message));
          }
        };
        worker.postMessage(payload);
      };
    } else {
      util.notify('File not selected. Please try again');
    }
  };

  return {
    evalFunction: evalFunction,
    previewTransform: previewTransform,
    mapDocs: mapDocs,
    updateDocs: updateDocs,
    updateDoc: updateDoc,
    uploadDocs: uploadDocs,
    deleteColumn: deleteColumn,
    ensureCommit: ensureCommit,
    uploadCSV: uploadCSV 
  };
}();
this.recline = this.recline || {};

// Models module following classic module pattern
recline.Model = function($) {

var my = {};

// A Dataset model.
//
// Other than standard list of Backbone attributes it has two important attributes:
//
// * currentDocuments: a DocumentList containing the Documents we have currently loaded for viewing (you update currentDocuments by calling getRows)
// * docCount: total number of documents in this dataset (obtained on a fetch for this Dataset)
my.Dataset = Backbone.Model.extend({
  __type__: 'Dataset',
  initialize: function() {
    this.currentDocuments = new my.DocumentList();
    this.docCount = null;
  },

  // AJAX method with promise API to get rows (documents) from the backend.
  //
  // Resulting DocumentList are used to reset this.currentDocuments and are
  // also returned.
  //
  // :param numRows: passed onto backend getDocuments.
  // :param start: passed onto backend getDocuments.
  //
  // this does not fit very well with Backbone setup. Backbone really expects you to know the ids of objects your are fetching (which you do in classic RESTful ajax-y world). But this paradigm does not fill well with data set up we have here.
  // This also illustrates the limitations of separating the Dataset and the Backend
  getDocuments: function(numRows, start) {
    var self = this;
    var dfd = $.Deferred();
    this.backend.getDocuments(this.id, numRows, start).then(function(rows) {
      var docs = _.map(rows, function(row) {
        return new my.Document(row);
      });
      self.currentDocuments.reset(docs);
      dfd.resolve(self.currentDocuments);
    });
    return dfd.promise();
  },

  toTemplateJSON: function() {
    var data = this.toJSON();
    data.docCount = this.docCount;
    return data;
  }
});

my.Document = Backbone.Model.extend({
  __type__: 'Document'
});

my.DocumentList = Backbone.Collection.extend({
  __type__: 'DocumentList',
  // webStore: new WebStore(this.url),
  model: my.Document
});

// Backends section
// ================

my.setBackend = function(backend) {
  Backbone.sync = backend.sync;
};

// Backend which just caches in memory
// 
// Does not need to be a backbone model but provides some conveniences
my.BackendMemory = Backbone.Model.extend({
  // Initialize a Backend with a local in-memory dataset.
  // 
  // NB: We can handle one and only one dataset at a time.
  //
  // :param dataset: the data for a dataset on which operations will be
  // performed. Its form should be a hash with metadata and data
  // attributes.
  //
  // - metadata: hash of key/value attributes of any kind (but usually with title attribute)
  // - data: hash with 2 keys:
  //  - headers: list of header names/labels
  //  - rows: list of hashes, each hash being one row. A row *must* have an id attribute which is unique.
  //
  //  Example of data:
  // 
  //        {
  //            headers: ['x', 'y', 'z']
  //          , rows: [
  //              {id: 0, x: 1, y: 2, z: 3}
  //            , {id: 1, x: 2, y: 4, z: 6}
  //          ]
  //        };
  initialize: function(dataset) {
    // deep copy
    this._datasetAsData = $.extend(true, {}, dataset);
    _.bindAll(this, 'sync');
  }, 
  getDataset: function() {
    var dataset = new my.Dataset({
      id: this._datasetAsData.metadata.id
    });
    // this is a bit weird but problem is in sync this is set to parent model object so need to give dataset a reference to backend explicitly
    dataset.backend = this;
    return dataset;
  },
  sync: function(method, model, options) {
    var self = this;
    if (method === "read") {
      var dfd = $.Deferred();
      // this switching on object type is rather horrible
      // think may make more sense to do work in individual objects rather than in central Backbone.sync
      if (model.__type__ == 'Dataset') {
        var dataset = model;
        var rawDataset = this._datasetAsData;
        dataset.set(rawDataset.metadata);
        dataset.set({
          headers: rawDataset.data.headers
          });
        dataset.docCount = rawDataset.data.rows.length;
        dfd.resolve(dataset);
      }
      return dfd.promise();
    } else if (method === 'update') {
      var dfd = $.Deferred();
      if (model.__type__ == 'Document') {
        _.each(this._datasetAsData.data.rows, function(row, idx) {
          if(row.id === model.id) {
            self._datasetAsData.data.rows[idx] = model.toJSON();
          }
        });
        dfd.resolve(model);
      }
      return dfd.promise();
    } else if (method === 'delete') {
      var dfd = $.Deferred();
      if (model.__type__ == 'Document') {
        this._datasetAsData.data.rows = _.reject(this._datasetAsData.data.rows, function(row) {
          return (row.id === model.id);
        });
        dfd.resolve(model);
      }
      return dfd.promise();
    } else {
      alert('Not supported: sync on BackendMemory with method ' + method + ' and model ' + model);
    }
  },
  getDocuments: function(datasetId, numRows, start) {
    if (start === undefined) {
      start = 0;
    }
    if (numRows === undefined) {
      numRows = 10;
    }
    var dfd = $.Deferred();
    rows = this._datasetAsData.data.rows;
    var results = rows.slice(start, start+numRows);
    dfd.resolve(results);
    return dfd.promise();
 }
});

// Webstore Backend for connecting to the Webstore
//
// Initializing model argument must contain a url attribute pointing to
// relevant Webstore table.
//
// Designed to only attach to one dataset and one dataset only ...
// Could generalize to support attaching to different datasets
my.BackendWebstore = Backbone.Model.extend({
  getDataset: function(id) {
    var dataset = new my.Dataset({
      id: id
    });
    dataset.backend = this;
    return dataset;
  },
  sync: function(method, model, options) {
    if (method === "read") {
      // this switching on object type is rather horrible
      // think may make more sense to do work in individual objects rather than in central Backbone.sync
      if (this.__type__ == 'Dataset') {
        var dataset = this;
        // get the schema and return
        var base = this.backend.get('url');
        var schemaUrl = base + '/schema.json';
        var jqxhr = $.ajax({
          url: schemaUrl,
          dataType: 'jsonp',
          jsonp: '_callback'
          });
        var dfd = $.Deferred();
        jqxhr.then(function(schema) {
          headers = _.map(schema.data, function(item) {
            return item.name;
          });
          dataset.set({
            headers: headers
          });
          dataset.docCount = schema.count;
          dfd.resolve(dataset, jqxhr);
        });
        return dfd.promise();
      }
    }
  },
  getDocuments: function(datasetId, numRows, start) {
    if (start === undefined) {
      start = 0;
    }
    if (numRows === undefined) {
      numRows = 10;
    }
    var base = this.get('url');
    var jqxhr = $.ajax({
      url: base + '.json?_limit=' + numRows,
      dataType: 'jsonp',
      jsonp: '_callback',
      cache: true
      });
    var dfd = $.Deferred();
    jqxhr.then(function(results) {
      dfd.resolve(results.data);
    });
    return dfd.promise();
 }
});

// DataProxy Backend for connecting to the DataProxy
//
// Example initialization:
//
//     BackendDataProxy({
//       model: {
//         url: {url-of-data-to-proxy},
//         type: xls || csv,
//         format: json || jsonp # return format (defaults to jsonp)
//         dataproxy: {url-to-proxy} # defaults to http://jsonpdataproxy.appspot.com
//       }
//     })
my.BackendDataProxy = Backbone.Model.extend({
  defaults: {
    dataproxy: 'http://jsonpdataproxy.appspot.com'
    , type: 'csv'
    , format: 'jsonp'
  },
  getDataset: function(id) {
    var dataset = new my.Dataset({
      id: id
    });
    dataset.backend = this;
    return dataset;
  },
  sync: function(method, model, options) {
    if (method === "read") {
      // this switching on object type is rather horrible
      // think may make more sense to do work in individual objects rather than in central Backbone.sync
      if (this.__type__ == 'Dataset') {
        var dataset = this;
        // get the schema and return
        var base = this.backend.get('dataproxy');
        var data = this.backend.toJSON();
        delete data['dataproxy'];
        // TODO: should we cache for extra efficiency
        data['max-results'] = 1;
        var jqxhr = $.ajax({
          url: base
          , data: data
          , dataType: 'jsonp'
        });
        var dfd = $.Deferred();
        jqxhr.then(function(results) {
          dataset.set({
            headers: results.fields
          });
          dfd.resolve(dataset, jqxhr);
        });
        return dfd.promise();
      }
    } else {
      alert('This backend only supports read operations');
    }
  },
  getDocuments: function(datasetId, numRows, start) {
    if (start === undefined) {
      start = 0;
    }
    if (numRows === undefined) {
      numRows = 10;
    }
    var base = this.get('dataproxy');
    var data = this.toJSON();
    delete data['dataproxy'];
    data['max-results'] = numRows;
    var jqxhr = $.ajax({
      url: base
      , data: data
      , dataType: 'jsonp'
      // , cache: true
      });
    var dfd = $.Deferred();
    jqxhr.then(function(results) {
      var _out = _.map(results.data, function(row) {
        var tmp = {};
        _.each(results.fields, function(key, idx) {
          tmp[key] = row[idx];
        });
        return tmp;
      });
      dfd.resolve(_out);
    });
    return dfd.promise();
 }
});

return my;

}(jQuery);

var util = function() {
  var templates = {
    transformActions: '<li><a data-action="transform" class="menuAction" href="JavaScript:void(0);">Global transform...</a></li>'
    , columnActions: ' \
      <li><a data-action="bulkEdit" class="menuAction" href="JavaScript:void(0);">Transform...</a></li> \
      <li><a data-action="deleteColumn" class="menuAction" href="JavaScript:void(0);">Delete this column</a></li> \
    '
    , rowActions: '<li><a data-action="deleteRow" class="menuAction" href="JavaScript:void(0);">Delete this row</a></li>'
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

  function inURL(url, str) {
    var exists = false;
    if ( url.indexOf( str ) > -1 ) {
      exists = true;
    }
    return exists;
  }
  
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

  function notify(message, options) {
    if (!options) var options = {};
    var tmplData = _.extend({
      msg: message,
      category: 'warning'
      },
      options);
    var _template = ' \
      <div class="alert-message {{category}} fade in" data-alert="alert"><a class="close" href="#">×</a> \
        <p>{{msg}} \
          {{#loader}} \
          <img src="images/small-spinner.gif" class="notification-loader"> \
          {{/loader}} \
        </p> \
      </div>';
    var _templated = $.mustache(_template, tmplData); 
    _templated = $(_templated).appendTo($('.data-explorer .alert-messages'));
    if (!options.persist) {
      setTimeout(function() {
        $(_templated).remove();
      }, 3000);
    }
  }
  
  function formatMetadata(data) {
    out = '<dl>';
    $.each(data, function(key, val) {
      if (typeof(val) == 'string' && key[0] != '_') {
        out = out + '<dt>' + key + '<dd>' + val;
      } else if (typeof(val) == 'object' && key != "geometry" && val != null) {
        if (key == 'properties') {
          $.each(val, function(attr, value){
            out = out + '<dt>' + attr + '<dd>' + value;
          })
        } else {
          out = out + '<dt>' + key + '<dd>' + val.join(', ');
        }
      }
    });
    out = out + '</dl>';
    return out;
  }

  function getBaseURL(url) {
    var baseURL = "";
    if ( inURL(url, '_design') ) {
      if (inURL(url, '_rewrite')) {
        var path = url.split("#")[0];
        if (path[path.length - 1] === "/") {
          baseURL = "";
        } else {
          baseURL = '_rewrite/';
        }
      } else {
        baseURL = '_rewrite/';
      }
    }
    return baseURL;
  }
  
  var persist = {
    restore: function() {
      $('.persist').each(function(i, el) {
        var inputId = $(el).attr('id');
        if(localStorage.getItem(inputId)) $('#' + inputId).val(localStorage.getItem(inputId));
      })
    },
    save: function(id) {
      localStorage.setItem(id, $('#' + id).val());
    },
    clear: function() {
      $('.persist').each(function(i, el) {
        localStorage.removeItem($(el).attr('id'));
      })
    }
  }
  
  // simple debounce adapted from underscore.js
  function delay(func, wait) {
    return function() {
      var context = this, args = arguments;
      var throttler = function() {
        delete app.timeout;
        func.apply(context, args);
      };
      if (!app.timeout) app.timeout = setTimeout(throttler, wait);      
    };
  };
  
  function resetForm(form) {
    $(':input', form)
     .not(':button, :submit, :reset, :hidden')
     .val('')
     .removeAttr('checked')
     .removeAttr('selected');
  }
  
  function largestWidth(selector, min) {
    var min_width = min || 0;
    $(selector).each(function(i, n){
        var this_width = $(n).width();
        if (this_width > min_width) {
            min_width = this_width;
        }
    });
    return min_width;
  }
  
  function getType(obj) {
    if (obj === null) {
      return 'null';
    }
    if (typeof obj === 'object') {
      if (obj.constructor.toString().indexOf("Array") !== -1) {
        return 'array';
      } else {
        return 'object';
      }
    } else {
      return typeof obj;
    }
  }
  
  function lookupPath(path) {
    var docs = app.apiDocs;
    try {
      _.each(path, function(node) {
        docs = docs[node];
      })
    } catch(e) {
      util.notify("Error selecting documents" + e);
      docs = [];
    }
    return docs;
  }
  
  function nodePath(docField) {
    if (docField.children('.object-key').length > 0) return docField.children('.object-key').text();
    if (docField.children('.array-key').length > 0) return docField.children('.array-key').text();
    if (docField.children('.doc-key').length > 0) return docField.children('.doc-key').text();
    return "";
  }
  
  function selectedTreePath() {
    var nodes = []
      , parent = $('.chosen');
    while (parent.length > 0) {
      nodes.push(nodePath(parent));
      parent = parent.parents('.doc-field:first');
    }
    return _.compact(nodes).reverse();
  }
  
  // TODO refactor handlers so that they dont stack up as the tree gets bigger
  function handleTreeClick(e) {
    var clicked = $(e.target);
    if(clicked.hasClass('expand')) return;
    if (clicked.children('.array').length > 0) {
      var field = clicked;
    } else if (clicked.siblings('.array').length > 0) {
      var field = clicked.parents('.doc-field:first');
    } else {
      var field = clicked.parents('.array').parents('.doc-field:first');
    }
    $('.chosen').removeClass('chosen');
    field.addClass('chosen');
    return false;
  }
  
  var createTreeNode = {
    "string": function (obj, key) {
      var val = $('<div class="doc-value string-type"></div>');
      if (obj[key].length > 45) {
        val.append($('<span class="string-type"></span>')
        .text(obj[key].slice(0, 45)))
        .append(
          $('<span class="expand">...</span>')
          .click(function () {
            val.html('')
            .append($('<span class="string-type"></span>')
              .text(obj[key].length ? obj[key] : "   ")
            )
          })
        )
      }
      else {
        var val = $('<div class="doc-value string-type"></div>');
        val.append(
          $('<span class="string-type"></span>')
          .text(obj[key].length ? obj[key] : "   ")
        )
      }
      return val;
    }
    , "number": function (obj, key) {
      var val = $('<div class="doc-value number"></div>')
      val.append($('<span class="number-type">' + obj[key] + '</span>'))
      return val;
    }
    , "null": function (obj, key) {
      var val = $('<div class="doc-value null"></div>')
      val.append($('<span class="null-type">' + obj[key] + '</span>'))
      return val;
    }
    , "boolean": function (obj, key) {
      var val = $('<div class="fue null"></div>')
      val.append($('<span class="null-type">' + obj[key] + '</span>'))
      return val;
    }
    , "array": function (obj, key, indent) {
       if (!indent) indent = 1;
        var val = $('<div class="doc-value array"></div>')
        $('<span class="array-type">[</span><span class="expand" style="float:left">...</span><span class="array-type">]</span>')
          .click(function (e) {
            var n = $(this).parent();
            var cls = 'sub-'+key+'-'+indent
            n.html('')
            n.append('<span style="padding-left:'+((indent - 1) * 10)+'px" class="array-type">[</span>')
            for (i in obj[key]) {
              var field = $('<div class="doc-field"></div>').click(handleTreeClick);
              n.append(
                field
                  .append('<div class="array-key '+cls+'" >'+i+'</div>')
                  .append(createTreeNode[getType(obj[key][i])](obj[key], i, indent + 1))
                )
            }
            n.append('<span style="padding-left:'+((indent - 1) * 10)+'px" class="array-type">]</span>')
            $('div.'+cls).width(largestWidth('div.'+cls))
          })
          .appendTo($('<div class="array-type"></div>').appendTo(val))
        return val;
    }
    , "object": function (obj, key, indent) {
      if (!indent) indent = 1;
      var val = $('<div class="doc-value object"></div>')
      $('<span class="object-type">{</span><span class="expand" style="float:left">...</span><span class="object-type">}</span>')
        .click(function (e) {
          var n = $(this).parent();
          n.html('')
          n.append('<span style="padding-left:'+((indent - 1) * 10)+'px" class="object-type">{</span>')
          for (i in obj[key]) {
            var field = $('<div class="doc-field"></div>').click(handleTreeClick);
            var p = $('<div class="id-space" style="margin-left:'+(indent * 10)+'px"/>');
            var di = $('<div class="object-key">'+i+'</div>')
            field.append(p)
              .append(di)
              .append(createTreeNode[getType(obj[key][i])](obj[key], i, indent + 1))
            n.append(field)
          }

          n.append('<span style="padding-left:'+((indent - 1) * 10)+'px" class="object-type">}</span>')
          di.width(largestWidth('div.object-key'))
        })
        .appendTo($('<div class="object-type"></div>').appendTo(val))
      return val;
    }
  }

  function renderTree(doc) {
    var d = $('div#document-editor');
    for (i in doc) {
      var field = $('<div class="doc-field"></div>').click(handleTreeClick);
      $('<div class="id-space" />').appendTo(field);    
      field.append('<div class="doc-key doc-key-base">'+i+'</div>')
      field.append(createTreeNode[getType(doc[i])](doc, i));
      d.append(field);
    }

    $('div.doc-key-base').width(largestWidth('div.doc-key-base'))
  }
  
  
  return {
    inURL: inURL,
    registerEmitter: registerEmitter,
    listenFor: listenFor,
    show: show,
    hide: hide,
    position: position,
    render: render,
    notify: notify,
    observeExit: observeExit,
    formatMetadata:formatMetadata,
    getBaseURL:getBaseURL,
    resetForm: resetForm,
    delay: delay,
    persist: persist,
    lookupPath: lookupPath,
    selectedTreePath: selectedTreePath,
    renderTree: renderTree
  };
}();
this.recline = this.recline || {};

// Views module following classic module pattern
recline.View = function($) {

var my = {};

// Parse a URL query string (?xyz=abc...) into a dictionary.
function parseQueryString(q) {
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

// The primary view for the entire application.
//
// It should be initialized with a recline.Model.Dataset object and an existing
// dom element to attach to (the existing DOM element is important for
// rendering of FlotGraph subview).
// 
// To pass in configuration options use the config key in initialization hash
// e.g.
//
//      var explorer = new DataExplorer({
//        config: {...}
//      })
//
// Config options:
//
// * displayCount: how many documents to display initially (default: 10)
// * readOnly: true/false (default: false) value indicating whether to
//   operate in read-only mode (hiding all editing options).
//
// All other views as contained in this one.
my.DataExplorer = Backbone.View.extend({
  template: ' \
  <div class="data-explorer"> \
    <div class="alert-messages"></div> \
    \
    <div class="header"> \
      <ul class="navigation"> \
        <li class="active"><a href="#grid" class="btn">Grid</a> \
        <li><a href="#graph" class="btn">Graph</a></li> \
      </ul> \
      <div class="pagination"> \
        <form class="display-count"> \
          Showing 0 to <input name="displayCount" type="text" value="{{displayCount}}" title="Edit and hit enter to change the number of rows displayed" /> of  <span class="doc-count">{{docCount}}</span> \
        </form> \
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

  events: {
    'submit form.display-count': 'onDisplayCountUpdate'
  },

  initialize: function(options) {
    var self = this;
    this.el = $(this.el);
    this.config = _.extend({
        displayCount: 50
        , readOnly: false
      },
      options.config);
    if (this.config.readOnly) {
      this.setReadOnly();
    }
    // Hash of 'page' views (i.e. those for whole page) keyed by page name
    this.pageViews = {
      grid: new my.DataTable({
          model: this.model
        })
      , graph: new my.FlotGraph({
          model: this.model
        })
    };
    // this must be called after pageViews are created
    this.render();

    this.router = new Backbone.Router();
    this.setupRouting();

    // retrieve basic data like headers etc
    // note this.model and dataset returned are the same
    this.model.fetch().then(function(dataset) {
      self.el.find('.doc-count').text(self.model.docCount || 'Unknown');
      // initialize of dataTable calls render
      self.model.getDocuments(self.config.displayCount);
    });
  },

  onDisplayCountUpdate: function(e) {
    e.preventDefault();
    this.config.displayCount = parseInt(this.el.find('input[name="displayCount"]').val());
    this.model.getDocuments(this.config.displayCount);
  },

  setReadOnly: function() {
    this.el.addClass('read-only');
  },

  render: function() {
    var tmplData = this.model.toTemplateJSON();
    tmplData.displayCount = this.config.displayCount;
    var template = $.mustache(this.template, tmplData);
    $(this.el).html(template);
    var $dataViewContainer = this.el.find('.data-view-container');
    _.each(this.pageViews, function(view, pageName) {
      $dataViewContainer.append(view.el)
    });
  },

  setupRouting: function() {
    var self = this;
    this.router.route('', 'grid', function() {
      self.updateNav('grid');
    });
    this.router.route(/grid(\?.*)?/, 'view', function(queryString) {
      self.updateNav('grid', queryString);
    });
    this.router.route(/graph(\?.*)?/, 'graph', function(queryString) {
      self.updateNav('graph', queryString);
      // we have to call here due to fact plot may not have been able to draw
      // if it was hidden until now - see comments in FlotGraph.redraw
      qsParsed = parseQueryString(queryString);
      if ('graph' in qsParsed) {
        var chartConfig = JSON.parse(qsParsed['graph']);
        _.extend(self.pageViews['graph'].chartConfig, chartConfig);
      }
      self.pageViews['graph'].redraw();
    });
  },

  updateNav: function(pageName, queryString) {
    this.el.find('.navigation li').removeClass('active');
    var $el = this.el.find('.navigation li a[href=#' + pageName + ']');
    $el.parent().addClass('active');
    // show the specific page
    _.each(this.pageViews, function(view, pageViewName) {
      if (pageViewName === pageName) {
        view.el.show();
      } else {
        view.el.hide();
      }
    });
  }
});

// DataTable provides a tabular view on a Dataset.
//
// Initialize it with a recline.Dataset object.
my.DataTable = Backbone.View.extend({
  tagName:  "div",
  className: "data-table-container",

  initialize: function() {
    var self = this;
    this.el = $(this.el);
    _.bindAll(this, 'render');
    this.model.currentDocuments.bind('add', this.render);
    this.model.currentDocuments.bind('reset', this.render);
    this.model.currentDocuments.bind('remove', this.render);
    this.state = {};
  },

  events: {
    'click .column-header-menu': 'onColumnHeaderClick'
    , 'click .row-header-menu': 'onRowHeaderClick'
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
    this.state.currentColumn = $(e.target).siblings().text();
    util.position('data-table-menu', e);
    util.render('columnActions', 'data-table-menu');
  },

  onRowHeaderClick: function(e) {
    this.state.currentRow = $(e.target).parents('tr:first').attr('data-id');
    util.position('data-table-menu', e);
    util.render('rowActions', 'data-table-menu');
  },

  onMenuClick: function(e) {
    var self = this;
    e.preventDefault();
    var actions = {
      bulkEdit: function() { self.showTransformColumnDialog('bulkEdit', {name: self.state.currentColumn}) },
      transform: function() { self.showTransformDialog('transform') },
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
            util.notify("Row deleted successfully");
          })
          .fail(function(err) {
            util.notify("Errorz! " + err)
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
    var view = new my.DataTransform({
    });
    view.render();
    $el.empty();
    $el.append(view.el);
    util.observeExit($el, function() {
      util.hide('dialog');
    })
    $('.dialog').draggable({ handle: '.dialog-header', cursor: 'move' });
  },


  // ======================================================
  // Core Templating
  template: ' \
    <div class="data-table-menu-overlay" style="display: none; z-index: 101; ">&nbsp;</div> \
    <ul class="data-table-menu"></ul> \
    <table class="data-table" cellspacing="0"> \
      <thead> \
        <tr> \
          {{#notEmpty}}<th class="column-header"></th>{{/notEmpty}} \
          {{#headers}} \
            <th class="column-header"> \
              <div class="column-header-title"> \
                <a class="column-header-menu"></a> \
                <span class="column-header-name">{{.}}</span> \
              </div> \
              </div> \
            </th> \
          {{/headers}} \
        </tr> \
      </thead> \
      <tbody></tbody> \
    </table> \
  ',

  toTemplateJSON: function() {
    var modelData = this.model.toJSON()
    modelData.notEmpty = ( modelData.headers.length > 0 )
    return modelData;
  },
  render: function() {
    var self = this;
    var htmls = $.mustache(this.template, this.toTemplateJSON());
    this.el.html(htmls);
    this.model.currentDocuments.forEach(function(doc) {
      var tr = $('<tr />');
      self.el.find('tbody').append(tr);
      var newView = new my.DataTableRow({
          model: doc,
          el: tr,
          headers: self.model.get('headers')
        });
      newView.render();
    });
    return this;
  }
});

// DataTableRow View for rendering an individual document.
//
// Since we want this to update in place it is up to creator to provider the element to attach to.
// In addition you must pass in a headers in the constructor options. This should be list of headers for the DataTable.
my.DataTableRow = Backbone.View.extend({
  initialize: function(options) {
    _.bindAll(this, 'render');
    this._headers = options.headers;
    this.el = $(this.el);
    this.model.bind('change', this.render);
  },
  template: ' \
      <td><a class="row-header-menu"></a></td> \
      {{#cells}} \
      <td data-header="{{header}}"> \
        <div class="data-table-cell-content"> \
          <a href="javascript:{}" class="data-table-cell-edit" title="Edit this cell">&nbsp;</a> \
          <div class="data-table-cell-value">{{value}}</div> \
        </div> \
      </td> \
      {{/cells}} \
    ',
  events: {
    'click .data-table-cell-edit': 'onEditClick',
    // cell editor
    'click .data-table-cell-editor .okButton': 'onEditorOK',
    'click .data-table-cell-editor .cancelButton': 'onEditorCancel'
  },
  
  toTemplateJSON: function() {
    var doc = this.model;
    var cellData = _.map(this._headers, function(header) {
      return {header: header, value: doc.get(header)}
    })
    return { id: this.id, cells: cellData }
  },

  render: function() {
    this.el.attr('data-id', this.model.id);
    var html = $.mustache(this.template, this.toTemplateJSON());
    $(this.el).html(html);
    return this;
  },

  // ======================================================
  // Cell Editor

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
    var header = cell.parents('td').attr('data-header');
    var newValue = cell.parents('.data-table-cell-editor').find('.data-table-cell-editor-editor').val();
    var newData = {};
    newData[header] = newValue;
    this.model.set(newData);
    util.notify("Updating row...", {loader: true});
    this.model.save().then(function(response) {
        util.notify("Row updated successfully", {category: 'success'});
      })
      .fail(function() {
        util.notify('Error saving row', {
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
      util.notify("Error with function! " + editFunc.errorMessage);
      return;
    }
    util.hide('dialog');
    util.notify("Updating all visible docs. This could take a while...", {persist: true, loader: true});
      var docs = self.model.currentDocuments.map(function(doc) {
       return doc.toJSON();
      });
    // TODO: notify about failed docs? 
    var toUpdate = costco.mapDocs(docs, editFunc).edited;
    var totalToUpdate = toUpdate.length;
    function onCompletedUpdate() {
      totalToUpdate += -1;
      if (totalToUpdate === 0) {
        util.notify(toUpdate.length + " documents updated successfully");
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


// Graph view for a Dataset using Flot graphing library.
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
          {{#headers}} \
          <option value="{{.}}">{{.}}</option> \
          {{/headers}} \
          </select> \
        </div> \
        <div class="editor-series-group"> \
          <div class="editor-series"> \
            <label>Series <span>A (y-axis)</span></label> \
            <div class="input"> \
              <select> \
              {{#headers}} \
              <option value="{{.}}">{{.}}</option> \
              {{/headers}} \
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
    // we need the model.headers to render properly
    this.model.bind('change', this.render);
    this.model.currentDocuments.bind('add', this.redraw);
    this.model.currentDocuments.bind('reset', this.redraw);
    this.chartConfig = _.extend({
        group: null,
        series: [],
        graphType: 'line'
      },
      config)
    this.render();
  },

  toTemplateJSON: function() {
    return this.model.toJSON();
  },

  render: function() {
    htmls = $.mustache(this.template, this.toTemplateJSON());
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
    window.location.hash = window.location.hash.split('?')[0] +
        '?graph=' + JSON.stringify(this.chartConfig);
    this.redraw();
  },

  redraw: function() {
    // There appear to be issues generating a Flot graph if either:

    // * The relevant div that graph attaches to his hidden at the moment of creating the plot -- Flot will complain with
    //
    //   Uncaught Invalid dimensions for plot, width = 0, height = 0
    // * There is no data for the plot -- either same error or may have issues later with errors like 'non-existent node-value' 
    var areWeVisible = !jQuery.expr.filters.hidden(this.el[0]);
    if (!this.plot && (!areWeVisible || this.model.currentDocuments.length == 0)) {
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

return my;

}(jQuery);

