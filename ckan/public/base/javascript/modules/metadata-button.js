/* Watches the "Show metadata diff" button on the Changes summary page.
 * When the button is pressed, toggles the display of the metadata diff
 * for the chronologically most recent revision on and off.
 *
 * target - a button to watch for changes (default: button)
 *
 */

ckan.module('metadata-button', function(jQuery) {
  return {
    options: {
      target: 'button'
    },

    initialize: function () {
      // Watch for our button to be clicked.
      this.el.on('click', jQuery.proxy(this._onClick, this));
    },

    _onClick: function(event) {
      console.log("PRESSED THE BUTTON");
      var div = document.getElementById("metadata_diff");
      if (div.style.display === "none") {
        div.style.display = "block";
      }
      else {
        div.style.display = "none";
      }
      var btn = document.getElementById("metadata_button");
      if (btn.value === "Show metadata diff") {
        btn.value = "Hide metadata diff";
      }
      else {
        btn.value = "Show metadata diff";
      }
    }
  }
});
