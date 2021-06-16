/*! DataTables Bulma integration
 * ©2020 SpryMedia Ltd - datatables.net/license
 */

(function( factory ){
	if ( typeof define === 'function' && define.amd ) {
		// AMD
		define( ['jquery', 'datatables.net'], function ( $ ) {
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
				// Require DataTables, which attaches to jQuery, including
				// jQuery if needed and have a $ property so we can access the
				// jQuery object that is used
				$ = require('datatables.net')(root, $).$;
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


/* Set the defaults for DataTables initialisation */
$.extend( true, DataTable.defaults, {
	dom:
		"<'columns is-gapless is-multiline'" +
			"<'column is-one-half'l>" +
			"<'column is-one-half'f>" +
			"<'column is-full'tr>" +
			"<'column is-one-half'i>" +
			"<'column is-one-half'p>" +
		">",
	renderer: 'bulma'
} );


/* Default class modification */
$.extend( DataTable.ext.classes, {
	sWrapper:      "dataTables_wrapper dt-bulma",
	sFilterInput:  "input",
	sLengthSelect: "custom-select custom-select-sm form-control form-control-sm",
	sProcessing:   "dataTables_processing card"
} );


/* Bulma paging button renderer */
DataTable.ext.renderer.pageButton.bulma = function ( settings, host, idx, buttons, page, pages ) {
	var api     = new DataTable.Api( settings );
	var classes = settings.oClasses;
	var lang    = settings.oLanguage.oPaginate;
	var aria = settings.oLanguage.oAria.paginate || {};
	var btnDisplay, btnClass, counter=0;

	var attach = function( container, buttons ) {
		var i, ien, node, button, tag, disabled;
		var clickHandler = function ( e ) {
			e.preventDefault();
			if ( !$(e.currentTarget).hasClass('disabled') && api.page() != e.data.action ) {
				api.page( e.data.action ).draw( 'page' );
			}
		};

		for ( i=0, ien=buttons.length ; i<ien ; i++ ) {
			button = buttons[i];

			if ( Array.isArray( button ) ) {
				attach( container, button );
			}
			else {
				btnDisplay = '';
				btnClass = '';
				tag = 'a';
				disabled = false;

				switch ( button ) {
					case 'ellipsis':
						btnDisplay = '&#x2026;';
						btnClass = 'pagination-link';
						tag = 'span';
						break;

					case 'first':
						btnDisplay = lang.sFirst;
						btnClass = button;
						disabled = page <= 0;
						break;

					case 'previous':
						btnDisplay = lang.sPrevious;
						btnClass = button;
						disabled = page <= 0;
						break;

					case 'next':
						btnDisplay = lang.sNext;
						btnClass = button;
						disabled = page >= pages - 1;
						break;

					case 'last':
						btnDisplay = lang.sLast;
						btnClass = button;
						disabled = page >= pages - 1;
						break;

					default:
						btnDisplay = button + 1;
						btnClass = page === button ?
							'is-current' : '';
						break;
				}

				if ( btnDisplay ) {
					node = $('<li>', {
							'id': idx === 0 && typeof button === 'string' ?
								settings.sTableId +'_'+ button :
								null
						} )
						.append( $('<' + tag + '>', {
								'href': '#',
								'aria-controls': settings.sTableId,
								'aria-label': aria[ button ],
								'data-dt-idx': counter,
								'tabindex': settings.iTabIndex,
								'class': 'pagination-link ' + btnClass,
								'disabled': disabled
							} )
							.html( btnDisplay )
						)
						.appendTo( container );

					settings.oApi._fnBindAction(
						node, {action: button}, clickHandler
					);

					counter++;
				}
			}
		}
	};

	// IE9 throws an 'unknown error' if document.activeElement is used
	// inside an iframe or frame. 
	var activeEl;

	try {
		// Because this approach is destroying and recreating the paging
		// elements, focus is lost on the select button which is bad for
		// accessibility. So we want to restore focus once the draw has
		// completed
		activeEl = $(host).find(document.activeElement).data('dt-idx');
	}
	catch (e) {}

	var nav = $('<nav class="pagination" role="navigation" aria-label="pagination"><ul class="pagination-list"></ul></nav>');
	$(host).empty().append(nav);

	attach(nav.find('ul'), buttons);

	if ( activeEl !== undefined ) {
		$(host).find( '[data-dt-idx='+activeEl+']' ).trigger('focus');
	}
};

// Javascript enhancements on table initialisation
$(document).on( 'init.dt', function (e, ctx) {
	if ( e.namespace !== 'dt' ) {
		return;
	}

	var api = new $.fn.dataTable.Api( ctx );

	// Length menu drop down - needs to be wrapped with a div
	$( 'div.dataTables_length select', api.table().container() ).wrap('<div class="select">');

	// Filtering input
	// $( 'div.dataTables_filter.ui.input', api.table().container() ).removeClass('input').addClass('form');
	// $( 'div.dataTables_filter input', api.table().container() ).wrap( '<span class="ui input" />' );
} );



return DataTable;
}));
