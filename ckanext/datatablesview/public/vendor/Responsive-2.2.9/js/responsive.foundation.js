/*! Foundation integration for DataTables' Responsive
 * ©2015 SpryMedia Ltd - datatables.net/license
 */

(function( factory ){
	if ( typeof define === 'function' && define.amd ) {
		// AMD
		define( ['jquery', 'datatables.net-zf', 'datatables.net-responsive'], function ( $ ) {
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
				$ = require('datatables.net-zf')(root, $).$;
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

_display.modal = function ( options ) {
	return function ( row, update, render ) {
		if ( ! $.fn.foundation ) {
			_original( row, update, render );
		}
		else {
			if ( ! update ) {
				var	modalContainer = $('<div class="reveal-overlay" style="display:block"/>');
				$( '<div class="reveal reveal-modal" style="display:block; top: 150px;" data-reveal/>' )
					.append( '<button class="close-button" aria-label="Close">&#215;</button>' )
					.append( options && options.header ? '<h4>'+options.header( row )+'</h4>' : null )
					.append( render() )
					.appendTo( modalContainer );
				
				modalContainer.appendTo('body');

				$('button.close-button').on('click', function() {
					$('.reveal-overlay').remove();
				})
				$('.reveal-overlay').on('click', function() {
					$('.reveal-overlay').remove();
				})
			}
		}
	};
};


return DataTable.Responsive;
}));
