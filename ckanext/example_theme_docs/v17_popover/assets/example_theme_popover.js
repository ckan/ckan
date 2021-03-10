"use strict";

/* example_theme_popover
 *
 * This JavaScript module adds a Bootstrap popover with some extra info about a
 * dataset to the HTML element that the module is applied to. Users can click
 * on the HTML element to show the popover.
 *
 * title - the title of the dataset
 * license - the title of the dataset's copyright license
 * num_resources - the number of resources that the dataset has.
 *
 */
ckan.module('example_theme_popover', function ($) {
  return {
    initialize: function () {

      // Access some options passed to this JavaScript module by the calling
      // template.
      var num_resources = this.options.num_resources;
      var license = this.options.license;

      // Format a simple string with the number of resources and the license,
      // e.g. "3 resources, Open Data Commons Attribution License".
      var content = 'NUM resources, LICENSE'
        .replace('NUM', this.options.num_resources)
        .replace('LICENSE', this.options.license)

      // Add a Bootstrap popover to the HTML element (this.el) that this
      // JavaScript module was initialized on.
      this.el.popover({title: this.options.title,
                       content: content,
                       placement: 'left'});
    }
  };
});

