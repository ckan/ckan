/*!
 Bulma integration for DataTables' Buttons
 ©2021 SpryMedia Ltd - datatables.net/license
*/
(function(b){"function"===typeof define&&define.amd?define(["jquery","datatables.net-bm","datatables.net-buttons"],function(a){return b(a,window,document)}):"object"===typeof exports?module.exports=function(a,c){a||(a=window);c&&c.fn.dataTable||(c=require("datatables.net-bm")(a,c).$);c.fn.dataTable.Buttons||require("datatables.net-buttons")(a,c);return b(c,a,a.document)}:b(jQuery,window,document)})(function(b,a,c,f){a=b.fn.dataTable;b.extend(!0,a.Buttons.defaults,{dom:{container:{className:"dt-buttons field is-grouped"},
button:{className:"button is-light",active:"is-active",disabled:"is-disabled"},collection:{tag:"div",className:"dropdown-content",button:{tag:"a",className:"dt-button dropdown-item",active:"is-active",disabled:"is-disabled"}}},buttonCreated:function(d,e){d.buttons&&(d._collection=b('<div class="dropdown-menu"/>').append(d._collection),b(e).append('<span class="icon is-small"><i class="fa fa-angle-down" aria-hidden="true"></i></span>'));return e}});return a.Buttons});
