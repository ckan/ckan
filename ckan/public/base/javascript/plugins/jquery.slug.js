/* Restricts the input into the field to just slug safe characters.
 *
 * The element will also fire the "slugify" event passing in the new and
 * previous strings as arguments.
 *
 * Examples
 *
 *   var slug = jQuery([name=slug]).slug();
 *
 *   slug.on('slugify', function (event, current, previous) {
 *     console.log("value was: %s, and is now %s", current, previous);
 *   });
 *
 * Returns the jQuery collection.
 */
(function ($) {

  /* Handles the on change event that "slugifies" the entire string. This
   * catches text pasted into the input.
   *
   * event - the DOM event object.
   *
   * Returns nothing.
   */
  function onChange(event) {
    var value = this.value;
    var updated = $.url.slugify(value, true);

    if (value !== updated) {
      this.value = updated;
      $(this).trigger('slugify', [this.value, value]);
    }
  }

  /* Handles the keypress event that will convert each character as the user
   * inputs new text. This will not catch text pasted into the input.
   *
   * event - the DOM event object.
   *
   * Returns nothing.
   */
  function onKeypress(event) {
    if (!event.charCode) {
      return;
    }

    event.preventDefault();

    var value = this.value;
    var start = this.selectionStart;
    var end   = this.selectionEnd;
    var char  = String.fromCharCode(event.charCode);
    var updated;
    var range;

    if (this.setSelectionRange) {
      updated = value.substring(0, start) + char + value.substring(end, value.length);

      this.value = $.url.slugify(updated, false);
      this.setSelectionRange(start + 1, start + 1);
    } else if (document.selection && document.selection.createRange) {
      range = document.selection.createRange();
      range.text = char + range.text;
    }

    $(this).trigger('slugify', [this.value, value]);
  }

  /* The jQuery plugin for converting an input.
   */
  $.fn.slug = function () {
    return this.each(function () {
      $(this).on({
        'blur.slug': onChange,
        'change.slug': onChange,
        'keypress.slug': onKeypress
      });
    });
  };

  // Export the methods onto the plugin for testability.
  $.extend($.fn.slug, {onChange: onChange, onKeypress: onKeypress});
})(this.jQuery);
