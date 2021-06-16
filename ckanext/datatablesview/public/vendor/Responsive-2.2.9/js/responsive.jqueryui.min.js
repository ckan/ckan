/*!
 jQuery UI integration for DataTables' Responsive
 ©2015 SpryMedia Ltd - datatables.net/license
*/
(function(c){"function"===typeof define&&define.amd?define(["jquery","datatables.net-jqui","datatables.net-responsive"],function(a){return c(a,window,document)}):"object"===typeof exports?module.exports=function(a,b){a||(a=window);b&&b.fn.dataTable||(b=require("datatables.net-jqui")(a,b).$);b.fn.dataTable.Responsive||require("datatables.net-responsive")(a,b);return c(b,a,a.document)}:c(jQuery,window,document)})(function(c,a,b,k){a=c.fn.dataTable;b=a.Responsive.display;var h=b.modal;b.modal=function(d){return function(e,
f,g){c.fn.dialog?f||c("<div/>").append(g()).appendTo("body").dialog(c.extend(!0,{title:d&&d.header?d.header(e):"",width:500},d.dialog)):h(e,f,g)}};return a.Responsive});
