this.CKAN = this.CKAN || {};

this.CKAN.Client = (function (CKAN, $, _, Backbone, undefined) {

  // Client constructor. Creates a new client for communicating with
  // the CKAN API.
  function Client(config) {
    this._environment = {};
    this.configure(config || Client.defaults);

    _.bindAll(this, 'syncDataset', '_datasetConverter');
  }

  // Default config parameters for the Client.
  Client.defaults = {
    apiKey: '',
    endpoint: 'http://ckan.net'
  };

  // Extend the Client prototype with Backbone.Events to provide .bind(),
  // .unbind() and .trigger() methods.
  _.extend(Client.prototype, Backbone.Events, {

    cache: {
      dataset: new Backbone.Collection()
    },

    // Allows the implementor to specify an object literal of settings to
    // configure the current client. Options include:
    //
    // - apiKey: The API key for the current user to create/edit datasets.
    // - endpoint: The API endpoint to connect to.
    configure: function (config) {
      config = config || {};
      if (config.endpoint) {
        config.endpoint = config.endpoint.replace(/\/$/, '');
        config.restEndpoint   = config.endpoint + '/api/2/rest';
        config.searchEndpoint = config.endpoint + '/api/2/search';
      }
      return this.environment(config);
    },

    // Client environment getter/setter. Environment variables can be retrieved
    // by providing a key string, if the key does not exist the method will
    // return `undefined`. To set keys either a key value pair can be provided
    // or an object literal containing multiple key/value pairs.
    environment: function (key, value) {
      if (typeof key === "string") {
        if (arguments.length === 1) {
          return this._environment[key];
        }
        this._environment[key] = value;
      } else {
        _.extend(this._environment, key);
      }
      return this;
    },

    // Helper method to fetch datasets from the server. Using this method to
    // fetch datasets will ensure that only one instance of a model per server
    // resource exists on the page at one time.
    //
    // The method accepts the dataset `"id"` and an object of `"options"`, these
    // can be any options accepted by the `.fetch()` method on `Backbone.Model`.
    // If the model already exists it will simply be returned otherwise an empty
    // model will be returned and the data requested from the server.
    //
    //     var dataset = client.getDatasetById('my-data-id', {
    //       success: function () {
    //         // The model is now populated.
    //       },
    //       error: function (xhr) {
    //         // Something went wrong check response status etc.
    //       }
    //     });
    //
    getDatasetById: function (id, options) {
      var cache   = this.cache.dataset,
          dataset = cache.get(id);
      var ourOptions = options || {};

      if (!dataset) {
        dataset = this.createDataset({id: id});

        // Add the stub dataset to the global cache to ensure that only one
        // is ever created.
        cache.add(dataset);
        
        // Fetch the dataset from the server passing in any options provided.
        // Also set up a callback to remove the model from the cache in
        // case of error.
        ourOptions.error = function () {
          cache.remove(dataset);
        };
        // TODO: RP not sure i understand what this does and why it is needed
        dataset.fetch(ourOptions);
      }
      return dataset;
    },

    // Helper method to create a new instance of CKAN.Model.Dataset and
    // register a sync listener to update the representation on the server when
    // the model is created/updated/deleted.
    //
    //     var myDataset = client.createDataset({
    //       title: "My new data set"
    //     });
    //
    // This ensures that the models are always saved with the latest environment
    // data.
    createDataset: function (attributes) {
      return (new CKAN.Model.Dataset(attributes)).bind('sync', this.syncDataset);
    },

    // A wrapper around Backbone.sync() that adds additional ajax options to
    // each request. These include the API key and the request url rather than
    // using the model to generate it.
    syncDataset: function (method, model, options) {
      // Get the package url.
      var url = this.environment('restEndpoint') + '/package';

      // Add additional request options.
      options = _.extend({}, {
        url: model.isNew() ? url : url + '/' + model.id,
        headers: {
          'X-CKAN-API-KEY': this.environment('apiKey')
        }
      }, options);

      Backbone.sync(method, model, options);
      return this;
    },

    // Performs a search for datasets against the CKAN API. The `options`
    // argument can contain any keys supported by jQuery.ajax(). The query
    // parameters should be provided in the `options.query` property.
    //
    //     var query = client.searchDatasets({
    //       success: function (datasets) {
    //         console.log(datasets); // Logs a Backbone.Collection
    //       }
    //     });
    //
    // The `options.success` method (and any other success callbacks) will
    // recieve a `SearchCollection` containing `Dataset` models. The method
    // returns a jqXHR object so that additional callbacks can be registered
    // with .success() and .error().
    searchDatasets: function (options) {
      options = options || {};
      options.data = _.defaults(options.query, {'limit': 10, 'all_fields': 1});
      delete options.query;

      return $.ajax(_.extend({
        url: this.environment('searchEndpoint') + '/package',
        converters: {
          'text json': this._datasetConverter
        }
      }, options));
    },

    // A "converter" method for jQuery.ajax() this is used to convert the
    // results from a search API request into models which in turn will be
    // passed into any registered success callbacks. We do this here so that
    // _all_ registered success callbacks recieve the same data rather than
    // just the callback registered when the search was made.
    _datasetConverter: function (raw) {
      var json = $.parseJSON(raw),
          models = _.map(json.results, function (attributes) {
            return this.createDataset(attributes);
          }, this);

      return new CKAN.Model.SearchCollection(models, {total: json.count});
    },

    // Performs a query on CKAN API.
    // The `options` argument can contain any keys supported by jQuery.ajax().
    // In addition it should contain either a url or offset variable. If
    // offset provided it will be used to construct the full api url by
    // prepending the endpoint plus 'api' (i.e. offset of '/2/rest/package'
    // will become '{endpoint}/api/2/rest'.
    //
    // The `options.success` method (and any other success callbacks) will
    // recieve a `SearchCollection` containing `Dataset` models. The method
    // returns a jqXHR object so that additional callbacks can be registered
    // with .success() and .error().
    apiCall: function (options) {
      options = options || {};
      // Add additional request options.
      options = _.extend({}, {
        url: this.environment('endpoint') + '/api' + options.offset,
        headers: {
          'X-CKAN-API-KEY': this.environment('apiKey')
        }
      }, options);

      return $.ajax(options);
    },

    // wrap CKAN /api/storage/auth/form - see http://packages.python.org/ckanext-storage
    // params and returns value are as for that API
    // key is file label/path 
    getStorageAuthForm: function(key, options) {
      options.offset = '/storage/auth/form/' + key;
      this.apiCall(options);
    }
  });

  return Client;

})(this.CKAN, this.$, this._, this.Backbone);
this.CKAN = this.CKAN || {};

// Global object that stores all CKAN models.
CKAN.Model = function ($, _, Backbone, undefined) {

  var Model = {};

  // Simple validator helper returns a `validate()` function that checks
  // the provided model keys and returns an error object if these do not
  // exist on the model or the attributes object provided.\
  //
  //     validate: validator('title', 'description', url)
  //
  function validator() {
    var required = arguments;
    return function (attrs) {
      var errors;
      if (attrs) {
        _.each(required, function (key) {
          if (!attrs[key] && !this.get(key)) {
            if (!errors) {
              errors = {};
            }
            errors[key] = 'The "' + key + '" is required';
          }
        }, this);
      }
      return errors;
    };
  }

  // A Base model that all CKAN models inherit from. Methods that should be
  // shared across all models should be defined here.
  Model.Base = Backbone.Model.extend({

    // Extend the default Backbone.Model constructor simply to provide a named
    // function. This improves debugging in consoles such as the Webkit inspector.
    constructor: function Base(attributes, options) {
      Backbone.Model.prototype.constructor.apply(this, arguments);
    },

    // Rather than letting the models connect to the server themselves we
    // leave this to the implementor to decide how models are saved. This allows
    // the API details such as API key and enpoints to change without having
    // to update the models. When `.save()` or `.destroy()` is called the
    // `"sync"` event will be published with the arguments provided to `.sync()`.
    //
    //     var package = new Package({name: 'My Package Name'});
    //     package.bind('sync', Backbone.sync);
    //
    // This method returns itself for chaining.
    sync: function () {
      return this.trigger.apply(this, ['sync'].concat(_.toArray(arguments)));
    },

    // Overrides the standard `toJSON()` method to serialise any nested
    // Backbone models and collections (or any other object that has a `toJSON()`
    // method).
    toJSON: function () {
      var obj = Backbone.Model.prototype.toJSON.apply(this, arguments);
      _.each(obj, function (value, key) {
        if (value && typeof value === 'object' && value.toJSON) {
          obj[key] = value.toJSON();
        }
      });
      return obj;
    }
  });

  // Model objects
  Model.Dataset = Model.Base.extend({
    constructor: function Dataset() {
      // Define an key/model mapping for child relationships. These will be
      // managed as a Backbone collection when setting/getting the key.
      this.children = {
        resources: Model.Resource,
        relationships: Model.Relationship
      };
      Model.Base.prototype.constructor.apply(this, arguments);
    },

    defaults: {
      title: '',
      name: '',
      notes: '',
      resources: [],
      tags: []
    },

    // Override the `set()` method on `Backbone.Model` to handle resources as
    // relationships. This will now manually update the `"resouces"` collection
    // (using `_updateResources()`) with any `Resource` models provided rather
    // than replacing the key.
    set: function (attributes, options) {
      var children, validated;

      // If not yet defined set the child collections. This will be done when
      // set is called for the first time in the constructor.
      this._createChildren();

      // Check to see if any child keys are present in the attributes and
      // remove them from the object. Then update them seperately after the
      // parent `set()` method has been called.
      _.each(this.children, function (Model, key) {
        if (attributes && attributes[key]) {
          if (!(attributes[key] instanceof Backbone.Collection)) {
            if (!children) {
              children = {};
            }
            children[key] = attributes[key];
            delete attributes[key];
          }
        }
      }, this);

      validated = Model.Base.prototype.set.call(this, attributes, options);

      // Ensure validation passed before updating child models.
      if (validated && children) {
        this._updateChildren(children);
      }

      return validated;
    },

    // Checks to see if our model instance has Backbone collections defined for
    // child keys. If they do not exist it creates them.
    _createChildren: function () {
      _.each(this.children, function (Model, key) {
        if (!this.get(key)) {
          var newColl = new Backbone.Collection();
          this.attributes[key] = newColl;
          newColl.model = Model;
          // bind change events so updating the children trigger change on Dataset
          var self = this;
          // TODO: do we want to do all or be more selective
          newColl.bind('all', function() {
            self.trigger('change');
          });
        }
      }, this);
      return this;
    },

    // Manages the one to many relationship between resources and the dataset.
    // Accepts an array of Resources (ideally model instances but will convert
    // object literals into resources for you). New models will be added to the
    // collection and existing ones updated. Any pre-existing models not found
    // in the new array will be removed.
    _updateChildren: function (children) {
      _.each(children, function (models, key) {
        var collection = this.get(key),
            ids = {};

        // Add/Update models.
        _.each(models, function (model) {
          var existing = collection.get(model.id),
              isLiteral = !(model instanceof this.children[key]);

          // Provide the dataset key if not already there and current model is
          // not a relationship.
          if (isLiteral && key !== 'relationships') {
            model.dataset = this;
            delete model.package_id;
          }

          if (!existing) {
            collection.add(model);
          }
          else if (existing && isLiteral) {
            existing.set(model);
          }

          ids[model.id] = 1;
        }, this);

        // Remove missing models.
        collection.remove(collection.select(function (model) {
          return !ids[model.id];
        }));
      }, this);
      return this;
    },

    // NOTE: Returns localised URL.
    toTemplateJSON: function () {
      var out = this.toJSON();
      var title = this.get('title');
      out.displaytitle = title ? title : 'No title ...';
      var notes = this.get('notes');
      // Don't use a global Showdown; CKAN doesn't need that library
      var showdown = new Showdown.converter();
      out.notesHtml = showdown.makeHtml(notes ? notes : '');
      out.snippet = this.makeSnippet(out.notesHtml);
      return out;
    },

    makeSnippet: function (notesHtml) {
      var out = $(notesHtml).text();
      if (out.length > 190) {
        out = out.slice(0, 190) + ' ...';
      }
      return out;
    }
  });

  // A model for working with resources. Each resource is _required_ to have a
  // parent `Dataset`. This must be provided under the `"dataset"` key when the
  // `Resource` is created. This is handled for you when creating resources
  // via the `Dataset` `set()` method.
  //
  // The `save()`, `fetch()` and `delete()` methods are mapped to the parent
  // dataset and can be used to update a Resource's metadata.
  //
  //     var resource = new Model.Resource({
  //       name: 'myresource.csv',
  //       url:  'http://www.example.com/myresource.csv',
  //       dataset: dataset
  //     });
  //
  //     // Updates the resource name on the server by saving the parent dataset
  //     resource.set({name: 'Some new name'});
  //
  Model.Resource = Model.Base.extend({
    constructor: function Resource() {
      Model.Base.prototype.constructor.apply(this, arguments);
    },

    // Override the `save()` method to update the Resource with attributes then
    // call the parent dataset and save that. Any `options` provided will be
    // passed on to the dataset `save()` method.
    save: function (attrs, options) {
      var validated = this.set(attrs);
      if (validated) {
        return this.get('dataset').save({}, options);
      }
      return validated;
    },

    // Override the `fetch()` method to call `fetch()` on the parent dataset.
    fetch: function (options) {
      return this.get('dataset').fetch(options);
    },

    // Override the `fetch()` method to trigger the `"destroy"` event which
    // will remove it from any collections then save the parent dataset.
    destroy: function (options) {
      return this.trigger('destroy', this).get('dataset').save({}, options);
    },

    // Override the `toJSON()` method to set the `"package_id"` key required
    // by the server.
    toJSON: function () {
      // Call Backbone.Model rather than Base to break the circular reference.
      var obj = Backbone.Model.prototype.toJSON.apply(this, arguments);
      if (obj.dataset) {
        obj.package_id = obj.dataset.id;
        delete obj.dataset;
      } else {
        obj.package_id = null;
      }
      return obj;
    },

    toTemplateJSON: function() {
      var obj = Backbone.Model.prototype.toJSON.apply(this, arguments);
      obj.displaytitle = obj.description ? obj.description : 'No description ...';
      return obj;
    },

    // Validates the provided attributes. Returns an object literal of
    // attribute/error pairs if invalid, `undefined` otherwise.
    validate: validator('url')
  });

  // Helper function that returns a stub method that warns the devloper that
  // this method has not yet been implemented.
  function apiPlaceholder(method) {
    var console = window.console;
    return function () {
      if (console && console.warn) {
        console.warn('The method "' + method + '" has not yet been implemented');
      }
      return this;
    };
  }

  // A model for working with relationship objects. These are currently just the
  // realtionship objects returned by the server wrapped in a `Base` model
  // instance. Currently there is no save or delete functionality.
  Model.Relationship = Model.Base.extend({
    constructor: function Relationship() {
      Model.Base.prototype.constructor.apply(this, arguments);
    },

    // Add placeholder method that simply returns itself to all methods that
    // interact with the server. This will also log a warning message to the
    // developer into the console.
    save: apiPlaceholder('save'),
    fetch: apiPlaceholder('fetch'),
    destroy: apiPlaceholder('destroy'),

    // Validates the provided attributes. Returns an object literal of
    // attribute/error pairs if invalid, `undefined` otherwise.
    validate: validator('object', 'subject', 'type')
  });

  // Collection for managing results from the CKAN search API. An additional
  // `options.total` parameter can be provided on initialisation to
  // indicate how many models there are on the server in total. This can
  // then be accessed via the `total` property.
  Model.SearchCollection = Backbone.Collection.extend({
    constructor: function SearchCollection(models, options) {
      if (options) {
        this.total = options.total;
      }
      Backbone.Collection.prototype.constructor.apply(this, arguments);
    }
  });

  return Model;

}(this.jQuery, this._, this.Backbone);
var CKAN = CKAN || {};

CKAN.Templates = {
  minorNavigationDataset: ' \
    <ul class="tabbed"> \
      <li><a href="#dataset/${dataset.id}/view">View</a></li> \
      <li><a href="#dataset/${dataset.id}/edit">Edit</a></li> \
    </ul> \
    '
};
var CKAN = CKAN || {};

CKAN.View = function($) {
  var my = {};

  // Flash a notification message
  // 
  // Parameters: msg, type. type is set as class on notification and should be one of success, error.
  // If type not defined defaults to success
  my.flash = function(msg, type) {
    if (type === undefined) {
      var type = 'success'
    }
    $.event.trigger('notification', [msg, type]);
  };

  my.NotificationView = Backbone.View.extend({
    initialize: function() {
      $.template('notificationTemplate',
          '<div class="flash-banner ${type}">${message} <button>X</button></div>');

      var self = this;
      $(document).bind('notification', function(e, msg, type) {
        self.render(msg, type)
      });
    },

    events: {
      'click .flash-banner button': 'hide'
    },

    render: function(msg, type) {
      var _out = $.tmpl('notificationTemplate', {'message': msg, 'type': type})
      this.el.html(_out);
      this.el.slideDown(400);
    },

    hide: function() {
      this.el.slideUp(200);
    }
  });

  my.ConfigView = Backbone.View.extend({
    initialize: function() {
      this.cfg = {};
      this.$ckanUrl = this.el.find('input[name=ckan-url]');
      this.$apikey = this.el.find('input[name=ckan-api-key]');

      var cfg = this.options.config;
      this.$ckanUrl.val(cfg.endpoint);
      this.$apikey.val(cfg.apiKey);
    },

    events: {
      'submit #config-form': 'updateConfig'
    },

    updateConfig: function(e) {
      e.preventDefault();
      this.saveConfig();
      CKAN.View.flash('Saved configuration');
    },

    saveConfig: function() {
      this.cfg = {
        'endpoint': this.$ckanUrl.val(),
        'apiKey': this.$apikey.val()
      };
      $.event.trigger('config:update', this.cfg);
    }
  });

  my.DatasetEditView = Backbone.View.extend({
    initialize: function() {
      _.bindAll(this, 'saveData', 'render');
      this.model.bind('change', this.render);
    },

    render: function() {
      tmplData = {
        dataset: this.model.toTemplateJSON()
      }
      var tmpl = $.tmpl(CKAN.Templates.datasetForm, tmplData);
      $(this.el).html(tmpl);
      if (tmplData.dataset.id) { // edit not add
        $('#minornavigation').html($.tmpl(CKAN.Templates.minorNavigationDataset, tmplData));
      }
      return this;
    },

    events: {
      'submit form.dataset': 'saveData',
      'click .previewable-textarea a': 'togglePreview',
      'click .dataset-form-navigation a': 'showFormPart'
    },

    showFormPart: function(e) {
      e.preventDefault();
      var action = $(e.target)[0].href.split('#')[1];
      $('.dataset-form-navigation a').removeClass('selected');
      $('.dataset-form-navigation a[href=#' + action + ']').addClass('selected');
    },

    saveData: function(e) {
      e.preventDefault();
      this.model.set(this.getData());
      this.model.save({}, {
        success: function(model) {
          CKAN.View.flash('Saved dataset');
          window.location.hash = '#dataset/' + model.id + '/view';
        },
        error: function(model, error) {
          CKAN.View.flash('Error saving dataset ' + error.responseText, 'error');
        }
      });
    },

    getData: function() {
      var _data = $(this.el).find('form.dataset').serializeArray();
      modelData = {};
      $.each(_data, function(idx, value) {
        modelData[value.name.split('--')[1]] = value.value
      });
      return modelData;
    },

    togglePreview: function(e) {
      // set model data as we use it below for notesHtml
      this.model.set(this.getData());
      e.preventDefault();
      var el = $(e.target);
      var action = el.attr('action');
      var div = el.closest('.previewable-textarea');
      div.find('.tabs a').removeClass('selected');
      div.find('.tabs a[action='+action+']').addClass('selected');
      var textarea = div.find('textarea');
      var preview = div.find('.preview');
      if (action=='preview') {
        preview.html(this.model.toTemplateJSON().notesHtml);
        textarea.hide();
        preview.show();
      } else {
        textarea.show();
        preview.hide();
      }
      return false;
    }

  });

  my.DatasetFullView = Backbone.View.extend({
    initialize: function() {
      _.bindAll(this, 'render');
      this.model.bind('change', this.render);

      // slightly painful but we have to set this up here so
      // it has access to self because when called this will
      // be overridden and refer to the element in dom that
      // was being saved
      var self = this;
      this.saveFromEditable = function(value, settings) {
        var _attribute = $(this).attr('backbone-attribute');
        var _data = {};
        _data[_attribute] = value;
        self.model.set(_data);
        self.model.save({}, {
          success: function(model) {
            CKAN.View.flash('Saved updated notes');
          },
          error: function(model, error) {
            CKAN.View.flash('Error saving notes ' + error.responseText, 'error');
          }
        });
        // do not worry too much about what we return here
        // because update of model will automatically lead to
        // re-render
        return value;
      };
    },

    events: {
      'click .action-add-resource': 'showResourceAdd'
    },

    render: function() {
      var tmplData = {
        domain: this.options.domain,
        dataset: this.model.toTemplateJSON(),
      };
      $('.page-heading').html(tmplData.dataset.displaytitle);
      $('#minornavigation').html($.tmpl(CKAN.Templates.minorNavigationDataset, tmplData));
      $('#sidebar .widget-list').html($.tmpl(CKAN.Templates.sidebarDatasetView, tmplData));
      this.el.html($.tmpl(CKAN.Templates.datasetView, tmplData));
      this.setupEditable();
      return this;
    },

    setupEditable: function() {
      var self = this;
      this.el.find('.editable-area').editable(
        self.saveFromEditable, {
          type      : 'textarea',
          cancel    : 'Cancel',
          submit    : 'OK',
          tooltip   : 'Click to edit...',
          onblur    : 'ignore',
          data      : function(value, settings) {
            var _attribute = $(this).attr('backbone-attribute');
            return self.model.get(_attribute);
          }
        }
      );
    },

    showResourceAdd: function(e) {
      var self = this;
      e.preventDefault();
      var $el = $('<div />').addClass('resource-add-dialog');
      $('body').append($el);
      var resource = new CKAN.Model.Resource({
          'dataset': self.model
          });
      function handleNewResourceSave(model) {
        var res = self.model.get('resources');
        res.add(model);
        $el.dialog('close');
        self.model.save({}, {
          success: function(model) {
            CKAN.View.flash('Saved dataset');
            // TODO: no need to re-render (should happen automatically)
            self.render();
          }
          , error: function(model, error) {
            CKAN.View.flash('Failed to save: ' + error, 'error');
          }
        });
      }
      resource.bind('change', handleNewResourceSave);
      var resourceView = new CKAN.View.ResourceCreate({
        el: $el,
        model: resource
      });
      resourceView.render();
      dialogOptions = {
        autoOpen: false,
        // does not seem to work for width ...
        position: ['center', 'center'],
        buttons: [],
        width:  660,
        resize: 'auto',
        modal: false,
        draggable: true,
        resizable: true
      };
      dialogOptions.title = 'Add Data (File, API, ...)';
      $el.dialog(dialogOptions);
      $el.dialog('open');
      $el.bind("dialogbeforeclose", function () {
        self.el.find('.resource-add-dialog').remove();
      });
    }
  });

  my.DatasetSearchView = Backbone.View.extend({
    events: {
      'submit #search-form': 'onSearch'
    },

    initialize: function(options) {
      var view = this;

      // Temporarily provide the view with access to the client for searching.
      this.client = options.client;
      this.$results = this.el.find('.results');
      this.$datasetList = this.$results.find('.datasets');
      this.$dialog = this.el.find('.dialog');

      this.resultView = new CKAN.View.DatasetListing({
        collection: new Backbone.Collection(),
        el: this.$datasetList
      });

      _.bindAll(this, "render");
    },

    render: function() {
      this.$('.count').html(this.totalResults);
      this.hideSpinner();
      this.$results.show();
      return this;
    },

    onSearch: function (event) {
      event.preventDefault();
      var q = $(this.el).find('input.search').val();
      this.doSearch(q);
    },

    doSearch: function (q) {
      $(this.el).find('input.search').val(q),
          self = this;

      this.showSpinner();
      this.$results.hide();
      this.$results.find('.datasets').empty();
      this.client.searchDatasets({
        query: {q:q},
        success: function (collection) {
          self.totalResults = collection.total;
          self.resultView.setCollection(collection);
          self.render();
        }
      });
    },

    showSpinner: function() {
      this.$dialog.empty();
      this.$dialog.html('<h2>Loading results...</h2><img src="http://assets.okfn.org/images/icons/ajaxload-circle.gif" />');
      this.$dialog.show();
    },

    hideSpinner: function() {
      this.$dialog.empty().hide();
    }
  });

  my.ResourceView = Backbone.View.extend({
    render: function() {
      var resourceData = this.model.toTemplateJSON();
      var resourceDetails = {};
      var exclude = [ 'resource_group_id',
        'description',
        'url',
        'position',
        'id',
        'webstore',
        'qa',
        'dataset',
        'displaytitle'
        ];
      $.each(resourceData, function(key, value) {
        if (! _.contains(exclude, key)) {
          resourceDetails[key] = value;
        }
      });
      tmplData = {
        dataset: this.model.get('dataset').toTemplateJSON(),
        resource: resourceData,
        resourceDetails: resourceDetails
      };
      $('.page-heading').html(tmplData.dataset.name + ' / ' + tmplData.resource.displaytitle);
      var tmpl = $.tmpl(CKAN.Templates.resourceView, tmplData);
      $(this.el).html(tmpl);
      return this;
    },

    events: {
    }
  });

  my.ResourceEditView = Backbone.View.extend({
    render: function() {
      var tmpl = $.tmpl(CKAN.Templates.resourceForm, this.model.toJSON());
      $(this.el).html(tmpl);
      return this;
    },

    events: {
      'submit form': 'saveData'
    },

    saveData: function() {
      // only set rather than save as can only save resources as part of a dataset atm
      this.model.set(this.getData(), {
        error: function(model, error) {
          var msg = 'Failed to save, possibly due to invalid data ';
          msg += JSON.stringify(error);
          alert(msg);
        }
      });
      return false;
    },

    getData: function() {
      var _data = $(this.el).find('form.resource').serializeArray();
      modelData = {};
      $.each(_data, function(idx, value) {
        modelData[value.name.split('--')[1]] = value.value
      });
      return modelData;
    }

  });

  return my;
}(jQuery);
var CKAN = CKAN || {};

CKAN.UI = function($) {
  var my = {};

  my.Workspace = Backbone.Router.extend({
    routes: {
      "": "index",
      "search": "search",
      "search/:query": "search",
      "search/:query/p:page": "search",
      "dataset/:id/view": "datasetView",
      "dataset/:id/edit": "datasetEdit",
      "dataset/:datasetId/resource/:resourceId": "resourceView",
      "add-dataset": "datasetAdd",
      "add-resource": "resourceAdd",
      "config": "config"
    },

    initialize: function(options) {
      var self = this;
      var defaultConfig = {
        endpoint: 'http://ckan.net',
        apiKey: ''
      };

      var config = options.config || defaultConfig;
      this.client = new CKAN.Client(config);
      if (options.fixtures && options.fixtures.datasets) {
        $.each(options.fixtures.datasets, function(idx, obj) {
          var collection = self.client.cache.dataset;
          collection.add(new CKAN.Model.Dataset(obj));
        });
      }

      var newPkg = this.client.createDataset();
      var newCreateView = new CKAN.View.DatasetEditView({model: newPkg, el: $('#dataset-add-page')});
      newCreateView.render();

      var newResource = new CKAN.Model.Resource({
        dataset: newPkg
      });
      var newResourceEditView = new CKAN.View.ResourceEditView({model: newResource, el: $('#add-resource-page')});
      newResourceEditView.render();

      var searchView = this.searchView =  new CKAN.View.DatasetSearchView({
        client: this.client,
        el: $('#search-page')
      });

      // set up top bar search
      $('#menusearch').find('form').submit(function(e) {
        e.preventDefault();
        var _el = $(e.target);
        var _q = _el.find('input[name="q"]').val();
        searchView.doSearch(_q);
        self.search(_q);
      });


      var configView = new CKAN.View.ConfigView({
        el: $('#config-page'),
        config: config
      });
      $(document).bind('config:update', function(e, cfg) {
        self.client.configure(cfg);
      });

      this.notificationView = new CKAN.View.NotificationView({
        el: $('.flash-banner-box')
      });
    },

    switchView: function(view) {
      $('.page-view').hide();
      $('#sidebar .widget-list').empty();
      $('#minornavigation').empty();
      $('#' + view + '-page').show();
    },

    index: function(query, page) {
      this.search();
    },

    search: function(query, page) {
      this.switchView('search');
      $('.page-heading').html('Search');
    },

    _findDataset: function(id, callback) {
      var pkg = this.client.getDatasetById(id);

      if (pkg===undefined) {
        pkg = this.client.createDataset({id: id});
        pkg.fetch({
          success: callback,
          error: function() {
            alert('There was an error');
          }
        });
      } else {
        callback(pkg);
      }
    },

    datasetView: function(id) {
      var self = this;
      self.switchView('view');
      var $viewpage = $('#view-page');
      this._findDataset(id, function (model) {
        var newView = new CKAN.View.DatasetFullView({
          model: model,
          el: $viewpage
        });
        newView.render();
      });
    },

    datasetEdit: function(id) {
      this.switchView('dataset-edit');
      $('.page-heading').html('Edit Dataset');
      function _show(model) {
        var newView = new CKAN.View.DatasetEditView({model: model});
        $('#dataset-edit-page').html(newView.render().el);
      }
      this._findDataset(id, _show)
    },

    datasetAdd: function() {
      this.switchView('dataset-add');
      $('.page-heading').html('Add Dataset');
      $('#sidebar .widget-list').empty();
    },

    resourceView: function(datasetId, resourceId) {
      this.switchView('resource-view');
      var $viewpage = $('#resource-view-page');
      this._findDataset(datasetId, function (model) {
        var resource = model.get('resources').get(resourceId);
        var newView = new CKAN.View.ResourceView({
          model: resource,
          el: $viewpage
        });
        newView.render();
      });
    },

    resourceAdd: function() {
      this.switchView('add-resource');
    },

    config: function() {
      this.switchView('config');
    },

    url: function(controller, action, id) {
      if (id) {
        return '#' + controller + '/' + id + '/' + action;
      } else {
        return '#' + controller + '/' + action;
      }
    }
  });
  
  my.initialize = function(options) {
    my.workspace = new my.Workspace(options);
    Backbone.history.start()
  };

  return my;
}(jQuery);

CKAN.Templates.datasetForm = ' \
  <form class="dataset" action="" method="POST"> \
    <dl> \
      <dt> \
        <label class="field_opt" for="dataset--title"> \
          Title * \
        </label> \
      </dt> \
      <dd> \
        <input id="Dataset--title" name="Dataset--title" type="text" value="${dataset.title}" placeholder="A title (not a description) ..."/> \
      </dd> \
 \
      <dt> \
        <label class="field_req" for="Dataset--name"> \
          Name * \
          <span class="hints"> \
            A short unique name for the dataset - used in urls and restricted to [a-z] -_ \
          </span> \
        </label> \
      </dt> \
      <dd> \
        <input id="Dataset--name" maxlength="100" name="Dataset--name" type="text" value="${dataset.name}" placeholder="A shortish name usable in urls ..." /> \
      </dd> \
 \
      <dt> \
        <label class="field_opt" for="Dataset--license_id"> \
          Licence \
        </label> \
      </dt> \
      <dd> \
        <select id="Dataset--license_id" name="Dataset--license_id"> \
          <option selected="selected" value=""></option> \
          <option value="notspecified">Other::License Not Specified</option> \
        </select> \
      </dd> \
 \
      <dt> \
        <label class="field_opt" for="Dataset--notes"> \
          Description and Notes \
          <span class="hints"> \
            (You can use <a href="http://daringfireball.net/projects/markdown/syntax">Markdown formatting</a>) \
          </span> \
        </label> \
      </dt> \
      <dd> \
        <div class="previewable-textarea"> \
          <ul class="tabs"> \
            <li><a href="#" action="write" class="selected">Write</a></li> \
            <li><a href="#" action="preview">Preview</a></li> \
          </ul> \
          <textarea id="Dataset--notes" name="Dataset--notes" placeholder="Start with a summary sentence ...">${dataset.notes}</textarea> \
          <div id="Dataset--notes-preview" class="preview" style="display: none;"> \
          <div> \
        </div> \
      </dd> \
    </dl> \
 \
    <div class="submit"> \
      <input id="save" name="save" type="submit" value="Save" /> \
    </div> \
  </form> \
';

CKAN.Templates.datasetFormSidebar = ' \
  <div class="dataset-form-navigation"> \
    <ul> \
      <li> \
        <a href="#basics" class="selected">Basics</a> \
      </li> \
      <li> \
        <a href="#data">The Data</a> \
      </li> \
      <li> \
        <a href="#additional"> \
          Additional Information \
        </a> \
      </li> \
    </ul> \
  </div> \
';
CKAN.Templates.datasetView = ' \
  <div class="dataset view" dataset-id="${dataset.id}"> \
    <div class="extract"> \
      ${dataset.snippet} \
      {{if dataset.snippet.length > 50}} \
      <a href="#anchor-notes">Read more</a> \
      {{/if}} \
    </div> \
    <div class="tags"> \
      {{if dataset.tags.length}} \
      <ul class="dataset-tags"> \
        {{each dataset.tags}} \
          <li>${$value}</li> \
        {{/each}} \
      </ul> \
      {{/if}} \
    </div> \
    <div class="resources subsection"> \
      <h3>Resources</h3> \
      <table> \
        <tr> \
          <th>Description</th> \
          <th>Format</th> \
          <th>Actions</th> \
        </tr> \
        {{each dataset.resources}} \
        <tr> \
          <td> \
            <a href="#dataset/${dataset.id}/resource/${$value.id}"> \
            {{if $value.description}} \
            ${$value.description} \
            {{else}} \
            (No description) \
            {{/if}} \
            </a> \
          </td> \
          <td>${$value.format}</td> \
          <td><a href="${$value.url}" target="_blank" class="resource-download">Download</a> \
        </tr> \
        {{/each}} \
        {{if !dataset.resources.length }} \
        <tr><td>No resources.</td><td></td></tr> \
        {{/if}} \
      </table> \
      <div class="add-resource"> \
        <a href="#" class="action-add-resource">Add a resource</a> \
      </div> \
    </div> \
    <div class="notes subsection"> \
      <h3 id="anchor-notes">Notes</h3> \
      <div class="notes-body editable-area" backbone-attribute="notes"> \
        {{html dataset.notesHtml}} \
        {{if !dataset.notes || dataset.notes.length === 0}} \
        <em>No notes yet. Click to add some ...</em> \
        {{/if}} \
      </div> \
    </div> \
    <div class="details subsection"> \
      <h3>Additional Information</h3> \
      <table> \
        <thead> \
          <tr> \
            <th>Field</th> \
            <th>Value</th> \
          </tr> \
        </thead> \
        <tbody> \
          <tr> \
            <td>Creator</td> \
            <td>${dataset.author}</td> \
          </tr> \
          <tr> \
            <td>Maintainer</td> \
            <td>${dataset.maintainer}</td> \
          </tr> \
          {{each dataset.extras}} \
          <tr> \
            <td class="package-label" property="rdfs:label">${$index}</td> \
            <td class="package-details" property="rdf:value">${$value}</td> \
          </tr> \
          {{/each}} \
        </tbody> \
      </table> \
    </div> \
  </div> \
';

CKAN.Templates.sidebarDatasetView = ' \
    <li class="widget-container widget_text"> \
      <h3>Connections</h3> \
      <ul> \
        {{each dataset.relationships}} \
        <li> \
          ${$value.type} dataset \
          <a href="#dataset/${$value.object}/view">${$value.object}</a> \
          {{if $value.comment}} \
          <span class="relationship_comment"> \
            (${$value.comment}) \
          </span> \
          {{/if}} \
        </li> \
        {{/each}} \
      </ul> \
      {{if dataset.relationships.length == 0}} \
      No connections to other datasets. \
      {{/if}} \
    </li> \
';
CKAN.Templates.resourceForm = ' \
  <form class="resource" action="" method="POST"> \
    <dl> \
      <dt> \
        <label class="field_opt" for="Resource--url"> \
          Link \
        </label> \
      </dt> \
      <dd> \
        <input id="Resource--url" name="Resource--url" type="text" value="${url}" placeholder="http://mydataset.com/file.csv" /> \
      </dd> \
      <dt> \
        <label class="field_opt" for="Resource--type"> \
          Kind \
        </label> \
      </dt> \
      <dd> \
        <select id="Resource--type" name="Resource--type"> \
          <option selected="selected" value="file">File</option> \
          <option value="api">API</option> \
          <option value="listing">Listing</option> \
          <option value="example">Example</option> \
        </select> \
      </dd> \
    </dl> \
 \
  <fieldset> \
    <legend> \
      <h3>Optional Info</h3> \
    </legend> \
    <dl> \
      <dt> \
        <label class="field_opt" for="Resource--description"> \
          Description \
        </label> \
      </dt> \
      <dd> \
        <input id="Resource--description" name="Resource--description" type="text" value="${description}" placeholder="A short description ..."/> \
      </dd> \
 \
 \
      <dt> \
        <label class="field_opt" for="Resource--format"> \
          Format \
        </label> \
      </dt> \
      <dd> \
        <input id="Resource--format" name="Resource--format" type="text" value="${format}" placeholder="e.g. csv, zip:csv (zipped csv), sparql"/> \
      </dd> \
    </fieldset> \
 \
    <div class="submit"> \
      <input id="save" name="save" type="submit" value="Save" /> \
    </div> \
  </form> \
';

CKAN.Templates.resourceCreate = ' \
  <div class="resource-create"> \
    <table> \
      <tr class="heading"> \
        <td> \
          <h3>Link to data already online</h3> \
        </td> \
        <td><h3>or</h3></td> \
        <td><h3>Upload data</h3></td> \
      </tr> \
      <tr> \
        <td class="edit"></td> \
        <td class="separator"></td> \
        <td class="upload"></td> \
      </tr> \
    </table> \
  </div> \
';
CKAN.Templates.resourceUpload = ' \
<div class="fileupload"> \
  <form action="http://test-ckan-net-storage.commondatastorage.googleapis.com/" class="resource-upload" \
    enctype="multipart/form-data" \
    method="POST"> \
 \
    <div class="fileupload-buttonbar"> \
      <div class="hidden-inputs"></div> \
      <label class="fileinput-button"> \
        File \
      </label> \
      <input type="file" name="file" /> \
      <span class="fileinfo"></span> \
      <input type="submit" value="upload" /> \
    </div> \
  </form> \
  <div class="messages" style="display: none;"></div> \
</div> \
';

CKAN.Templates.resourceView = ' \
  <div class="resource view" resource-id="${resource.id}"> \
    <h3> \
      <a href="${resource.url}" class="url">${resource.url}</a> [${resource.format}] \
    </h3> \
    <div class="description"> \
      ${resource.description} \
    </div> \
    \
    <div class="details subsection"> \
      <h3>Additional Information</h3> \
      <table> \
        <thead> \
          <tr> \
            <th>Field</th> \
            <th>Value</th> \
          </tr> \
        </thead> \
        <tbody> \
          {{each resourceDetails}} \
          <tr> \
            <td class="label">${$index}</td> \
            <td class="value">${$value}</td> \
          </tr> \
          {{/each}} \
        </tbody> \
      </table> \
    </div> \
  </div> \
';
this.CKAN || (this.CKAN = {});
this.CKAN.View || (this.CKAN.View = {});

(function (CKAN, $, _, Backbone, undefined) {
  CKAN.View.DatasetListing = Backbone.View.extend({
    tagName: 'ul',

    constructor: function DatasetListing() {
      Backbone.View.prototype.constructor.apply(this, arguments);

      _.bindAll(this, 'addItem', 'removeItem');

      this.el = $(this.el);
      this.setCollection(this.collection);
    },

    setCollection: function (collection) {
      if (this.collection) {
        this.collection.unbind('add', this.addItem);
        this.collection.unbind('remove', this.removeItem);
      }

      this.collection = collection;
      if (collection) {
        this.collection.bind('add', this.addItem);
        this.collection.bind('remove', this.removeItem);
      }
      return this.render();
    },

    addItem: function (model) {
      var view = new CKAN.View.DatasetListingItem({
        domian: this.options.domain,
        model: model
      });
      this.el.data(model.cid, view).append(view.render().el);
      return this;
    },

    removeItem: function (model) {
      var view = this.el.data(model.cid);
      if (view) {
        view.remove();
      }
      return this;
    },

    render: function () {
      this.el.empty();
      if (this.collection) {
        this.collection.each(this.addItem);
      }
      return this;
    },

    remove: function () {
      this.setCollection(null);
      return Backbone.View.prototype.remove.apply(this, arguments);
    }
  });
  
  CKAN.View.DatasetListingItem = Backbone.View.extend({
    tagName: 'li',

    className: 'dataset summary',

    options: {
      template: '\
        <div class="header"> \
          <span class="title" > \
            <a href="${urls.datasetView}" ckan-attrname="title" class="editable">${displaytitle}</a> \
          </span> \
          <div class="search_meta"> \
            {{if formats.length > 0}} \
            <ul class="dataset-formats"> \
              {{each formats}} \
                <li>${$value}</li> \
              {{/each}} \
            </ul> \
            {{/if}} \
          </div> \
        </div> \
        <div class="extract"> \
          {{html snippet}} \
        </div> \
        <div class="dataset-tags"> \
          {{if tags.length}} \
          <ul class="dataset-tags"> \
            {{each tags}} \
              <li>${$value}</li> \
            {{/each}} \
          </ul> \
          {{/if}} \
        </div> \
      '
    },

    constructor: function DatasetListingItem() {
      Backbone.View.prototype.constructor.apply(this, arguments);
      this.el = $(this.el);
    },

    render: function () {
      var dataset = this.model.toTemplateJSON();
      // if 'UI' mode ...
      var urls = {};
      if (CKAN.UI && CKAN.UI.workspace) {
        urls.datasetView = CKAN.UI.workspace.url('dataset', 'view', this.model.id);
      } else {
        urls.datasetView = dataset.ckan_url;
      }
      var data = _.extend(dataset, {
        dataset: dataset,
        formats: this._availableFormats(),
        urls: urls
      });
      this.el.html($.tmpl(this.options.template, data));
      return this;
    },

    _availableFormats: function () {
      var formats = this.model.get('resources').map(function (resource) {
        return resource.get('format');
      });
      return _.uniq(_.compact(formats));
    }
  });
})(CKAN, $, _, Backbone, undefined);
this.CKAN || (this.CKAN = {});
this.CKAN.View || (this.CKAN.View = {});

(function (CKAN, $, _, Backbone, undefined) {
  CKAN.View.ResourceCreate = Backbone.View.extend({
    initialize: function() {
      this.el = $(this.el);
      _.bindAll(this, 'renderMain');
      this.renderMain();
      this.$edit = $(this.el.find('.edit')[0]);
      this.$upload = $(this.el.find('.upload')[0]);
      this.editView = new CKAN.View.ResourceEditView({
        model: this.model,
        el: this.$edit
      });
      this.uploadView = new CKAN.View.ResourceUpload({
        el: this.$upload,
        model: this.model,
        // TODO: horrible reverse depedency ...
        client: CKAN.UI.workspace.client
      });
    },

    renderMain: function () {
      this.el.empty();
      tmplData = {
      };
      var tmpl = $.tmpl(CKAN.Templates.resourceCreate, tmplData);
      this.el.html(tmpl);
      return this;
    },

    render: function () {
      this.editView.render();
      this.uploadView.render();
    }
  });

})(CKAN, $, _, Backbone, undefined);

this.CKAN || (this.CKAN = {});
this.CKAN.View || (this.CKAN.View = {});

(function (CKAN, $, _, Backbone, undefined) {
  CKAN.View.ResourceUpload = Backbone.View.extend({
    tagName: 'div',

    // expects a client arguments in its options
    initialize: function(options) {
      this.el = $(this.el);
      this.client = options.client;
      _.bindAll(this, 'render', 'updateFormData', 'setMessage', 'uploadFile');
    },

    events: {
      'click input[type="submit"]': 'uploadFile'
    },

    render: function () {
      this.el.empty();
      tmplData = {
      }
      var tmpl = $.tmpl(CKAN.Templates.resourceUpload, tmplData);
      this.el.html(tmpl);
      this.$messages = this.el.find('.alert-message');
      this.setupFileUpload();
      return this;
    },

    setupFileUpload: function() {
      var self = this;
      this.el.find('.fileupload').fileupload({
        // needed because we are posting to remote url 
        forceIframeTransport: true,
        replaceFileInput: false,
        autoUpload: false,
        fail: function(e, data) {
          alert('Upload failed');
        },
        add: function(e,data) {
          self.fileData = data;
          self.fileUploadData = data;
          self.key = self.makeUploadKey(data.files[0].name);
          self.updateFormData(self.key);
        },
        send: function(e, data) {
          self.setMessage('Uploading file ... <img src="http://assets.okfn.org/images/icons/ajaxload-circle.gif" class="spinner" />');
        },
        done: function(e, data) {
          self.onUploadComplete(self.key);
        }
      })
    },

    ISODateString: function(d) {
      function pad(n) {return n<10 ? '0'+n : n};
      return d.getUTCFullYear()+'-'
         + pad(d.getUTCMonth()+1)+'-'
         + pad(d.getUTCDate())+'T'
         + pad(d.getUTCHours())+':'
         + pad(d.getUTCMinutes())+':'
         + pad(d.getUTCSeconds());
    },

    // Create an upload key/label for this file.
    // 
    // Form: {current-date}/file-name. Do not just use the file name as this
    // would lead to collisions.
    // (Could add userid/username and/or a small random string to reduce
    // collisions but chances seem very low already)
    makeUploadKey: function(fileName) {
      // google storage replaces ' ' with '+' which breaks things
      // See http://trac.ckan.org/ticket/1518 for more.
      var corrected = fileName.replace(/ /g, '-');
      // note that we put hh mm ss as hhmmss rather hh:mm:ss (former is 'basic
      // format')
      var now = new Date();
      // replace ':' with nothing
      var str = this.ISODateString(now).replace(':', '').replace(':', '');
      return str  + '/' + corrected;
    },

    updateFormData: function(key) {
      var self = this;
      self.setMessage('Checking upload permissions ... <img src="http://assets.okfn.org/images/icons/ajaxload-circle.gif" class="spinner" />');
      self.el.find('.fileinfo').text(key);
      self.client.getStorageAuthForm(key, {
        async: false,
        success: function(data) {
          self.el.find('form').attr('action', data.action);
          _tmpl = '<input type="hidden" name="${name}" value="${value}" />';
          var $hidden = $(self.el.find('form div.hidden-inputs')[0]);
          $.each(data.fields, function(idx, item) {
            $hidden.append($.tmpl(_tmpl, item));
          });
          self.hideMessage();
        },
        error: function(jqXHR, textStatus, errorThrown) {
          // TODO: more graceful error handling (e.g. of 409)
          self.setMessage('Failed to get credentials for storage upload. Upload cannot proceed', 'error');
          self.el.find('input[name="upload"]').hide();
        }
      });
    },

    uploadFile: function(e) {
      e.preventDefault();
      if (!this.fileData) {
        alert('No file selected');
        return;
      }
      var jqXHR = this.fileData.submit();
    },

    onUploadComplete: function(key) {
      var self = this;
      self.client.apiCall({
        offset: '/storage/metadata/' + self.key,
        success: function(data) {
          var name = data._label;
          if (name && name.length > 0 && name[0] === '/') {
            name = name.slice(1);
          }
          var d = new Date(data._last_modified);
          var lastmod = self.ISODateString(d);
          self.model.set({
              url: data._location
              , name: name
              , size: data._content_length 
              , last_modified: lastmod
              , format: data._format
              , mimetype: data._format
              , resource_type: 'file.upload'
              , owner: data['uploaded-by']
              , hash: data._checksum
              , cache_url: data._location
              , cache_url_updated: lastmod
            }
            , {
              error: function(model, error) {
                var msg = 'Filed uploaded OK but error adding resource: ' + error + '.';
                msg += 'You may need to create a resource directly. Uploaded file at: ' + data._location;
                CKAN.View.flash(msg, 'error');
              }
            }
          );
          self.setMessage('File uploaded OK and resource added', 'success');
          CKAN.View.flash('File uploaded OK and resource added');
        }
      });
    },

    setMessage: function(msg, category) {
      var category = category || 'info';
      this.$messages.removeClass('info success error');
      this.$messages.addClass(category);
      this.$messages.show();
      this.$messages.html(msg);
    },

    hideMessage: function() {
      this.$messages.hide('slow');
    }
  });

})(CKAN, $, _, Backbone, undefined);
