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

      // Read translatable strings from data attributes so templates can inject
      // translated values. Fallback to English if attributes are not present.
      var btn = document.getElementById("metadata_button");
      var showText = btn.getAttribute('data-show-text') || 'Show metadata diff';
      var hideText = btn.getAttribute('data-hide-text') || 'Hide metadata diff';

      if (btn.value === showText) {
        btn.value = hideText;
      }
      else {
        btn.value = showText;
      }
    }
  }
});
