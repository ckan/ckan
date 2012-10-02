window.user_context_dict = {};
this.ckan.module('user-context', function($, _) {
	return {
		options : {
			id: null,
			loading: false,
			authed: false,
			url: '',
			template: '<div class="profile-info">{{ about }}<div class="btn-group">{{ buttons }}</div><div class="nums"><dl><dt>Followers</dt><dd>{{ followers }}</dd></dl><dl><dt>Datasets</dt><dd>{{ datasets }}</dd></dl><dl><dt>Edits</dt><dd>{{ edits }}</dd></dl></div></div>',
			i18n: {
				follow: _('Follow'),
				unfollow: _('Unfollow'),
				loading: _('Loading...')
			}
		},
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
			}
		},
		getUserData: function() {
			if (!this.loading) {
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
		_onMouseOver: function(e) {
			$('[data-module="user-context"]').popover('hide');
			this.el.popover('show');
			this.getUserData();
		},
		_onHandleUserData: function(json) {
			this.loading = false;
			if (json.success) {
				var id = this.options.id;
				var client = this.sandbox.client;
				var user = json.result;
				var popover = this.el.data('popover');
				if (typeof user.number_of_followers == 'undefined') {
					user.number_of_followers = '...';
					client.call('GET', 'user_follower_count', '?id=' + id, this._onHandleUserFollowersData);
				}
				if (typeof user.am_following_user == 'undefined') {
					user.am_following_user = 'disabled';
					client.call('GET', 'am_following_user', '?id=' + id, this._onHandleAmFollowingData);
				}
				if (typeof popover.$tip != 'undefined') {
					var tip	= popover.$tip;
					var about = user.about ? '<p class="about">' + user.about + '</p>' : '';
					var template = this.options.template
						.replace('{{ about }}', about)
						.replace('{{ followers }}', user.number_of_followers)
						.replace('{{ datasets }}', user.number_administered_packages)
						.replace('{{ edits }}', user.number_of_edits)
						.replace('{{ buttons }}', this._getButtons(user));
					$('.popover-title', tip).html('<a href="javascript:;" class="popover-close">&times;</a>' + user.display_name);
					$('.popover-content', tip).html(template);
					$('.popover-close', tip).on('click', this._onHandlePopoverClose);
				}
				window.user_context_dict[this.options.id] = json;
			}
		},
		_onHandlePopoverClose: function() {
			this.el.popover('hide');
		},
		_onHandleUserFollowersData: function(json) {
			var data = window.user_context_dict[this.options.id];
			data.result.number_of_followers = json.result;
			this._onHandleUserData(data);
		},
		_onHandleAmFollowingData: function(json) {
			var data = window.user_context_dict[this.options.id];
			data.result.am_following_user = json.result;
			this._onHandleUserData(data);
		},
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
						html = '<a href="javascript:;" class="btn btn-danger"><i class="icon-remove-sign"></i> ' + this.i18n('unfollow') + '</a>';	
					}
				} else {
					html = '<a href="javascript:;" class="btn btn-success"><i class="icon-plus-sign"></i> ' + this.i18n('follow') + '</a>';
				}	
			}
			html += '<a href="' + this.options.url + '" class="btn"><i class="icon-user"></i> View profile</a>';
			return html;
		}
	};
});
