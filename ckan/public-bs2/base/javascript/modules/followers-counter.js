/* Updates the Followers counter in the UI when the Follow/Unfollow button
* is clicked.
*
* id - id of the object the user is trying to follow/unfollow.
* num_followers - Number of followers the object has.
*
* Example
*
*   <dd data-module="followers-counter"
*       data-module-id="object-id"
*       data-module-num_followers="6">
*     <span>6</span>
*   </dd>
*
*/
this.ckan.module('followers-counter', function($) {
  'use strict';

  return {
    options: {
      id: null,
      num_followers: 0
    },

    /* Subscribe to events when the Follow/Unfollow button is clicked.
    *
    * Returns nothing.
    */
    initialize: function() {
      $.proxyAll(this, /_on/);

      this.counterEl = this.$('span');
      this.objId = this.options.id;

      this.sandbox.subscribe('follow-follow-' + this.objId, this._onFollow);
      this.sandbox.subscribe('follow-unfollow-' + this.objId, this._onUnfollow);
    },

    /* Calls a function to update the counter when the Follow button is clicked.
    *
    * Returns nothing.
    */
    _onFollow: function() {
      this._updateCounter({action: 'follow'});
    },

    /* Calls a function to update the counter when the Unfollow button is clicked.
    *
    * Returns nothing.
    */
    _onUnfollow: function() {
      this._updateCounter({action: 'unfollow'});
    },

    /* Handles updating the UI for Followers counter.
    *
    * Returns nothing.
    */
    _updateCounter: function(options) {
      var locale = $('html').attr('lang');
      var action = options.action;
      var incrementedFollowers;

      if (action === 'follow') {
        incrementedFollowers = (++this.options.num_followers).toLocaleString(locale);
      } else if (action === 'unfollow') {
        incrementedFollowers = (--this.options.num_followers).toLocaleString(locale);
      }

      // Only update the value if it's less than 1000, because for larger
      // numbers the change won't be noticeable since the value is converted
      // to SI number abbreviated with "k", "m" and so on.
      if (this.options.num_followers < 1000) {
        this.counterEl.text(incrementedFollowers);
        this.counterEl.removeAttr('title');
      } else {
        this.counterEl.attr('title', incrementedFollowers);
      }
    },

    /* Remove any subscriptions to prevent memory leaks. This function is
     * called when a module element is removed from the page.
     *
     * Returns nothing.
     */
    teardown: function() {
      this.sandbox.unsubscribe('follow-follow-' + this.objId, this._onFollow);
      this.sandbox.unsubscribe('follow-unfollow-' + this.objId, this._onUnfollow);
    }
  }
});
