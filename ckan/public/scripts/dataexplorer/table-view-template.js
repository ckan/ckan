DATAEXPLORER.TABLEVIEW.template.html = ' \
<div class="dataexplorer-tableview-viewer"> \
  <div class="dataexplorer-tableview-nav"> \
    <span class="dataexplorer-tableview-nav-toggle"> \
      <input type="radio" id="dataexplorer-tableview-nav-grid" name="dataexplorer-tableview-nav-toggle" value="grid" checked="checked" /> \
      <label for="dataexplorer-tableview-nav-grid">Grid</label> \
      <input type="radio" id="dataexplorer-tableview-nav-graph" name="dataexplorer-tableview-nav-toggle" value="chart" /> \
      <label for="dataexplorer-tableview-nav-graph">Graph</label> \
    </span> \
    <input type="checkbox" id="dataexplorer-tableview-nav-editor" checked="checked" /> \
    <label for="dataexplorer-tableview-nav-editor">Toggle Editor</label> \
  </div> \
  <div class="dataexplorer-tableview-editor"> \
    <div class="dataexplorer-tableview-editor-info dataexplorer-tableview-editor-hide-info"> \
      <h1><span></span>Help</h1> \
      <p>To create a chart select a column (group) to use as the x-axis \
         then another column (Series A) to plot against it.</p> \
      <p>You can add add \
         additional series by clicking the "Add series" button</p> \
      <p>Please note you must be logged in to save charts.</p> \
    </div> \
    <form> \
      <ul> \
        <li class="dataexplorer-tableview-editor-type"> \
          <label>Graph Type</label> \
          <select></select> \
        </li> \
        <li class="dataexplorer-tableview-editor-group"> \
          <label>Group Column (x-axis)</label> \
          <select></select> \
        </li> \
        <li class="dataexplorer-tableview-editor-series"> \
          <label>Series <span>A (y-axis)</span></label> \
          <select></select> \
        </li> \
      </ul> \
      <div class="dataexplorer-tableview-editor-buttons"> \
        <button class="dataexplorer-tableview-editor-add">Add Series</button> \
      </div> \
      <div class="dataexplorer-tableview-editor-buttons dataexplorer-tableview-editor-submit"> \
        <button class="dataexplorer-tableview-editor-save">Save</button> \
        <input type="hidden" class="dataexplorer-tableview-editor-id" value="chart-1" /> \
      </div> \
    </form> \
  </div> \
  <div class="dataexplorer-tableview-panel dataexplorer-tableview-grid"></div> \
  <div class="dataexplorer-tableview-panel dataexplorer-tableview-graph"></div> \
</div> \
';
