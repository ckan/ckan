
CKAN.Templates.resourceAddChoice = ' \
  <ul> \
    <li>Add a resource:</li> \
    <li><a href="#" action="upload-file" class="action-resource-tab">Upload a file</a></li> \
    <li><a href="#" action="link-file" class="action-resource-tab">Link to a file</a></li> \
    <li><a href="#" action="link-api" class="action-resource-tab">Link to an API</a></li> \
  </ul> \
';

CKAN.Templates.resourceAddLinkFile = ' \
  <form class="resource-add" action=""> \
    <dl> \
      <dt> \
        <label class="field_opt" for="url"> \
          File URL \
        </label> \
      </dt> \
      <dd> \
        <input name="url" type="text" placeholder="http://mydataset.com/file.csv" style="width: 60%"/> \
        <input name="save" type="submit" class="pretty primary" value="Add" /> \
        <input name="reset" type="reset" class="pretty" value="Cancel" /> \
      </dd> \
    </dl> \
     \
  </form> \
';

CKAN.Templates.resourceAddLinkApi = ' \
  <form class="resource-add" action=""> \
    <dl> \
      <dt> \
        <label class="field_opt" for="url"> \
          Api URL \
        </label> \
      </dt> \
      <dd> \
        <input name="url" type="text" placeholder="http://mydataset.com/file.csv" style="width: 60%" /> \
        <input name="save" type="submit" class="pretty primary" value="Add" /> \
        <input name="reset" type="reset" class="pretty" value="Cancel" /> \
      </dd> \
    </dl> \
     \
  </form> \
';

CKAN.Templates.resourceUpload = ' \
<div class="fileupload"> \
  <form action="http://test-ckan-net-storage.commondatastorage.googleapis.com/" class="resource-upload" \
    enctype="multipart/form-data" \
    method="POST"> \
 \
    <div class="hidden-inputs"></div> \
    <dl> \
      <dt> \
        <label class="field_opt fileinput-button" for="file"> \
          File \
        </label> \
      </dt> \
      <dd> \
        <input type="file" name="file" /> \
        <span class="fileinfo"></span> \
        <input id="upload" name="upload" type="submit" class="pretty primary" value="Add" /> \
        <input id="reset" name="reset" type="reset" class="pretty" value="Cancel" /> \
      </dd> \
    </dl> \
  </form> \
  <div class="messages" style="display: none;"></div> \
  </div> \
</div> \
';



CKAN.Templates.resourceEntry = ' \
  <td class="resource-expand-link"> \
    <a class="resource-expand-link" href="#"><img src="/images/icons/edit-expand.png" /></a> \
    <a class="resource-collapse-link" href="#"><img src="/images/icons/edit-collapse.png" /></a> \
  </td> \
  <td class="resource-summary resource-url"> \
    ${resource.url} \
  </td> \
  <td class="resource-summary resource-format"> \
    ${resource.format} \
  </td> \
  <td class="resource-summary resource-description"> \
    ${resource.description} \
  </td> \
  <td class="resource-expanded" colspan="3"> \
    <dl> \
      <dt><label class="field_opt">Url</label></dt> \
      <dd> \
        <input name="resources__${num}__url" type="text" value="${resource.url}" class="long" /> \
      </dd> \
      <dt>Type</dt> \
      <dd> \
        ${resource.type} \
      </dd> \
      <dt>Mimetype</dt> \
      <dd> \
        ${resource.mimetype} \
      </dd> \
      <dt>Mimetype-inner</dt> \
      <dd> \
        ${resource.mimetype_inner} \
      </dd> \
      <dt>Size</dt> \
      <dd> \
        ${resource.size} \
      </dd> \
      <dt>Last Modified</dt> \
      <dd> \
        ${resource.lastModified} \
      </dd> \
      <dt><label class="field_opt">Format</label></dt> \
      <dd> \
        <input name="resources__${num}__format" type="text" value="${resource.format}" class="long" /> \
      </dd> \
      <dt><label class="field_opt">Description</label></dt> \
      <dd> \
        <input name="resources__${num}__description" type="text" value="${resource.description}" class="long" /> \
      </dd> \
      <dt><label class="field_opt">Hash</label></dt> \
      <dd> \
        <input name="resources__${num}__hash" type="text" value="${resource.hash}" class="long" /> \
      </dd> \
    </dl> \
    <input name="resources__${num}__id" type="hidden" value="${resource.id}" class="long disabled" /> \
  </td> \
  <td class="resource-is-changed"> \
    <img src="/images/icons/add.png" title="This resource has unsaved changes." class="resource-is-changed" /> \
  </td> \
';
