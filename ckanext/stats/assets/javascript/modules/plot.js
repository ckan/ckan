/* A quick module for generating flot charts from an HTML table. Options can
 * be passed directly to flot using the data-module-* attributes. The tables
 * are currently expected to be marked up as follows:
 *
 *   <table data-module="plot">
 *     <thead>
 *       <tr>
 *         <th>X Axis</th>
 *         <th>Series A Legend</th>
 *         <th>Series B Legend</th>
 *       </tr>
 *     </thead>
 *     <tbody>
 *       <tr>
 *         <th>X Value</th>
 *         <td>Series A Y Value</td>
 *         <td>Series B Y Value</td>
 *       </tr>
 *       ...
 *     </tbody>
 *   </table>
 *
 * Points are pulled out of the th/td elements using innerHTML or by looking
 * for a data-value attribute. This is useful when a more readable value
 * needs to be used in the elements contents (eg. dates). A data-type attribute
 * can also be applied to parse the value. Only data-type="date" is currently
 * supported and expects data-value to be a unix timestamp.
 */
this.ckan.module('plot', function (jQuery) {
  return {
    /* Holds the jQuery.plot() object when created */
    graph: null,

    /* Holds the canvas container when created */
    canvas: null,

    /* Default options */
    options: {
      xaxis: {},
      yaxis: {},
      legend: {position: 'nw'},
      colors: ['#ffcc33', '#ff8844']
    },

    /* Sets up the canvas element and parses the table.
     *
     * Returns nothing.
     */
    initialize: function () {
      jQuery.proxyAll(this, /_on/);

      if (!this.el.is('table')) {
        throw new Error('CKAN module plot can only be called on table elements');
      }

      this.setupCanvas();

      // Because the canvas doesn't render correctly unless visible we must
      // listen for events that reveal the canvas and then try and re-render.
      // Currently the most common of these is the "shown" event triggered by
      // the tabs plugin.
      this.sandbox.body.on("shown", this._onShown);
      this.data = this.parseTable(this.el);

      this.draw();
    },

    /* Removes event handlers when the module is removed from the DOM.
     *
     * Returns nothing.
     */
    teardown: function () {
      this.sandbox.body.off("shown", this._onShown);
    },

    /* Creates the canvas wrapper and removes the table from the document.
     *
     * Returns nothing.
     */
    setupCanvas: function () {
      this.canvas = jQuery('<div class="module-plot-canvas">');
      this.el.replaceWith(this.canvas);
    },

    /* Attempts to draw the chart if the canvas is visible. If not visible the
     * graph does not render correctly. So we keep trying until it is.
     *
     * Examples
     *
     *   module.draw();
     *
     * Returns nothing.
     */
    draw: function () {
      if (!this.drawn && this.canvas.is(':visible')) {
        this.graph = jQuery.plot(this.canvas, this.data, this.options);
      }
    },

    /* Parses an HTML table element to build the data array for the chart.
     * The thead element provides the axis and labels for the series. The
     * first column in the tbody is used for the x-axis and subsequent
     * columns are the series.
     *
     * table - A table element to parse.
     *
     * Examples
     *
     *   module.parseTable(module.el);
     *
     * Returns data object suitable for use in jQuery.plot().
     */
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

    /* Retrieves the value from a td/th element. This first looks for a
     * data-value attribute on the element otherwise uses the element
     * text contents.
     *
     * A data-type attribute can also be provided to tell the module how
     * to deal with the element. By default we let jQuery.data() handle
     * the parsing but this can provide additional data. See .parseValue()
     * for more info.
     *
     * cell - An element to extract a value from.
     *
     * Examples
     *
     *   var element = jQuery('<td data-value="10">Ten</td>');
     *   module.getValue(element); //=> 10
     *
     *   var element = jQuery('<td>20</td>');
     *   module.getValue(element); //=> 20
     *
     *   var element = jQuery('<td data-type="date">1343747094</td>');
     *   module.getValue(element); //=> <Date Tue Jul 31 2012 16:04:54 GMT+0100 (BST)>
     *
     * Returns the parsed value.
     */
    getValue: function (cell) {
      var item  = cell instanceof jQuery ? cell : jQuery(cell);
      var type  = item.data('type')  || 'string';
      var value = item.data('value') || item.text();
      return this.parseValue(value, type);
    },

    /* Provides the ability to further format a value.
     *
     * If date is provided as a type then it expects value to be a unix
     * timestamp in seconds.
     *
     * value - The value extracted from the element.
     * type  - A type string, currently only supports "date".
     *
     * Examples
     *
     *   module.parseValue(10); // => 10
     *   module.parseValue("cat"); // => "cat"
     *   module.parseValue(1343747094, 'date'); // => <Date Tue Jul 31 2012 16:04:54 GMT+0100 (BST)>
     *
     * Returns the parsed value.
     */
    parseValue: function (value, type) {
      if (type === 'date') {
        value = new Date(parseInt(value, 10) * 1000);
        if (!value) {
          value = 0;
        }
      }
      return value;
    },

    /* Event handler for when tabs are toggled. Determines if the canvas
     * resides in the shown element and attempts to re-render.
     *
     * event - The shown event object.
     *
     * Returns nothing.
     */
    _onShown: function (event) {
      if (!this.drawn && jQuery.contains(jQuery(event.target.hash)[0], this.canvas[0])) {
        this.draw();
      }
    }
  };
});
