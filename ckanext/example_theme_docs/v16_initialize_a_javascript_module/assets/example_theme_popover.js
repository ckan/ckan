// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

ckan.module('example_theme_popover', function ($) {
  return {
    initialize: function () {
      console.log("I've been initialized for element: ", this.el);
    }
  };
});

