/* flexitable.js
  
   TODO:
   - replace separate moveUp/moveDown buttons with a drag handle.
*/

(function ($) {

  var fieldNameRegex = /^(\S+)-(\d+)-(\S+)$/;

  var controlsHtml = '<td><div class="controls">' +
                       '<a class="moveUp"   title="Move this row up" href="#moveUp">Move up</a>' +
                       '<a class="moveDown" title="Move this row down" href="#moveDown">Move down</a>' +
                       '<a class="remove"   title="Remove this row" href="#remove">Remove row</a>' +
                     '</div></td>';
  
  var addRowHtml = '<p class="flexitable"><button class="addRow">Add row to table</button></p>';

  function getRowNumber(tr) {
    var rowNumber = $(tr).find('input').attr('name').match(fieldNameRegex)[2];
    return parseInt(rowNumber, 10);
  }

  function setRowNumber(tr, num) {
    $(tr).find('input').each(function () {
      $(this).attr({
        id:   $(this).attr('id').replace(fieldNameRegex, "$1-" + num + "-$3"),
        name: $(this).attr('name').replace(fieldNameRegex, "$1-" + num + "-$3")
      });
    });
  }
  
  // Currently only supports -1 or 1 for up or down respectively.
  function moveRow(row, offset) {
    row = $(row);
    var movingUp = (offset < 0),
        swapWith = movingUp ? 'prev' : 'next',
        swapHow  = movingUp ? 'after' : 'before',
        swapEl = row[swapWith](),
        rowNum = getRowNumber(row);

    if (swapEl[0]) {
      row[swapHow](swapEl);

      setRowNumber(row, rowNum + offset);
      setRowNumber(swapEl, rowNum);
    }
  }
  
  function addRow () {
    var table = $(this).parents('p').eq(0).prev(),
        lastRow = table.find('tr:last'),
        clone = lastRow.clone(true);

    clone.insertAfter(lastRow).find('input').val('');
    setRowNumber(clone, getRowNumber(lastRow) + 1);
    return false;
  }
  
  function removeRow () {
    if (confirm('Are you sure you wish to remove this row?')) {
      var row = $(this).parents('tr'),
          following = row.nextAll();
      
      row.remove();
      following.each(function () {
        setRowNumber(this, getRowNumber(this) - 1);
      });
    }
    return false;
  }

  $(document).ready(function () {
    $('.flexitable').find('tbody tr').append(controlsHtml).end()

                    .find('a.moveUp').click(function () {
                      moveRow($(this).parents('tr')[0], -1);
                      return false;
                    }).end()

                    .find('a.moveDown').click(function () {
                      moveRow($(this).parents('tr')[0], 1);
                      return false;
                    }).end()
                    
                    .find('a.remove').click(removeRow).end()
                    
                    .after(addRowHtml)
                    .next().find('button.addRow').click(addRow);
  });

})(jQuery);
