/*! Bulma integration for DataTables' Responsive
 * ©2015 SpryMedia Ltd - datatables.net/license
 */

(function( factory ){
	if ( typeof define === 'function' && define.amd ) {
		// AMD
		define( ['jquery', 'datatables.net-bm', 'datatables.net-responsive'], function ( $ ) {
			return factory( $, window, document );
		} );
	}
	else if ( typeof exports === 'object' ) {
		// CommonJS
		module.exports = function (root, $) {
			if ( ! root ) {
				root = window;
			}

			if ( ! $ || ! $.fn.dataTable ) {
				$ = require('datatables.net-bm')(root, $).$;
			}

			if ( ! $.fn.dataTable.Responsive ) {
				require('datatables.net-responsive')(root, $);
			}

			return factory( $, root, root.document );
		};
	}
	else {
		// Browser
		factory( jQuery, window, document );
	}
}(function( $, window, document, undefined ) {
'use strict';
var DataTable = $.fn.dataTable;


var _display = DataTable.Responsive.display;
var _original = _display.modal;
var _modal = $(
		'<div class="modal DTED">'+
			'<div class="modal-background"></div>'+
			'<div class="modal-content">' +
				'<div class="modal-header">'+
					'<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>'+
				'</div>'+
				'<div class="modal-body"/>'+
			'</div>'+
			'<button class="modal-close is-large" aria-label="close"></button>'+
		'</div>'
)

_display.modal = function ( options ) {
	return function ( row, update, render ) {
		if ( ! update ) {
			if ( options && options.header ) {
				var header = _modal.find('div.modal-header');
				header.find('button').detach();
				
				header
					.empty()
					.append( '<h4 class="modal-title subtitle">'+options.header( row )+'</h4>' );
			}

			_modal.find( 'div.modal-body' )
				.empty()
				.append( render() );

			_modal
				.appendTo( 'body' )

			_modal.addClass('is-active is-clipped');

			$('.modal-close').one('click', function() {
				_modal.removeClass('is-active is-clipped');
			})
			$('.modal-background').one('click', function() {
				_modal.removeClass('is-active is-clipped');
			})
		}
	};
};


return DataTable.Responsive;
}));
