/*
 * Copies value into buffer(aka `Ctrl-C`)
 *
 * value - (optional) Value that will be copied
 *
 * Examples
 *
 * <button type="button" data-module="copy-into-buffer" data-module-copy-value="Hello, world!">Copy</button>
 *
 */
this.ckan.module("copy-into-buffer", function ($) {
  "use strict";
  return {
    options: {
      copyValue: null,
    },

    /* Sets up the module.
     *
     * Returns nothing.
     */
    initialize: function () {
      this._onClick = this._onClick.bind(this);
      this.el.on("click", this._onClick);
    },
    teardown: function () {
      this.el.off("click", this._onClick);
    },

    /* Event handler for clicking on the element */
    _onClick: function (event) {
      event.preventDefault();
      this.copy(this.options.copyValue);
    },

    /* Put copy of value into buffer.
     *
     * value - text that will be copied.
     *
     * Returns nothing.
     */
    copy: function (value) {
      var container = $("<textarea>");
      container.val(value);
      container.css({
        opacity: 0,
        position: "fixed",
        top: 0,
        bottom: 0,
      });
      container.appendTo(document.body);
      container.focus();
      container.select();
      document.execCommand("copy");
      container.remove();
    },
  };
});
