/*!
 Foundation integration for DataTables' Responsive
 ©2015 SpryMedia Ltd - datatables.net/license
*/
(function(a){"function"===typeof define&&define.amd?define(["jquery","datatables.net-zf","datatables.net-responsive"],function(b){return a(b,window,document)}):"object"===typeof exports?module.exports=function(b,c){b||(b=window);c&&c.fn.dataTable||(c=require("datatables.net-zf")(b,c).$);c.fn.dataTable.Responsive||require("datatables.net-responsive")(b,c);return a(c,b,b.document)}:a(jQuery,window,document)})(function(a,b,c,k){b=a.fn.dataTable;c=b.Responsive.display;var h=c.modal;c.modal=function(e){return function(f,
d,g){a.fn.foundation?d||(d=a('<div class="reveal-overlay" style="display:block"/>'),a('<div class="reveal reveal-modal" style="display:block; top: 150px;" data-reveal/>').append('<button class="close-button" aria-label="Close">&#215;</button>').append(e&&e.header?"<h4>"+e.header(f)+"</h4>":null).append(g()).appendTo(d),d.appendTo("body"),a("button.close-button").on("click",function(){a(".reveal-overlay").remove()}),a(".reveal-overlay").on("click",function(){a(".reveal-overlay").remove()})):h(f,d,
g)}};return b.Responsive});
