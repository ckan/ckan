/* Quick module to enhance the Bootstrap tags plug-in to update the url
 * hash when a tab changes to allow the user to bookmark the page.
 *
 * Each tab id must use a prefix which which will be stripped from the hash.
 * This is to prevent the page jumping when the hash fragment changes.
 *
 * prefix - The prefix used on the ids.
 *
 */

ckan.module("stats-nav", function($) {
  return {
    /* An options object */
    options: {
      prefix: "stats-"
    },

    /* Initializes the module and sets up event listeners.
     *
     * Returns nothing.
     */
    initialize: function() {
      var location = this.sandbox.location;
      var prefix = this.options.prefix;
      var hash = location.hash.slice(1);
      var selected = this.el.find('[href^="#' + prefix + hash + '"]');

      // Update the hash fragment when the tab changes.
      this.el.on("shown.bs.tab", function(event) {
        location.hash = event.target.hash.slice(prefix.length + 1);
      });

      // Show the current tab if the location provides one.
      if (selected.length) {
        selected.tab("show");
      }
    }
  };
});
