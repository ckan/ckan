/* Updates the Followers counter in the UI when the Follow/Unfollow button
* is clicked.
*
* id - id of the object the user is trying to follow/unfollow.
*
* Example
*
*   <dd data-module="followers-counter" data-module-id="object-id">6</dd>
*
*/
this.ckan.module('followers-counter', function($) {
  'use strict';

  return {
    options: {id: null},

    /* Subscribe to events when the Follow/Unfollow button is clicked.
    *
    * Returns nothing.
    */
    initialize: function() {
      $.proxyAll(this, /_on/);

      this.counterEl = this.$('span');
      this.counterVal = this.counterEl.text();
      this.counterVal = parseInt(this.counterVal, 10);
      this.objId = this.options.id;

      this.sandbox.subscribe('follow-follow-' + this.objId, this._onFollow);
      this.sandbox.subscribe('follow-unfollow-' + this.objId, this._onUnfollow);
    },

    /* Handles updating the UI for Followers counter on Follow button click.
    *
    * Returns nothing.
    */
    _onFollow: function() {
      this.counterEl.text(++this.counterVal);
    },

    /* Handles updating the UI for Followers counter on Unfollow button click.
    *
    * Returns nothing.
    */
    _onUnfollow: function() {
      this.counterEl.text(--this.counterVal);
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
