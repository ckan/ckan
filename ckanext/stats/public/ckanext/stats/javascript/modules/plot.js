this.ckan.module('plot', function (jQuery, _) {
  return {
    graph: null,
    canvas: null,
    options: {
      xaxis: {},
      yaxis: {},
      legend: {position: 'nw'},
      colors: ['#ffcc33', '#ff8844']
    },

    initialize: function () {
      jQuery.proxyAll(this, /_on/);

      if (!this.el.is('table')) {
        throw new Error('CKAN module plot can only be called on table elements');
      }

      this.setupCanvas();
      this.sandbox.body.on("shown", this._onShown);
      this.data = this.parseTable(this.el);

      this.draw();

      window.g = window.g || [];
      window.g.push(this.graph);
    },

    teardown: function () {
      this.sandbox.body.off("shown", this._onShown);
    },

    setupCanvas: function () {
      this.canvas = jQuery('<div class="module-plot-canvas">');
      this.el.replaceWith(this.canvas);
    },

    draw: function () {
      if (!this.drawn && this.canvas.is(':visible')) {
        this.graph = jQuery.plot(this.canvas, this.data, this.options);
      }
    },

    parseTable: function (table) {
      var data = [];
      var _this = this;

      var headings = table.find('thead tr:first th').map(function () {
        return this.innerHTML;
      });

      table.find('tbody tr').each(function (row) {
        var element = jQuery(this);
        var x = [];

        x[row] = _this.getValue(element.find('th'));

        element.find('td').each(function (series) {
          var value   = _this.getValue(this);
          var label = headings[series + 1];

          data[series] = data[series] || {data: [], label: label};
          data[series].data[row] = [x[row], value];
        });
      });

      return data;
    },

    getValue: function (cell) {
      var item  = cell instanceof jQuery ? cell : jQuery(cell);
      var type  = item.data('type')  || 'string';
      var value = item.data('value') || item.text();
      return this.parseValue(value, type);
    },

    parseValue: function (value, type) {
      if (type === 'date') {
        value = new Date(parseInt(value, 10) * 1000);
      }
      return value;
    },

    _onShown: function (event) {
      if (!this.drawn && jQuery.contains(jQuery(event.target.hash)[0], this.canvas[0])) {
        this.draw();
      }
    }
  };
});
