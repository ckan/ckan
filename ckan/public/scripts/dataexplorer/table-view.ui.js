// This file contains all of the UI elements aside from the containing element
// (ie. lightbox) used to build the datapreview widget. The MainView should
// be initiated with an element containing the elements required by the
// subviews.
//
// Use TABLEVIEW.createTableView() to create new instances of MainView.
//
// Examples
//
//   var $element = $(templateString);
//   var datapreview = TABLEVIEW.createTableView($element);
//
//
(function ($, undefined) {

  var ui = {};

  // Binds methods on an object to always be called with the object as the
  // method context.
  //
  // context    - An object with methods to bind.
  // arguments* - Following arguments should be method names to bind.
  //
  // Examples
  //
  //   var object = {
  //     method1: function () {
  //       return this;
  //     },
  //     method2: function () {}
  //   };
  //
  //   bindAll(object, 'method1', 'method2');
  //
  //   object.method1.call(window) === object //=> true;
  //
  // Returns the context argument.
  //
  function bindAll(context) {
    var args = [].slice.call(arguments, 0), i = 0, count = args.length;
    for (; i < count; i += 1) {
      context[args[i]] = $.proxy(context[args[i]], context);
    }
    return context;
  }

  // Creates a new object that inherits from the proto argument.
  //
  // Source: http://github.com/aron/inheritance.js
  //
  // This function will use Object.create() if it exists otherwise falls back
  // to using a dummy constructor function to create a new object instance.
  // Unlike Object.create() this function will always return a new object even
  // if a non object is provided as an argument.
  //
  // proto - An object to use for the new objects internal prototype.
  //
  // Examples
  //
  //   var appleObject = {color: 'green'}
  //   var appleInstance = create(appleObject);
  //
  //   appleInstance.hasOwnProperty('color'); //=> false
  //   appleInstance.color === appleObject.color; //=> true
  //
  // Returns a newly created object.
  //
  function create(proto) {
    if (typeof proto !== 'object') {
      return {};
    }
    else if (Object.create) {
      return Object.create(proto);
    }
    function DummyObject() {}
    DummyObject.prototype = proto;
    return new DummyObject();
  }

  // Public: Creates a new constructor function that inherits from a parent.
  //
  // Source: http://github.com/aron/inheritance.js
  //
  // Instance and static methods can also be provided as additional arguments.
  // if the methods argument has a property called "constructor" this will be
  // used as the constructor function.
  //
  // Static methods will also be copied over from the parent object. However
  // these will not be inheritied prototypally as with the instance methods.
  //
  // parent     - A constructor Function to inherit from.
  // methods    - An Object literal of instance methods that are added to the
  //              constructors prototype.
  // properties - An Object literal of static/class methods to add to the
  //              constructor itself.
  //
  // Examples
  //
  //   function MyObject() {};
  //
  //   var SubClass = inherit(MyObject, {method: function () {}});
  //   var instance = new SubClass();
  //
  //   instance instanceof MyObject //=> true
  //
  // Returns the new constructor Function.
  //
  function inherit(parent, methods, properties) {
    methods = methods || {};

    var Child = methods.hasOwnProperty('constructor') ?
                methods.constructor : inherit.constructor(parent);

    Child.prototype = create(parent.prototype);
    Child.prototype.constructor = Child;

    delete methods.constructor;
    $.extend(Child.prototype, methods, {__super__: parent.prototype});

    return $.extend(Child, parent, properties);
  }

  // Public: Base view object that other views should inherit from.
  //
  // A wrapper around a dom element (itself wrapped in jQuery). Provides useful
  // features such as pub/sub methods, and show/hide toggling of the element.
  //
  // Implements Ben Allman's Tiny PubSub, https://gist.github.com/661855
  //
  // element - A jQuery wrapper, DOM Element or selector String.
  //
  // Examples
  //
  //   var myView = new View('my-element');
  //
  // Returns a new View instance.
  //
  ui.View = inherit({}, {
    constructor: function View(element) {
      this.el = element instanceof $ ? element : $(element);

      // Use a custom empty jQuery wrapper rather than this.el to prevent
      // browser events being triggered.
      this.events = $({});
    },

    // Public: Performs a jQuery lookup within the views element.
    //
    // selector - A selector String to query.
    //
    // Examples
    //
    //   this.$('.some-child-class');
    //
    // Returns a jQuery collection.
    //
    $: function (selector) {
      return this.el.find(selector);
    },

    // Public: Registers a listener for a topic that will be called when the
    // event is triggered. Optionally an Object of topic/callback pairs can
    // be passed to the method. Built on top of the jQuery .bind() method
    // so other features like namespaces can also be used.
    //
    // topic - Topic string to subscribe to.
    // fn    - Callback function to be called when the topic is triggered.
    //
    // Examples
    //
    //   view.bind('my-event', onMyEvent);
    //   view.bind({
    //     'my-event', onMyEvent,
    //     'my-other-events': onMyOtherEvent
    //   });
    //
    // Returns itself for chaining.
    //
    bind: function (topic, fn) {
      if (arguments.length === 1) {
        for (var key in topic) {
          if (topic.hasOwnProperty(key)) {
            this.bind(key, topic[key]);
          }
        }
        return this;
      }

      function wrapper() {
        return fn.apply(this, Array.prototype.slice.call(arguments, 1));
      }
      wrapper.guid = fn.guid = fn.guid || ($.guid ? $.guid++ : $.event.guid++);
      this.events.bind(topic, wrapper);
      return this;
    },

    // Public: Unbinds a callback for a topic.
    //
    // Accepts the same arguments as jQuery's .unbind().
    //
    // topic - The topic to unbind.
    // fn    - A specific function to unbind from the topic.
    //
    // Examples
    //
    //   view.unbind('my-event');
    //
    // Returns itself for chaining.
    //
    unbind: function () {
      this.events.unbind.apply(this.events, arguments);
      return this;
    },

    // Public: Triggers a topic providing an array of arguments to all listeners.
    //
    // topic - A topic to publish.
    // args  - An Array of arguments to pass into registered listeners.
    //
    // Examples
    //
    //   view.trigger('my-event', [anArg, anotherArg]);
    //
    // Returns itself.
    //
    trigger: function () {
      this.events.triggerHandler.apply(this.events, arguments);
      return this;
    },

    // Public: Shows the element if hidden.
    //
    // Returns itself.
    //
    show: function () {
      this.el.show();
      return this.trigger('show');
    },

    // Public: Hides the element if shown.
    //
    // Returns itself.
    //
    hide: function () {
      this.el.hide();
      return this.trigger('hide');
    }
  });

  // Public: Main view object for the data preview plugin.
  //
  // Contains the main interface elements and acts as a controller binding
  // them together.
  //
  // element - The main DOM Element used for the plugin.
  // columns - The columns array for the data rows formatted for SlickGrid.
  // data    - A data object formatted for use in SlickGrid.
  // chart   - A chart object to load.
  //
  // Examples
  //
  //   new MainView($('.datapraview-wrapper'), columns, data);
  //
  // Returns a new instance of MainView.
  //
  ui.MainView = inherit(ui.View, {
    constructor: function MainView(element, columns, data, chart) {
      this.__super__.constructor.apply(this, arguments);

      bindAll(this, 'redraw', 'onNavChange', 'onNavToggleEditor', 'onEditorSubmit');

      var view = this;
      this.nav = new ui.NavigationView(this.$('.dataexplorer-tableview-nav'));
      this.grid = new ui.GridView(this.$('.dataexplorer-tableview-grid'), columns, data);
      this.chart = new ui.ChartView(this.$('.dataexplorer-tableview-graph'), columns, data);
      this.editor = new ui.EditorView(this.$('.dataexplorer-tableview-editor'), columns, chart);

      this.nav.bind({
        'change': this.onNavChange,
        'toggle-editor': this.onNavToggleEditor
      });
      this.editor.bind({
        'show hide': this.redraw,
        'submit': this.onEditorSubmit
      });

      this.$('.dataexplorer-tableview-editor-info h1').click(function () {
        $(this).parent().toggleClass('dataexplorer-tableview-editor-hide-info');
      });

      this.chart.hide();
    },

    // Public: Redraws the both the grid and chart views.
    //
    // Useful if the viewport changes or is resized.
    //
    // Examples
    //
    //   view.resize();
    //
    // Returns itself.
    //
    redraw: function () {
      this.chart.redraw();
      this.grid.redraw();
      return this;
    },

    // Public: Toggles the display of the grid and chart views.
    //
    // Used as a callback function for the NavigationView "change" event.
    //
    // selected - The name of the newly selected view.
    //
    // Returns nothing.
    //
    onNavChange: function (selected) {
      var isGrid = selected === 'grid';
      this.grid[isGrid ? 'show' : 'hide']();
      this.chart[isGrid ? 'hide' : 'show']();
    },

    // Public: Toggles the display of the editor panel.
    //
    // Used as a callback function for the NavigationView "toggle-editor" event.
    //
    // showEditor - True if the editor should be visible.
    //
    // Returns nothing.
    //
    onNavToggleEditor: function (showEditor) {
      this.el.toggleClass('dataexplorer-tableview-hide-editor', !showEditor);
      this.redraw();
    },

    // Public: Updates the chart view when the editor is submitted.
    //
    // chart - The chart object to render.
    //
    // Returns nothing.
    //
    onEditorSubmit: function (chart) {
      this.nav.toggle('chart');
      this.chart.update(chart);
    }
  });

  // Public: Navigation element for switching between views.
  //
  // Handles the toggling of views within the plugin by firing events when
  // buttons are clicked within the view.
  //
  // element - The Element to use as navigation.
  //
  // Examples
  //
  //   var nav = new NavigationView($('.dataexplorer-tableview-nav'));
  //
  //   // Recieve events when the navigation buttons are clicked.
  //   nav.bind('change', onNavigationChangeHandler);
  //
  // Returns a new instance of NavigationView.
  //
  ui.NavigationView = inherit(ui.View, {
    constructor: function NavigationView(element) {
      this.__super__.constructor.apply(this, arguments);

      bindAll(this, 'onEditorToggleChange', 'onPanelToggleChange');

      this.panelButtons = this.$('.dataexplorer-tableview-nav-toggle').buttonset();
      this.panelButtons.change(this.onPanelToggleChange);

      this.editorButton = this.$('#dataexplorer-tableview-nav-editor').button();
      this.editorButton.change(this.onEditorToggleChange);
    },

    // Public: Toggles a navigation button.
    //
    // Triggers the "change" event with the panel name provided.
    //
    // panel - The name of a button to be selected.
    //
    // Examples
    //
    //   nav.toggle("grid");
    //
    // Returns itself.
    //
    toggle: function (panel) {
      // Need to fire all these events just to get jQuery UI to change state.
      this.$('input[value="' + panel + '"]').click().change().next().click();
      return this;
    },

    // Public: Triggers the "change" event when the navgation changes.
    //
    // Passes the name of the selected item into all callbacks.
    //
    // event - An event object.
    //
    // Returns nothing
    //
    onPanelToggleChange: function (event) {
      this.trigger('change', [event.target.value]);
    },

    // Public: Triggers the "toggle-editor" event when the editor button is
    // clicked. Passes true into callbacks if the button is active.
    //
    // event - An event object.
    //
    // Returns nothing
    //
    onEditorToggleChange: function (event) {
      this.trigger('toggle-editor', [event.target.checked]);
    }
  });

  // Public: Creates and manages a SlickGrid instance for displaying the
  // resource data in a useful grid.
  //
  // SlickGrid documentation: http://github.com/mleibman/SlickGrid/wiki
  //
  // element - The Element to use as a container for the SlickGrid.
  // columns - Column options formatted for use in the SlickGrid container.
  // data    - Data Object formatted for use in the SlickGrid.
  // options - Additional instance and SlickGrid options.
  //
  // Examples
  //
  //   var grid = new GridView($('.dataexplorer-tableview-grid'), columns, data);
  //
  // Returns a new instance of GridView.
  //
  ui.GridView = inherit(ui.View, {
    constructor: function GridView(element, columns, data, options) {
      this.__super__.constructor.apply(this, arguments);

      bindAll(this, '_onSort', 'redraw');

      this.dirty = false;
      this.columns = columns;
      this.data = data;
      this.grid = new Slick.Grid(element, data, columns, $.extend({
        enableColumnReorder: false,
        forceFitColumns: true,
        syncColumnCellResize: true,
        enableCellRangeSelection: false
      }, options));

      this.grid.onSort = this._onSort;

      // In order to extend the resize handles across into the adjacent column
      // we need to disable overflow hidden and increase each cells z-index.
      // We then wrap the contents in order to reapply the overflow hidden.
      this.$('.slick-header-column')
        .wrapInner('<div class="slick-header-wrapper" />')
        .css('overflow', 'visible')
        .css('z-index', function (index) {
          return columns.length - index;
        });

      new Slick.Controls.ColumnPicker(this.columns, this.grid);
    },

    // Public: Reveals the view.
    //
    // If the dirty property is true then it will redraw the grid.
    //
    // Examples
    //
    //   grid.show();
    //
    // Returns itself.
    //
    show: function () {
      this.__super__.show.apply(this, arguments);
      if (this.dirty) {
        this.redraw();
        this.dirty = false;
      }
      return this;
    },

    // Public: Redraws the grid.
    //
    // The grid will only be drawn if the element is visible. If hidden the
    // dirty property will be set to true and the grid redrawn the next time
    // the view is shown.
    //
    // Examples
    //
    //   grid.redraw();
    //
    // Returns itself.
    //
    redraw: function () {
      if (this.el.is(':visible')) {
        this.grid.resizeCanvas();
        this.grid.autosizeColumns();
      } else {
        this.dirty = true;
      }
    },

    // Public: Sort callback for the SlickGrid grid.
    //
    // Called when the grids columns are re-ordered. Accepts the selected
    // column and the direction and should sort the data property.
    //
    // column  - The column object being sorted.
    // sortAsc - True if the solumn should be sorted by ascending items.
    //
    // Returns nothing.
    //
    _onSort: function (column, sortAsc) {
      this.data.sort(function (a, b) {
        var x = a[column.field],
            y = b[column.field];

        if (x == y) {
          return 0;
        }
        return (x > y ? 1 : -1) * (sortAsc ? 1 : -1);
      });
      this.grid.invalidate();
    }
  });

  // Public: Creates a wrapper around a jQuery.Flot() chart.
  //
  // Currently a very basic implementation that accepts data prepared for the
  // SlickGrid, ie columns and data objects and uses them to generate a canvas
  // chart.
  //
  // Flot documentation: http://people.iola.dk/olau/flot/API.txt
  //
  // element - Element to use as a container for the Flot canvas.
  // columns - Array of column data.
  // data    - Data Object.
  // chart   - Optional chart data to load.
  //
  // Examples
  //
  //   new ChartView($('.dataexplorer-tableview-chart'), columns, data, {
  //     id: 'my-chart-id',  // Any unique id for the chart used for storage.
  //     type: 'line',       // ID of one of the ChartView.TYPES.
  //     groups: 'column-2', // The column to use as the x-axis.
  //     series: ['column-3', 'column-4'] // Columns to use as the series.
  //   });
  //
  // Returns a new instance of ChartView.
  //
  ui.ChartView = inherit(ui.View, {
    constructor: function ChartView(element, columns, data, chart) {
      this.__super__.constructor.apply(this, arguments);
      this.data = data;
      this.columns = columns;
      this.chart = chart;
      this.createPlot((chart && chart.type) || 'line');
      this.draw();
    },

    // Public: Creates a new Flot chart and assigns it to the plot property.
    //
    // typeId - The id String of the grid to create used to load chart
    //          specific options on creation.
    //
    // Examples
    //
    //   chart.createPlot('line');
    //
    // Returns itself.
    //
    createPlot: function (typeId) {
      var type = ui.ChartView.findTypeById(typeId),
          options = type && type.getOptions ? type.getOptions(this) : {};

      this.plot = $.plot(this.el, this.createSeries(), options);
      return this;
    },

    // Public: Creates the series/data Array required by jQuery.plot()
    //
    // Examples
    //
    //   $.plot(editor.el, editor.createSeries(), options);
    //
    // Returns an Array containing points for each series in the chart.
    //
    createSeries: function () {
      var series = [], view = this;
      if (this.chart) {
        $.each(this.chart.series, function (seriesIndex, field) {
          var points = [];
          $.each(view.data, function (index) {
            var x = this[view.chart.groups], y = this[field];
            if (typeof x === 'string') {
              x = index;
            }
            points.push([x, y]);
          });
          series.push({data: points, label: view._getColumnName(field)});
        });
      }
      return series;
    },

    // Public: Redraws the chart with regenerated series data.
    //
    // Usually .update() will be called instead.
    //
    // Returns itself.
    //
    draw: function () {
      this.plot.setData(this.createSeries());
      return this.redraw();
    },

    // Public: Updates the current plot with a new chart Object.
    //
    // chart - A chart Object usually provided by the EditorView.
    //
    // Examples
    //
    //   editor.bind('submit', function (chart) {
    //     chart.update(chart);
    //   });
    //
    // Returns itself.
    //
    update: function (chart) {
      if (!this.chart || chart.type !== this.chart.type) {
        this.createPlot(chart.type);
      }
      this.chart = chart;
      this.draw();
      return this;
    },

    // Public: Redraws the current chart in the canvas.
    //
    // Used if the chart data has changed or the viewport has been resized.
    //
    // Examples
    //
    //   $(window).resize(function () {
    //     chart.redraw();
    //   });
    //
    // Returns itself.
    //
    redraw: function () {
      this.plot.resize();
      this.plot.setupGrid();
      this.plot.draw();
      return this;
    },

    // Public: Gets the human readable column name for the field id.
    //
    // field - A field id String used in the data object.
    //
    // Examples
    //
    //   chart._getColumnName('column-1');
    //
    // Returns the String column name.
    //
    _getColumnName: function (field) {
      for (var i = 0, count = this.columns.length; i < count; i += 1) {
        if (this.columns[i].field === field) {
          return this.columns[i].name;
        }
      }
      return name;
    }
  }, {
    // Array of chart formatters. They require an id and name attribute and
    // and optional getOptions() method. Used to generate different chart types.
    //
    // id         - A unique id String for the chart type.
    // name       - A human readable name for the type.
    // getOptions - Function that accepts an instance of ChartView and returns
    //              an options object suitable for use in $.plot();
    //
    TYPES: [{
      id: 'line',
      name: 'Line Chart'
    }, {
      id: 'bar',
      name: 'Bar Chart (draft)',
      getOptions: function (view) {
        return {
          series: {
            lines: {show: false},
            bars: {
              show: true,
              barWidth: 1,
              align: "left",
              fill: true
            }
          },
          xaxis: {
            tickSize: 1,
            tickLength: 1,
            tickFormatter: function (val) {
              if (view.data[val]) {
                return view.data[val][view.chart.groups];
              }
              return '';
            }
          }
        };
      }
    }],

    // Public: Helper method for findind a chart type by id key.
    //
    // id - The id key to search for in the ChartView.TYPES Array.
    //
    // Examples
    //
    //   var type = ChartView.findTypeById('line');
    //
    // Returns the type object or null if not found.
    //
    findTypeById: function (id) {
      var filtered = $.grep(this.TYPES, function (type) {
        return type.id === id;
      });
      return filtered.length ? filtered[0] : null;
    }
  });

  // Public: Creates a form for editing chart metadata.
  //
  // Publishes "submit" and "save" events providing a chart Obejct to all
  // registered callbacks.
  //
  // element - The Element to use as the form wrapper.
  // columns - Array of columns that are used by the data set.
  // chart   - Optional chart Object to display on load.
  //
  // Examples
  //
  //   new EditorView($('.dataexplorer-tableview-editor'), columns, {
  //     id: 'my-chart-id',
  //     type: 'line',
  //     groups: 'column-2',
  //     series: ['column-3', 'column-4']
  //   });
  //
  // Returns a new instance of EditorView.
  //
  ui.EditorView = inherit(ui.View, {
    constructor: function EditorView(element, columns, chart) {
      this.__super__.constructor.apply(this, arguments);

      bindAll(this, 'onAdd', 'onRemove', 'onSubmit', 'onSave');

      this.columns = columns;
      this.type    = this.$('.dataexplorer-tableview-editor-type select');
      this.groups  = this.$('.dataexplorer-tableview-editor-group select');
      this.series  = this.$('.dataexplorer-tableview-editor-series select');
      this.id      = this.$('.dataexplorer-tableview-editor-id');

      this.$('button').button();
      this.save = this.$('.dataexplorer-tableview-editor-save').click(this.onSave);
      this.el.bind('submit', this.onSubmit);
      this.el.delegate('a[href="#remove"]', 'click', this.onRemove);
      this.el.delegate('select', 'change', this.onSubmit);

      this.$('.dataexplorer-tableview-editor-add').click(this.onAdd);

      this.setupTypeOptions().setupColumnOptions();

      this.seriesClone = this.series.parent().clone();

      if (chart) {
        this.load(chart);
      }
    },

    // Public: Fills the "type" select box with options.
    //
    // Returns itself.
    //
    setupTypeOptions: function () {
      var types = {};
      // TODO: This shouldn't be referenced directly but passed in as an option.
      $.each(ui.ChartView.TYPES, function () {
        types[this.id] = this.name;
      });

      this.type.html(this._createOptions(types));
      return this;
    },

    // Public: Fills the groups and series select elements with options.
    //
    // Returns nothing.
    //
    setupColumnOptions: function () {
      var options = {}, optionsString = '';
      $.each(this.columns, function (index, column) {
        options[column.field] = column.name;
      });
      optionsString = this._createOptions(options);

      this.groups.html(optionsString);
      this.series.html(optionsString);
      return this;
    },

    // Public: Adds a new empty series select box to the editor.
    //
    // All but the first select box will have a remove button that allows them
    // to be removed.
    //
    // Examples
    //
    //   editor.addSeries();
    //
    // Returns itself.
    //
    addSeries: function () {
      var element = this.seriesClone.clone(),
          label   = element.find('label'),
          index   = this.series.length;

      this.$('ul').append(element);
      this.updateSeries();

      label.append('<a href="#remove">Remove</a>');
      label.find('span').text(String.fromCharCode(this.series.length + 64));

      return this;
    },

    // Public: Removes a series list item from the editor.
    //
    // Also updates the labels of the remianing series elements.
    //
    // element - A jQuery wrapped list item Element to remove.
    //
    // Examples
    //
    //   // Remove the third series element.
    //   editor.removeSeries(editor.series.eq(2).parent());
    //
    // Returns itself.
    //
    removeSeries: function (element) {
      element.remove();
      this.updateSeries();
      this.series.each(function (index) {
        if (index > 0) {
          var labelSpan = $(this).prev().find('span');
          labelSpan.text(String.fromCharCode(index + 65));
        }
      });
      return this.submit();
    },

    // Public: Resets the series property to reference the select elements.
    //
    // Returns itself.
    //
    updateSeries: function () {
      this.series = this.$('.dataexplorer-tableview-editor-series select');
      return this;
    },

    // Public: Loads a chart into the editor.
    //
    // For an example of the chart object structure see the ChartView docs.
    //
    // chart - A chart Object to be loaded.
    //
    // Examples
    //
    //   editor.load(chart);
    //
    // Returns itself.
    //
    load: function (chart) {
      var editor = this;
      this._selectOption(this.type, chart.type);
      this._selectOption(this.groups, chart.groups);

      this.id.val(chart.id);
      this.type.val(chart.type);
      $.each(chart.series, function update(index, option) {
        var element = editor.series.eq(index);
        if (!element.length) {
          editor.addSeries();
          return update(index, option);
        }
        editor._selectOption(element, option);
      });

      return this;
    },

    // Public: Submits the current form.
    //
    // Triggers the "submit" event providing a chart object to all listeners.
    //
    // Examples
    //
    //   editor.bind("submit", chart.update);
    //   editor.submit();
    //
    // Returns itself.
    //
    submit: function () {
      return this._triggerChartData('submit');
    },

    // Public: Toggles the loading state on the view.
    //
    // Freezes all interface elements and displays a loading message.
    //
    // show - If false disables the loading state.
    //
    // Examples
    //
    //   // Set the state to loading.
    //   editor.loading();
    //
    //   // Disable the loading state.
    //   editor.loading(false);
    //
    // Returns itself.
    //
    loading: function (show) {
      var action = show === false ? 'enable' : 'disable';

      this.$('select').attr('disabled', show !== false);
      this.save.button(action);

      this._updateSaveText(show === false ? null : 'Loading...');

      return this;
    },

    // Public: Toggles the saving state on the view.
    //
    // show - If false disables the saving state.
    //
    // Examples
    //
    //   // Set the state to saving.
    //   editor.saving();
    //
    //   // Disable the saving state.
    //   editor.saving(false);
    //
    // Returns itself.
    //
    saving: function (show) {
      this.disableSave(show);
      this._updateSaveText(show === false ? null : 'Saving...');
      return this;
    },

    // Public: Toggles the save button state between enabled/disabled.
    //
    // disable - If false enables the button.
    //
    // Returns itself.
    //
    disableSave: function (disable) {
      this.save.button(disable === false ? 'enable' : 'disable');
      return this;
    },

    // Public: Event callback for the "Add series" button.
    //
    // event - A jQuery Event object.
    //
    // Examples
    //
    //   $('button').click(event.onAdd);
    //
    // Returns nothing.
    //
    onAdd: function (event) {
      event.preventDefault();
      this.addSeries();
    },

    // Public: Event callback for the "Remove series" button.
    //
    // event - A jQuery Event object.
    //
    // Examples
    //
    //   $('button').click(event.onRemove);
    //
    // Returns nothing.
    //
    onRemove: function (event) {
      event.preventDefault();
      var element = $(event.target).parents('.dataexplorer-tableview-editor-series');
      this.removeSeries(element);
    },

    // Public: Event callback for the "Save" button.
    //
    // Triggers the "save" event passing a chart object to all registered
    // callbacks.
    //
    // event - A jQuery Event object.
    //
    // Examples
    //
    //   $('button.save').click(editor.onSave);
    //
    // Returns nothing.
    //
    onSave: function (event) {
      event.preventDefault();
      this._triggerChartData('save');
    },

    // Public: Event callback for the editor form.
    //
    // event - A jQuery Event object.
    //
    // Examples
    //
    //   $('form.editor').submit(editor.onSubmit);
    //
    // Returns nothing.
    //
    onSubmit: function (event) {
      event && event.preventDefault();
      this.submit();
    },

    // Updates the text on the save button.
    //
    // If no text is provided reverts to the original button text.
    //
    // text - A text String to use in the button.
    //
    // Examples
    //
    //   editor._updateSaveText('Now saving!');
    //
    // Returns nothing.
    //
    _updateSaveText: function (text) {
      var span = this.save.find('span'),
          original = span.data('default');

      if (!original) {
        span.data('default', span.text());
      }

      span.text(text || original);
    },

    // Triggers an event on the editor and passes a chart object to callbacks.
    //
    // topic - Topic String for the event to fire.
    //
    // Examples
    //
    //   editor.bind('save', function (chart) {
    //     // DO something with the chart.
    //   });
    //   editor._triggerChartData('save');
    //
    // Returns
    //
    _triggerChartData: function (topic) {
      var series = this.series.map(function () {
        return $(this).val();
      });

      return this.trigger(topic, [{
        id: this.id.val(),
        type: this.type.val(),
        groups: this.groups.val(),
        series: $.makeArray(series)
      }]);
    },

    // Finds an option by "value" in a select element and makes it selected.
    //
    // select - A jQuery wrapped select Element.
    // option - The String value of the options "value" attribute.
    //
    // Examples
    //
    //   // For <select><option value="bill">Bill</option></select>
    //   editor._selectOption(mySelect, 'bill');
    //
    // Returns nothing.
    //
    _selectOption: function (select, option) {
      select.find('[value="' + option + '"]').attr('selected', 'selected');
    },

    // Creates a String of option elements.
    //
    // options - An object of value/text pairs.
    //
    // Examples
    //
    //   var html = editor._createOptions({
    //     value1: 'Value 1',
    //     value2: 'Value 2'
    //   });
    //
    // Returns a String of HTML.
    //
    _createOptions: function (options) {
      var html = [];
      $.each(options, function (value, text) {
        html.push('<option value="' + value + '">' + text + '</option>');
      });
      return html.join('');
    }
  });

  // Exports the UI and createTableView() methods onto the plugin object.
  $.extend(true, this, {DATAEXPLORER: {TABLEVIEW: {

    UI: ui,

    // Public: Helper method for creating a new view.
    //
    // element - The main DOM Element used for the plugin.
    // columns - The columns array for the data rows formatted for SlickGrid.
    // data    - A data object formatted for use in SlickGrid.
    // chart   - An optional chart object to load.
    //
    // Examples
    //
    //   TABLEVIEW.createTableView($('my-view'), columns, data);
    //
    // Returns a new instance of MainView.
    //
    createTableView: function (element, columns, data, chart) {
      return new ui.MainView(element, columns, data, chart);
    }
  }}});

})(jQuery);
