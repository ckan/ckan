/* User context hover/popovers
 * These appear when someone hovers over a avatar in a activity stream to
 * give the user more context into that particular user. It also allows for people to
 * follow and unfollow quickly from within the popover
 *
 * id - The user_id of user
 * url - The URL of the profile for that user
 * loading - Loading sat helper
 * authed - Is the current user authed ... if so what's their user_id
 * template - Simple string-replace template for content of popover
 *
 * Examples
 *
 *   <a data-module="user-context" data-module-id="{user_id}">A user</a>
 *
 */

// Global dictionary store for users
window.user_context_dict = {};

this.ckan.module('user-context', function($, _) {
	return {

		/* options object can be extended using data-module-* attributes */
		options : {
			id: null,
			loading: false,
			authed: false,
			url: '',
			template: '<div class="profile-info">{{ about }}<div class="btn-group">{{ buttons }}</div><div class="nums"><dl><dt>{{ lang.followers }}</dt><dd>{{ followers }}</dd></dl><dl><dt>{{ lang.datasets }}</dt><dd>{{ datasets }}</dd></dl><dl><dt>{{ lang.edits }}</dt><dd>{{ edits }}</dd></dl></div></div>',
			i18n: {
				follow: _('Follow'),
				unfollow: _('Unfollow'),
				loading: _('Loading...'),
				followers: _('Followers'),
				datasets: _('Datasets'),
				edits: _('Edits'),
				view_profile: _('View profile')
			}
		},

		/* Initialises the module setting up elements and event listeners.
		 *
		 * Returns nothing.
		 */
		initialize: function () {
			if (
				this.options.id != true
				&& this.options.id != null
			) {
				$.proxyAll(this, /_on/);
				if ($('.account').hasClass('authed')) {
					this.options.authed = $('.account').data('me');
				}
				this.el.popover({
					animation: false,
					content: this.i18n('loading'),
					placement: 'bottom'
				});
				this.el.on('mouseover', this._onMouseOver);
				this.sandbox.subscribe('follow-follow-' + this.options.id, this._onHandleFollow);
				this.sandbox.subscribe('follow-unfollow-' + this.options.id, this._onHandleUnFollow);
			}
		},

		/* Handles the showing of the popover on hover (also hides other active popovers)
		 *
		 * Returns nothing.
		 */
		_onMouseOver: function() {
			$('[data-module="user-context"]').popover('hide');
			this.el.popover('show');
			this.getUserData();
		},

		/* Get's the user data from the ckan api
		 *
		 * Returns nothing.
		 */
		getUserData: function() {
			if (!this.options.loading) {
				var id = this.options.id;
				if (typeof window.user_context_dict[id] == 'undefined') {
					var client = this.sandbox.client;
					this.loading = true;
					client.call('GET', 'user_show', '?id=' + id, this._onHandleUserData);
				} else {
					this._onHandleUserData(window.user_context_dict[id]);
				}
			}
		},

		/* Callback from getting the user_show from the ckan api
		 *
		 * Returns nothing.
		 */
		_onHandleUserData: function(json) {
			this.loading = false;
			if (json.success) {
				var id = this.options.id;
				var client = this.sandbox.client;
				var user = json.result;
				if (typeof user.number_of_followers == 'undefined') {
					user.number_of_followers = '...';
					client.call('GET', 'user_follower_count', '?id=' + id, this._onHandleUserFollowersData);
				}
				if (typeof user.am_following_user == 'undefined') {
					user.am_following_user = 'disabled';
					client.call('GET', 'am_following_user', '?id=' + id, this._onHandleAmFollowingData);
				}
				window.user_context_dict[this.options.id] = json;
				this._onRenderPopover();
			}
		},

		/* Renders the contents of the popover
		 *
		 * Returns nothing.
		 */
		_onRenderPopover: function() {
			var user = window.user_context_dict[this.options.id].result;
			var popover = this.el.data('popover');
			if (typeof popover.$tip != 'undefined') {
				var tip	= popover.$tip;
				var about = user.about ? '<p class="about">' + user.about + '</p>' : '';
				var template = this.options.template
					.replace('{{ about }}', about)
					.replace('{{ followers }}', user.number_of_followers)
					.replace('{{ datasets }}', user.number_administered_packages)
					.replace('{{ edits }}', user.number_of_edits)
					.replace('{{ buttons }}', this._getButtons(user))
					.replace('{{ lang.followers }}', this.i18n('followers'))
					.replace('{{ lang.datasets }}', this.i18n('datasets'))
					.replace('{{ lang.edits }}', this.i18n('edits'));
				$('.popover-title', tip).html('<a href="javascript:;" class="popover-close">&times;</a>' + user.display_name);
				$('.popover-content', tip).html(template);
				$('.popover-close', tip).on('click', this._onClickPopoverClose);
				var follow_check = $('[data-module="follow"]', tip);
				if (follow_check.length > 0) {
					ckan.module.initializeElement(follow_check[0]);
				}
			}
		},

		/* Handles closing the currently open popover
		 *
		 * Returns nothing.
		 */
		_onClickPopoverClose: function() {
			this.el.popover('hide');
		},

		/* Callback from getting the number of followers for given user
		 *
		 * json - user dict
		 *
		 * Returns nothing.
		 */
		_onHandleUserFollowersData: function(json) {
			var data = window.user_context_dict[this.options.id];
			data.result.number_of_followers = json.result;
			this._onHandleUserData(data);
		},

		/* Callback from getting whether the currently authed user is following
		 * said user
		 * 
		 * json - user dict
		 *
		 * Returns nothing.
		 */
		_onHandleAmFollowingData: function(json) {
			var data = window.user_context_dict[this.options.id];
			data.result.am_following_user = json.result;
			this._onHandleUserData(data);
		},

		/* Callback from when you follow a specified user... this is used to ensure
		 * all popovers associated to that user get re-populated
		 *
		 * Returns nothing.
		 */
		_onHandleFollow: function() {
			var data = window.user_context_dict[this.options.id];
			data.result.am_following_user = true;
			this._onRenderPopover();
		},

		/* As above... but with unfollow
		 *
		 * Returns nothing.
		 */
		_onHandleUnFollow: function(json) {
			var data = window.user_context_dict[this.options.id];
			data.result.am_following_user = false;
			this._onRenderPopover();
		},

		/* Returns the HTML associated to the button controls
		 *
		 * user = user dict
		 *
		 * Returns nothing.
		 */
		_getButtons: function(user) {
			var html = '';
			if (
				this.options.authed
				&& user.id != this.options.authed
			) {
				if (user.am_following_user) {
					if (user.am_following_user == 'disabled') {
						html = '<a href="javascript:;" class="btn disabled">' + this.i18n('loading') + '</a>';
					} else {
						html = '<a href="javascript:;" class="btn btn-danger" data-module="follow" data-module-type="user" data-module-id="' + user.id + '" data-module-action="unfollow"><i class="icon-remove-sign"></i> ' + this.i18n('unfollow') + '</a>';	
					}
				} else {
					html = '<a href="javascript:;" class="btn btn-success" data-module="follow" data-module-type="user" data-module-id="' + user.id + '" data-module-action="follow"><i class="icon-plus-sign"></i> ' + this.i18n('follow') + '</a>';
				}	
			}
			html += '<a href="' + this.options.url + '" class="btn"><i class="icon-user"></i> ' + this.i18n('view_profile') + '</a>';
			return html;
		}
	};
});
