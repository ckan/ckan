function addRowToTable()
{
    var tbl = document.getElementById('flexitable');
    var prefix = tbl.getAttribute('prefix');

    var lastRow = tbl.rows.length;
    var rowToInsert = lastRow;
    var row = tbl.insertRow(rowToInsert);
    var iteration = lastRow - 1;

    var row_prefix = prefix + '-' + iteration;
    
    var cell = row.insertCell(0);
    var el = document.createElement('input');
    el.type = 'text';
    el.id = row_prefix + '-url';
    el.name = row_prefix + '-url';
    el.size = 40;
    cell.appendChild(el);
    
    var cell = row.insertCell(1);
    var el = document.createElement('input');
    el.type = 'text';
    el.id = row_prefix + '-format';
    el.name = row_prefix + '-format';
    el.size = 5;
    cell.appendChild(el);

    var cell = row.insertCell(2);
    var el = document.createElement('input');
    el.type = 'text';
    el.id = row_prefix + '-description';
    el.name = row_prefix + '-description';
    el.size = 25;
    cell.appendChild(el);
    
    var cell = row.insertCell(3);
    var el = document.createElement('input');
    el.type = 'text';
    el.id = row_prefix + '-hash';
    el.name = row_prefix + '-hash';
    el.size = 10;
    cell.appendChild(el);

    var cell = row.insertCell(4);
    var anchor = document.createElement('a');
    anchor.href = 'javascript:moveRowUp(' + iteration + ')';
    var image = document.createElement('img');
    image.src = '/images/icons/arrow_up.png';
    anchor.appendChild(image);
    cell.appendChild(anchor);
    var anchor = document.createElement('a');
    anchor.href = 'javascript:moveRowDown(' + iteration + ')';
    var image = document.createElement('img');
    image.src = '/images/icons/arrow_down.png';
    anchor.appendChild(image);
    cell.appendChild(anchor);
    var anchor = document.createElement('a');
    anchor.href = 'javascript:removeRowFromTable(' + iteration + ')';
    var image = document.createElement('img');
    image.src = 'http://m.okfn.org/kforge/images/icon-delete.png';
    image.className = 'icon';
    anchor.appendChild(image);
    cell.appendChild(anchor);
}

function renumberRowFunctions()
{
    var tbl = document.getElementById('flexitable');
    var lastRow = tbl.rows.length;
    for (var row=1; row<lastRow; row++) {
      var button_cell = tbl.rows[row].cells[3];
      var anchor = button_cell.firstChild;
      while (anchor)
        {
          if (anchor.nodeType == 1) {
            anchor.href = anchor.href.replace(/(\d)/, (row-1));
          }
          anchor=anchor.nextSibling;
        }
    }
}

function removeLastRowFromTable()
{
    var tbl = document.getElementById('flexitable');
    var lastRow = tbl.rows.length;
    if (lastRow > 1) tbl.deleteRow(lastRow - 1);
}
function removeRowFromTable(row_index)
{
    var tbl = document.getElementById('flexitable');
    var lastRow = tbl.rows.length;
    var table_row = row_index + 1;
    if (table_row > 0 && table_row <= lastRow) tbl.deleteRow(table_row);
    renumberRowFunctions();
}
function moveRowUp(row_index)
{
    var tbl = document.getElementById('flexitable');
    var lastRow = tbl.rows.length;
    var table_row_index = row_index + 1;
    var swap_row_index = table_row_index - 1;
    if (table_row_index > 1 && table_row_index <= lastRow) {
      swapRows(swap_row_index, table_row_index, tbl);
    }
}
function moveRowDown(row_index)
{
    var tbl = document.getElementById('flexitable');
    var lastRow = tbl.rows.length;
    var table_row_index = row_index + 1;
    var swap_row_index = table_row_index + 1;
    if (table_row_index > 0 && table_row_index < lastRow-1) {
      swapRows(swap_row_index, table_row_index, tbl);
    }
}
function swapRows(row_i, row_j, table)
{
  var tbl = document.getElementById('flexitable');
  var lastRow = tbl.rows.length;
  for (var col=0; col<lastRow; col++){
    cell1 = table.rows[row_i].cells[col];
    cell2 = table.rows[row_j].cells[col];
    swapCells(cell1, cell2);
  }
}
function swapCells(cell1, cell2)
{
  var dummy = cell1.firstChild.value;
  cell1.firstChild.value = cell2.firstChild.value;
  cell2.firstChild.value = dummy;
}
